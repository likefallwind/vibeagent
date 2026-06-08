from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any

from .actions import AGENT_TOOL_DEFINITIONS, ActionParseError, execute_action, parse_tool_action
from .prompts import build_messages
from .types import (
    AgentLogger,
    ApprovalDecision,
    ApprovalDeniedObservation,
    ApprovalHandler,
    ApprovalRequest,
    ChatClient,
    ChatMessage,
    CheckPatchAction,
    CheckPatchesAction,
    ContentBlock,
    DeleteFileAction,
    EditFileAction,
    FileInfoAction,
    FinishAction,
    GlobAction,
    GitBlameAction,
    GitChangesAction,
    GitDiffAction,
    GitLogAction,
    GitShowAction,
    GitStatusAction,
    InsertLinesAction,
    ListFilesAction,
    ListFilesObservation,
    ListProcessesAction,
    ListTreeAction,
    MultiEditAction,
    Observation,
    PatchFileAction,
    PatchFilesAction,
    PlanItem,
    PythonCheckAction,
    PythonCallGraphAction,
    PythonCallsAction,
    PythonDependenciesAction,
    PythonDefinitionsAction,
    ReplacePythonDefinitionAction,
    PythonReferencesAction,
    PythonSymbolsAction,
    ReadFileAction,
    ReadFileRangesAction,
    ReadFilesAction,
    ReadProcessAction,
    ReplaceLinesAction,
    ReviewChangesAction,
    RepoMapAction,
    RunCommandObservation,
    RunCommandAction,
    SearchAction,
    SessionSummaryAction,
    StartCommandAction,
    StopProcessAction,
    SuggestChecksAction,
    TaskStep,
    ToolErrorObservation,
    UpdatePlanAction,
    WriteFileAction,
    WriteFilesAction,
    MoveFileAction,
)
from .workspace import RunWorkspace, create_run_workspace


@dataclass(frozen=True)
class AgentResult:
    success: bool
    message: str
    run_dir: Path
    run_id: str
    iterations: int
    observations: list[Observation]
    steps: list[TaskStep]
    plan: list[PlanItem] = field(default_factory=list)


def run_agent(
    task: str,
    client: ChatClient,
    base_dir: str | Path | None = None,
    max_iterations: int = 20,
    command_timeout_ms: int = 30_000,
    logger: AgentLogger | None = None,
    workspace: RunWorkspace | None = None,
    approval_handler: ApprovalHandler | None = None,
    prior_context: str | None = None,
) -> AgentResult:
    # Start with an isolated run workspace for one task execution.
    current_workspace = workspace or create_run_workspace(base_dir)
    observations: list[Observation] = []
    steps: list[TaskStep] = []
    plan: list[PlanItem] = []
    messages = build_messages(task, current_workspace, prior_context=prior_context)
    append_session_event(
        current_workspace.session_dir,
        "task",
        {"task": task, "prior_context": compact_session_context(prior_context) if prior_context else None},
    )

    for iteration in range(1, max_iterations + 1):
        # Tool loop: provider-neutral tool_call blocks -> local execution -> tool_result blocks.
        if logger:
            logger("thinking", f"iteration {iteration}/{max_iterations}")

        response = client.complete(messages, tools=AGENT_TOOL_DEFINITIONS)
        assistant_content = normalize_assistant_content(response.content if hasattr(response, "content") else response)
        append_session_event(current_workspace.session_dir, "model", {"iteration": iteration, "content": assistant_content})
        messages.append(ChatMessage(role="assistant", content=assistant_content))

        tool_calls = [block for block in assistant_content if block.get("type") == "tool_call"]
        if not tool_calls:
            text = content_blocks_to_text(assistant_content).strip()
            if text:
                if logger:
                    logger("finished", text)
                return AgentResult(
                    success=True,
                    message=text,
                    run_dir=current_workspace.root,
                    run_id=current_workspace.run_id,
                    iterations=iteration,
                    observations=observations,
                    steps=steps,
                    plan=plan,
                )
            return AgentResult(
                success=False,
                message="Model response did not include text or a tool call.",
                run_dir=current_workspace.root,
                run_id=current_workspace.run_id,
                iterations=iteration,
                observations=observations,
                steps=steps,
                plan=plan,
            )

        tool_results: list[ContentBlock] = []
        for block in tool_calls:
            tool_id = str(block.get("id") or "")
            tool_name = str(block.get("name") or "")
            tool_input = block.get("input") or {}
            append_session_event(
                current_workspace.session_dir,
                "tool_call",
                {"iteration": iteration, "id": tool_id, "name": tool_name, "input": tool_input},
            )

            try:
                action = parse_tool_action(tool_name, tool_input)
                step = start_task_step(current_workspace, steps, iteration, action, logger)
                log_action(logger, action)
                repeated_list = find_repeated_list_observation(action, observations)
                if repeated_list:
                    observation = ListFilesObservation(
                        kind="list_files",
                        path=repeated_list.path,
                        files=repeated_list.files,
                        total=repeated_list.total,
                        truncated=repeated_list.truncated,
                        message=(
                            f"Already listed {repeated_list.path}: {repeated_list.message} "
                            "Do not call list_files for this path again. Choose a useful tool call or answer directly."
                        ),
                    )
                else:
                    approval_request = build_approval_request(action)
                    if approval_request:
                        append_session_event(
                            current_workspace.session_dir,
                            "approval_requested",
                            {"iteration": iteration, "step": step, "request": approval_request},
                        )
                        if logger:
                            logger("approval required", summarize_approval_request(approval_request))
                        decision = request_approval(approval_handler, approval_request)
                        append_session_event(
                            current_workspace.session_dir,
                            "approval_decision",
                            {"iteration": iteration, "step": step, "decision": decision},
                        )
                        if logger:
                            status = "approval approved" if decision.approved else "approval denied"
                            logger(status, summarize_approval_decision(approval_request, decision))
                        if not decision.approved:
                            observation = ApprovalDeniedObservation(
                                kind="approval_denied",
                                action_type=approval_request.action_type,
                                target=approval_request.target,
                                message=decision.message or "Action was denied by approval policy.",
                            )
                        else:
                            observation = execute_action(current_workspace, action, command_timeout_ms)
                    else:
                        observation = execute_action(current_workspace, action, command_timeout_ms)
                if observation.kind == "update_plan":
                    plan = list(observation.plan)
                complete_task_step(current_workspace, step, observation, iteration, logger)
            except ActionParseError as error:
                observation = tool_error_observation(tool_name, error)

            observations.append(observation)
            result_payload = to_jsonable(observation)
            append_session_event(
                current_workspace.session_dir,
                "tool_result",
                {"iteration": iteration, "id": tool_id, "name": tool_name, "result": result_payload},
            )
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_call_id": tool_id,
                    "content": json.dumps(result_payload, ensure_ascii=False),
                }
            )

            if observation.kind == "finish":
                if logger:
                    logger("finished", observation.message)
                return AgentResult(
                    success=True,
                    message=observation.message,
                    run_dir=current_workspace.root,
                    run_id=current_workspace.run_id,
                    iterations=iteration,
                    observations=observations,
                    steps=steps,
                    plan=plan,
                )

            if isinstance(observation, RunCommandObservation) and logger:
                ok = observation.result.exit_code == 0 and not observation.result.timed_out
                logger("observed success" if ok else "observed failure", summarize_command(observation.result))

        messages.append(ChatMessage(role="user", content=tool_results))

    # Return failure only after exhausting max iterations without an explicit finish action.
    return AgentResult(
        success=False,
        message=f"Reached iteration limit ({max_iterations}) before finish.",
        run_dir=current_workspace.root,
        run_id=current_workspace.run_id,
        iterations=max_iterations,
        observations=observations,
        steps=steps,
        plan=plan,
    )


def summarize(value: str, max_length: int = 500) -> str:
    compact = " ".join(value.split())
    if len(compact) <= max_length:
        return compact
    return f"{compact[:max_length]}..."


def compact_session_context(value: str | None, max_length: int = 4000) -> str | None:
    if value is None:
        return None
    compact = "\n".join(line.rstrip() for line in value.strip().splitlines() if line.strip())
    if len(compact) <= max_length:
        return compact
    return f"{compact[:max_length]}..."


def find_repeated_list_observation(action: object, observations: list[Observation]) -> ListFilesObservation | None:
    if getattr(action, "type", None) != "list_files":
        return None

    path = getattr(action, "path", None) or "."
    for observation in reversed(observations):
        if observation.kind == "list_files" and observation.path == path:
            return observation
    return None


def start_task_step(
    workspace: RunWorkspace,
    steps: list[TaskStep],
    iteration: int,
    action: object,
    logger: AgentLogger | None,
) -> TaskStep:
    step = TaskStep(
        id=len(steps) + 1,
        label=build_step_label(action),
        action_type=str(getattr(action, "type", "unknown")),
        target=build_action_target(action),
        status="running",
    )
    steps.append(step)
    append_session_event(workspace.session_dir, "step_started", {"iteration": iteration, "step": step})
    if logger:
        logger("step started", step.label)
    return step


def complete_task_step(
    workspace: RunWorkspace,
    step: TaskStep,
    observation: Observation,
    iteration: int,
    logger: AgentLogger | None,
) -> None:
    if observation.kind == "approval_denied":
        step.status = "denied"
    elif observation_failed(observation):
        step.status = "failed"
    else:
        step.status = "completed"
    step.message = observation_summary(observation)
    append_session_event(workspace.session_dir, "step_completed", {"iteration": iteration, "step": step})
    if logger:
        logger("step completed", f"{step.label} -> {step.status}")


def build_step_label(action: object) -> str:
    if isinstance(action, WriteFileAction):
        return f"Write {action.path}"
    if isinstance(action, WriteFilesAction):
        return f"Write {len(action.files)} files"
    if isinstance(action, EditFileAction):
        return f"Edit {action.path}"
    if isinstance(action, MultiEditAction):
        return f"Multi-edit {action.path}"
    if isinstance(action, ReplaceLinesAction):
        return f"Replace lines {action.start_line}-{action.end_line} in {action.path}"
    if isinstance(action, InsertLinesAction):
        return f"Insert lines before {action.line} in {action.path}"
    if isinstance(action, CheckPatchAction):
        return f"Check patch {action.path}"
    if isinstance(action, CheckPatchesAction):
        return "Check patches"
    if isinstance(action, PatchFileAction):
        return f"Patch {action.path}"
    if isinstance(action, PatchFilesAction):
        return "Patch files"
    if isinstance(action, DeleteFileAction):
        return f"Delete {action.path}"
    if isinstance(action, MoveFileAction):
        return f"Move {action.source}"
    if isinstance(action, RunCommandAction):
        suffix = f" in {action.cwd}" if action.cwd else ""
        return f"Run {summarize(action.command, 80)}{suffix}"
    if isinstance(action, StartCommandAction):
        suffix = f" in {action.cwd}" if action.cwd else ""
        return f"Start {summarize(action.command, 80)}{suffix}"
    if isinstance(action, ReadProcessAction):
        return f"Read process {action.process_id}"
    if isinstance(action, ListProcessesAction):
        return "List background processes"
    if isinstance(action, StopProcessAction):
        return f"Stop process {action.process_id}"
    if isinstance(action, UpdatePlanAction):
        return "Update plan"
    if isinstance(action, RepoMapAction):
        return f"Map repo {action.path or '.'}"
    if isinstance(action, ReadFileAction):
        return f"Read {action.path}"
    if isinstance(action, ReadFilesAction):
        return f"Read {len(action.paths)} files"
    if isinstance(action, ReadFileRangesAction):
        return f"Read {len(action.ranges)} file ranges"
    if isinstance(action, FileInfoAction):
        return f"Inspect {len(action.paths)} paths"
    if isinstance(action, PythonSymbolsAction):
        return f"Read Python symbols for {len(action.paths)} files"
    if isinstance(action, PythonCheckAction):
        return f"Check Python {action.path or '.'}"
    if isinstance(action, PythonDependenciesAction):
        return f"Read Python dependencies {action.path or '.'}"
    if isinstance(action, PythonDefinitionsAction):
        return f"Read Python definitions {action.symbol}"
    if isinstance(action, ReplacePythonDefinitionAction):
        return f"Replace Python definition {action.symbol}"
    if isinstance(action, PythonCallsAction):
        return f"Read Python calls {action.symbol}"
    if isinstance(action, PythonCallGraphAction):
        return f"Read Python call graph {action.path or '.'}"
    if isinstance(action, PythonReferencesAction):
        return f"Find Python references {action.symbol}"
    if isinstance(action, SearchAction):
        return f"Search {summarize(action.query, 80)}"
    if isinstance(action, GlobAction):
        return f"Find files {summarize(action.pattern, 80)}"
    if isinstance(action, ListTreeAction):
        return f"List tree {action.path or '.'}"
    if isinstance(action, GitStatusAction):
        return "Read git status"
    if isinstance(action, GitChangesAction):
        return "Read git changes"
    if isinstance(action, ReviewChangesAction):
        return "Review changes"
    if isinstance(action, SuggestChecksAction):
        return "Suggest checks"
    if isinstance(action, GitDiffAction):
        return f"Read git diff {action.path or '.'}"
    if isinstance(action, GitLogAction):
        return f"Read git log {action.path or '.'}"
    if isinstance(action, GitShowAction):
        return f"Read git show {action.rev}"
    if isinstance(action, GitBlameAction):
        return f"Read git blame {action.path}"
    if isinstance(action, SessionSummaryAction):
        return f"Read session summary {action.run_id or 'current'}"
    if isinstance(action, ListFilesAction):
        return f"List files {action.path or '.'}"
    if getattr(action, "type", None) == "list_files":
        return f"List files {getattr(action, 'path', None) or '.'}"
    if isinstance(action, FinishAction):
        return "Finish task"
    return str(getattr(action, "type", "Unknown action"))


def build_action_target(action: object) -> str:
    if isinstance(
        action,
        (WriteFileAction, EditFileAction, MultiEditAction, CheckPatchAction, PatchFileAction, DeleteFileAction, ReadFileAction),
    ):
        return action.path
    if isinstance(action, ReplaceLinesAction):
        return f"{action.path}:{action.start_line}-{action.end_line}"
    if isinstance(action, InsertLinesAction):
        return f"{action.path}:{action.line}"
    if isinstance(action, WriteFilesAction):
        return ", ".join(file.path for file in action.files)
    if isinstance(action, ReadFilesAction):
        return ", ".join(action.paths)
    if isinstance(action, ReadFileRangesAction):
        return ", ".join(f"{item.path}:{item.start_line}+{item.line_count}" for item in action.ranges)
    if isinstance(action, FileInfoAction):
        return ", ".join(action.paths)
    if isinstance(action, PythonSymbolsAction):
        return ", ".join(action.paths)
    if isinstance(action, PythonCheckAction):
        return action.path or "."
    if isinstance(action, PythonDependenciesAction):
        return action.path or "."
    if isinstance(action, PythonDefinitionsAction):
        return f"{action.symbol} in {action.path or '.'}"
    if isinstance(action, ReplacePythonDefinitionAction):
        return f"{action.symbol} in {action.path or '.'}"
    if isinstance(action, PythonCallsAction):
        return f"{action.symbol} in {action.path or '.'}"
    if isinstance(action, PythonCallGraphAction):
        return action.path or "."
    if isinstance(action, PythonReferencesAction):
        return f"{action.symbol} in {action.path or '.'}"
    if isinstance(action, (CheckPatchesAction, PatchFilesAction)):
        return "multiple files"
    if isinstance(action, MoveFileAction):
        return f"{action.source} -> {action.destination}"
    if isinstance(action, RunCommandAction):
        return f"{action.command} (cwd: {action.cwd or '.'})"
    if isinstance(action, StartCommandAction):
        return f"{action.command} (cwd: {action.cwd or '.'})"
    if isinstance(action, (ReadProcessAction, StopProcessAction)):
        return action.process_id
    if isinstance(action, ListProcessesAction):
        return "background processes"
    if isinstance(action, RepoMapAction):
        return action.path or "."
    if isinstance(action, SearchAction):
        return action.query
    if isinstance(action, GlobAction):
        return action.pattern
    if isinstance(action, ListTreeAction):
        return action.path or "."
    if isinstance(action, GitStatusAction):
        return "git status"
    if isinstance(action, GitChangesAction):
        return "git changes"
    if isinstance(action, ReviewChangesAction):
        return "changed files"
    if isinstance(action, SuggestChecksAction):
        return "check commands"
    if isinstance(action, GitDiffAction):
        return action.path or ("staged changes" if action.staged else "working tree")
    if isinstance(action, GitLogAction):
        return action.path or f"last {action.max_count} commits"
    if isinstance(action, GitShowAction):
        return f"{action.rev}{f' -- {action.path}' if action.path else ''}"
    if isinstance(action, GitBlameAction):
        if action.start_line is not None:
            return f"{action.path}:{action.start_line}+{action.line_count or 120}"
        return action.path
    if isinstance(action, SessionSummaryAction):
        return action.run_id or "current session"
    if isinstance(action, UpdatePlanAction):
        current = next((item.step for item in action.plan if item.status == "in_progress"), None)
        return current or "plan"
    if getattr(action, "type", None) == "list_files":
        return str(getattr(action, "path", None) or ".")
    if isinstance(action, FinishAction):
        return "finish"
    return ""


def build_approval_request(action: object) -> ApprovalRequest | None:
    if isinstance(action, WriteFileAction):
        return ApprovalRequest(
            action_type="write_file",
            target=action.path,
            risk="This will create or replace a file in the active project.",
        )
    if isinstance(action, WriteFilesAction):
        return ApprovalRequest(
            action_type="write_files",
            target=", ".join(file.path for file in action.files),
            risk="This will create or replace multiple files in the active project.",
        )
    if isinstance(action, EditFileAction):
        return ApprovalRequest(
            action_type="edit_file",
            target=action.path,
            risk="This will modify an existing file in the active project.",
        )
    if isinstance(action, MultiEditAction):
        return ApprovalRequest(
            action_type="multi_edit_file",
            target=action.path,
            risk="This will apply multiple exact replacements to an existing file in the active project.",
        )
    if isinstance(action, ReplacePythonDefinitionAction):
        return ApprovalRequest(
            action_type="replace_python_definition",
            target=f"{action.symbol} in {action.path or '.'}",
            risk="This will replace a full Python class/function definition in the active project.",
        )
    if isinstance(action, ReplaceLinesAction):
        return ApprovalRequest(
            action_type="replace_lines",
            target=f"{action.path}:{action.start_line}-{action.end_line}",
            risk="This will replace a line range in an existing file in the active project.",
        )
    if isinstance(action, InsertLinesAction):
        return ApprovalRequest(
            action_type="insert_lines",
            target=f"{action.path}:{action.line}",
            risk="This will insert text into an existing file in the active project.",
        )
    if isinstance(action, PatchFileAction):
        return ApprovalRequest(
            action_type="patch_file",
            target=action.path,
            risk="This will apply a unified diff patch to an existing file in the active project.",
        )
    if isinstance(action, PatchFilesAction):
        return ApprovalRequest(
            action_type="patch_files",
            target="multiple files",
            risk="This will apply a multi-file unified diff patch to existing files in the active project.",
        )
    if isinstance(action, DeleteFileAction):
        return ApprovalRequest(
            action_type="delete_file",
            target=action.path,
            risk="This will delete an existing file in the active project.",
        )
    if isinstance(action, MoveFileAction):
        return ApprovalRequest(
            action_type="move_file",
            target=f"{action.source} -> {action.destination}",
            risk="This will move or rename an existing file in the active project.",
        )
    if isinstance(action, RunCommandAction):
        return ApprovalRequest(
            action_type="run_command",
            target=f"{action.command} (cwd: {action.cwd or '.'})",
            risk="This will run a shell command from the active project directory.",
        )
    if isinstance(action, StartCommandAction):
        return ApprovalRequest(
            action_type="start_command",
            target=f"{action.command} (cwd: {action.cwd or '.'})",
            risk="This will start a background shell command from the active project directory.",
        )
    return None


def request_approval(handler: ApprovalHandler | None, request: ApprovalRequest) -> ApprovalDecision:
    if handler is None:
        return ApprovalDecision(approved=False, message="No approval handler configured.")
    return handler(request)


def summarize_approval_request(request: ApprovalRequest) -> str:
    return f"{request.action_type} {summarize(request.target, 120)}"


def summarize_approval_decision(request: ApprovalRequest, decision: ApprovalDecision) -> str:
    message = decision.message or ("approved" if decision.approved else "denied")
    return f"{request.action_type} {summarize(request.target, 80)}: {summarize(message, 120)}"


def observation_failed(observation: Observation) -> bool:
    if observation.kind in {"tool_error", "approval_denied"}:
        return True
    if observation.kind == "write_file":
        return not observation.ok
    if observation.kind == "write_files":
        return not observation.ok
    if observation.kind == "edit_file":
        return not observation.ok
    if observation.kind == "multi_edit_file":
        return not observation.ok
    if observation.kind == "replace_python_definition":
        return not observation.ok
    if observation.kind == "replace_lines":
        return not observation.ok
    if observation.kind == "insert_lines":
        return not observation.ok
    if observation.kind == "check_patch":
        return not observation.ok
    if observation.kind == "check_patches":
        return not observation.ok
    if observation.kind == "patch_file":
        return not observation.ok
    if observation.kind == "patch_files":
        return not observation.ok
    if observation.kind == "delete_file":
        return not observation.ok
    if observation.kind == "move_file":
        return not observation.ok
    if observation.kind == "run_command":
        return observation.result.exit_code != 0 or observation.result.timed_out
    if observation.kind in {"start_command", "read_process", "stop_process"}:
        return not observation.ok
    if observation.kind == "list_processes":
        return False
    if observation.kind == "update_plan":
        return False
    if observation.kind == "repo_map":
        return not observation.ok
    if observation.kind == "read_file":
        return not observation.message.startswith("Read ")
    if observation.kind == "read_files":
        return any(not item.ok for item in observation.files)
    if observation.kind == "read_file_ranges":
        return any(not item.ok for item in observation.ranges)
    if observation.kind == "file_info":
        return any(not item.ok for item in observation.files)
    if observation.kind == "python_symbols":
        return any(not item.ok for item in observation.files)
    if observation.kind == "python_check":
        return not observation.ok
    if observation.kind == "python_dependencies":
        return not observation.ok
    if observation.kind == "python_definitions":
        return not observation.ok
    if observation.kind == "python_calls":
        return not observation.ok
    if observation.kind == "python_call_graph":
        return not observation.ok
    if observation.kind == "python_references":
        return not observation.ok
    if observation.kind == "search":
        return not observation.message.startswith("Found ")
    if observation.kind == "glob":
        return not observation.ok
    if observation.kind == "list_tree":
        return not observation.ok
    if observation.kind == "list_files":
        return not observation.message.startswith(("Found ", "Already listed "))
    if observation.kind == "git_status":
        return not observation.ok
    if observation.kind == "git_changes":
        return not observation.ok
    if observation.kind == "review_changes":
        return not observation.ok
    if observation.kind == "suggest_checks":
        return not observation.ok
    if observation.kind == "git_diff":
        return not observation.ok
    if observation.kind == "git_log":
        return not observation.ok
    if observation.kind == "git_show":
        return not observation.ok
    if observation.kind == "git_blame":
        return not observation.ok
    if observation.kind == "session_summary":
        return not observation.ok
    return False


def observation_summary(observation: Observation) -> str:
    if observation.kind == "run_command":
        return summarize_command(observation.result)
    return str(getattr(observation, "message", observation.kind))


def log_action(logger: AgentLogger | None, action: object) -> None:
    if not logger:
        return
    action_type = getattr(action, "type", None)
    if action_type == "list_files":
        logger("listing files", getattr(action, "path", None) or ".")
    elif action_type == "list_tree":
        logger("listing tree", getattr(action, "path", None) or ".")
    elif action_type == "repo_map":
        logger("mapping repo", build_action_target(action))
    elif action_type == "read_file":
        logger("reading file", getattr(action, "path"))
    elif action_type == "read_files":
        logger("reading files", build_action_target(action))
    elif action_type == "read_file_ranges":
        logger("reading file ranges", build_action_target(action))
    elif action_type == "file_info":
        logger("reading file info", build_action_target(action))
    elif action_type == "python_symbols":
        logger("reading python symbols", build_action_target(action))
    elif action_type == "python_check":
        logger("checking python", build_action_target(action))
    elif action_type == "python_dependencies":
        logger("reading python dependencies", build_action_target(action))
    elif action_type == "python_definitions":
        logger("reading python definitions", build_action_target(action))
    elif action_type == "python_calls":
        logger("reading python calls", build_action_target(action))
    elif action_type == "python_call_graph":
        logger("reading python call graph", build_action_target(action))
    elif action_type == "python_references":
        logger("reading python references", build_action_target(action))
    elif action_type == "search":
        logger("searching", getattr(action, "query"))
    elif action_type == "glob":
        logger("globbing", getattr(action, "pattern"))
    elif action_type == "git_status":
        logger("checking git status", None)
    elif action_type == "git_changes":
        logger("reading git changes", None)
    elif action_type == "review_changes":
        logger("reviewing changes", None)
    elif action_type == "suggest_checks":
        logger("suggesting checks", None)
    elif action_type == "git_diff":
        logger("reading git diff", build_action_target(action))
    elif action_type == "git_log":
        logger("reading git log", build_action_target(action))
    elif action_type == "git_show":
        logger("reading git show", build_action_target(action))
    elif action_type == "git_blame":
        logger("reading git blame", build_action_target(action))
    elif action_type == "session_summary":
        logger("reading session summary", build_action_target(action))
    elif action_type == "edit_file":
        logger("editing file", getattr(action, "path"))
    elif action_type == "multi_edit_file":
        logger("multi-editing file", getattr(action, "path"))
    elif action_type == "replace_python_definition":
        logger("replacing python definition", build_action_target(action))
    elif action_type == "replace_lines":
        logger("replacing lines", build_action_target(action))
    elif action_type == "insert_lines":
        logger("inserting lines", build_action_target(action))
    elif action_type == "check_patch":
        logger("checking patch", getattr(action, "path"))
    elif action_type == "check_patches":
        logger("checking patches", "multiple files")
    elif action_type == "patch_file":
        logger("patching file", getattr(action, "path"))
    elif action_type == "patch_files":
        logger("patching files", "multiple files")
    elif action_type == "delete_file":
        logger("deleting file", getattr(action, "path"))
    elif action_type == "move_file":
        logger("moving file", build_action_target(action))
    elif action_type == "write_file":
        logger("writing file", getattr(action, "path"))
    elif action_type == "write_files":
        logger("writing files", build_action_target(action))
    elif action_type == "run_command":
        logger("running command", build_action_target(action))
    elif action_type == "start_command":
        logger("starting command", build_action_target(action))
    elif action_type == "read_process":
        logger("reading process", getattr(action, "process_id"))
    elif action_type == "list_processes":
        logger("listing processes", None)
    elif action_type == "stop_process":
        logger("stopping process", getattr(action, "process_id"))
    elif action_type == "update_plan":
        logger("updating plan", build_action_target(action))


def normalize_assistant_content(value: Any) -> list[ContentBlock]:
    if isinstance(value, str):
        return [{"type": "text", "text": value}]
    if isinstance(value, list):
        return [dict(block) for block in value if isinstance(block, dict)]
    return []


def content_blocks_to_text(content: list[ContentBlock]) -> str:
    return "".join(block["text"] for block in content if block.get("type") == "text" and isinstance(block.get("text"), str))


def tool_error_observation(tool_name: str, error: ActionParseError) -> Observation:
    return ToolErrorObservation(kind="tool_error", tool=tool_name or "unknown", message=f"Invalid tool input: {error}")


def summarize_command(result: object) -> str:
    exit_code = getattr(result, "exit_code")
    timed_out = getattr(result, "timed_out")
    timeout_ms = getattr(result, "timeout_ms", "unknown")
    truncated = getattr(result, "stdout_truncated", False) or getattr(result, "stderr_truncated", False)
    output = getattr(result, "stderr") or getattr(result, "stdout") or "(no output)"
    return f"exit={exit_code} timedOut={timed_out} timeoutMs={timeout_ms} outputTruncated={truncated} {summarize(output, 300)}"


def append_session_event(session_dir: Path, event_type: str, payload: dict[str, Any]) -> None:
    session_dir.mkdir(parents=True, exist_ok=True)
    event = {"type": event_type, **payload}
    with (session_dir / "events.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(to_jsonable(event), ensure_ascii=False) + "\n")


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return to_jsonable(asdict(value))
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    return value
