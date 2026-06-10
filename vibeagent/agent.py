from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any

from .actions import AGENT_TOOL_DEFINITIONS, ActionParseError, execute_action, parse_tool_action
from .prompts import build_messages
from .types import (
    AgentLogger,
    AppendFileAction,
    ApprovalDecision,
    ApprovalDeniedObservation,
    ApprovalHandler,
    ApprovalRequest,
    ChatClient,
    ChatMessage,
    CheckAppendFileAction,
    CheckCreateDirectoryAction,
    CheckCreateDirectoriesAction,
    CheckCopyDirectoryAction,
    CheckCopyDirectoriesAction,
    CheckCopyFileAction,
    CheckCopyFilesAction,
    CheckDeleteEmptyDirectoryAction,
    CheckDeleteEmptyDirectoriesAction,
    CheckDeleteFileAction,
    CheckDeleteFilesAction,
    CheckEditFileAction,
    CheckInsertLinesAction,
    CheckPatchAction,
    CheckPatchesAction,
    CheckMultiEditAction,
    CheckMoveDirectoryAction,
    CheckMoveDirectoriesAction,
    CheckMoveFileAction,
    CheckMoveFilesAction,
    CheckReplaceLinesAction,
    CheckRegexReplaceAction,
    CheckSetExecutableAction,
    CheckStartCommandAction,
    CheckStopAllProcessesAction,
    CheckStopProcessAction,
    CheckWriteProcessAction,
    CheckWriteFileAction,
    CheckWriteFilesAction,
    CodeDependenciesAction,
    CodeDefinitionsAction,
    CodeReferencesAction,
    CodeOutlineAction,
    CheckRunCommandsAction,
    CommandCheckAction,
    ConfigCheckAction,
    ContentBlock,
    CopyDirectoryAction,
    CopyDirectoriesAction,
    CopyFileAction,
    CopyFilesAction,
    CreateDirectoryAction,
    CreateDirectoriesAction,
    DeleteFileAction,
    DeleteFilesAction,
    DeleteEmptyDirectoryAction,
    DeleteEmptyDirectoriesAction,
    EditFileAction,
    EnvironmentInfoAction,
    FileInfoAction,
    FinalReviewAction,
    FinishAction,
    GlobAction,
    CheckGitCommitAction,
    CheckGitFetchAction,
    CheckGitPullAction,
    CheckGitPushAction,
    CheckGitRestoreAction,
    CheckGitStashAction,
    CheckGitStashApplyAction,
    CheckGitStashDropAction,
    CheckGitStageAction,
    CheckGitSwitchAction,
    CheckGitUnstageAction,
    CheckJsonRemoveAction,
    CheckJsonPatchAction,
    CheckJsonSetAction,
    GitBlameAction,
    GitBranchesAction,
    GitChangesAction,
    GitCommitAction,
    GitDiffAction,
    GitDiffHunksAction,
    GitFetchAction,
    GitPullAction,
    GitPushAction,
    GitRestoreAction,
    GitStashAction,
    GitStashApplyAction,
    GitStashDropAction,
    GitStashesAction,
    GitInfoAction,
    GitLogAction,
    GitShowAction,
    GitStageAction,
    GitStatusAction,
    GitSwitchAction,
    GitUnstageAction,
    HttpCheckAction,
    JsonRemoveAction,
    JsonPatchAction,
    JsonSetAction,
    InsertLinesAction,
    ListFilesAction,
    ListFilesObservation,
    ListProcessesAction,
    ListTreeAction,
    MoveDirectoryAction,
    MoveDirectoriesAction,
    MoveFileAction,
    MoveFilesAction,
    MultiEditAction,
    Observation,
    PatchFileAction,
    PatchFilesAction,
    PlanItem,
    PortCheckAction,
    ProjectOverviewAction,
    PythonCheckAction,
    PythonCallGraphAction,
    PythonCallsAction,
    PythonDependenciesAction,
    PythonDefinitionsAction,
    CheckReplacePythonDefinitionAction,
    ReplacePythonDefinitionAction,
    PythonReferencesAction,
    PythonRenameAction,
    PythonRenamePreviewAction,
    PythonSymbolsAction,
    ProjectCommandsAction,
    ProjectManifestsAction,
    ReadFileAction,
    ReadFileRangesAction,
    ReadFilesAction,
    ReadProcessAction,
    RegexReplaceAction,
    ReplaceLinesAction,
    ReviewChangesAction,
    RepoMapAction,
    RunCommandObservation,
    RunCommandAction,
    RunCommandsAction,
    SearchAction,
    SessionSummaryAction,
    SetExecutableAction,
    StartCommandAction,
    StopAllProcessesAction,
    StopProcessAction,
    SuggestChecksAction,
    TaskStep,
    ToolErrorObservation,
    UpdatePlanAction,
    WaitProcessAction,
    WriteFileAction,
    WriteFilesAction,
    WriteProcessAction,
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
        model_event: dict[str, Any] = {"iteration": iteration, "content": assistant_content}
        response_usage = response.usage if hasattr(response, "usage") else None
        if response_usage is not None:
            model_event["usage"] = asdict(response_usage) if is_dataclass(response_usage) else response_usage
        append_session_event(current_workspace.session_dir, "model", model_event)
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
    if isinstance(action, CheckWriteFileAction):
        return f"Check write {action.path}"
    if isinstance(action, WriteFileAction):
        return f"Write {action.path}"
    if isinstance(action, CheckWriteFilesAction):
        return f"Check write {len(action.files)} files"
    if isinstance(action, WriteFilesAction):
        return f"Write {len(action.files)} files"
    if isinstance(action, CheckEditFileAction):
        return f"Check edit {action.path}"
    if isinstance(action, EditFileAction):
        return f"Edit {action.path}"
    if isinstance(action, CheckMultiEditAction):
        return f"Check multi-edit {action.path}"
    if isinstance(action, MultiEditAction):
        return f"Multi-edit {action.path}"
    if isinstance(action, CheckReplaceLinesAction):
        return f"Check replace lines {action.start_line}-{action.end_line} in {action.path}"
    if isinstance(action, ReplaceLinesAction):
        return f"Replace lines {action.start_line}-{action.end_line} in {action.path}"
    if isinstance(action, CheckInsertLinesAction):
        return f"Check insert lines before {action.line} in {action.path}"
    if isinstance(action, InsertLinesAction):
        return f"Insert lines before {action.line} in {action.path}"
    if isinstance(action, CheckAppendFileAction):
        return f"Check append to {action.path}"
    if isinstance(action, AppendFileAction):
        return f"Append to {action.path}"
    if isinstance(action, RegexReplaceAction):
        return f"Regex replace in {action.path}"
    if isinstance(action, CheckRegexReplaceAction):
        return f"Check regex replace in {action.path}"
    if isinstance(action, CheckPatchAction):
        return f"Check patch {action.path}"
    if isinstance(action, CheckPatchesAction):
        return "Check patches"
    if isinstance(action, PatchFileAction):
        return f"Patch {action.path}"
    if isinstance(action, PatchFilesAction):
        return "Patch files"
    if isinstance(action, CheckDeleteFileAction):
        return f"Check delete {action.path}"
    if isinstance(action, DeleteFileAction):
        return f"Delete {action.path}"
    if isinstance(action, CheckDeleteFilesAction):
        return f"Check delete {len(action.paths)} file(s)"
    if isinstance(action, DeleteFilesAction):
        return f"Delete {len(action.paths)} file(s)"
    if isinstance(action, CheckMoveFileAction):
        return f"Check move {action.source}"
    if isinstance(action, MoveFileAction):
        return f"Move {action.source}"
    if isinstance(action, CheckMoveFilesAction):
        return f"Check move {len(action.transfers)} file(s)"
    if isinstance(action, MoveFilesAction):
        return f"Move {len(action.transfers)} file(s)"
    if isinstance(action, CheckCopyFileAction):
        return f"Check copy {action.source}"
    if isinstance(action, CopyFileAction):
        return f"Copy {action.source}"
    if isinstance(action, CheckCopyFilesAction):
        return f"Check copy {len(action.transfers)} file(s)"
    if isinstance(action, CopyFilesAction):
        return f"Copy {len(action.transfers)} file(s)"
    if isinstance(action, CheckMoveDirectoryAction):
        return f"Check move directory {action.source}"
    if isinstance(action, MoveDirectoryAction):
        return f"Move directory {action.source}"
    if isinstance(action, CheckMoveDirectoriesAction):
        return f"Check move {len(action.transfers)} directories"
    if isinstance(action, MoveDirectoriesAction):
        return f"Move {len(action.transfers)} directories"
    if isinstance(action, CheckCopyDirectoryAction):
        return f"Check copy directory {action.source}"
    if isinstance(action, CopyDirectoryAction):
        return f"Copy directory {action.source}"
    if isinstance(action, CheckCopyDirectoriesAction):
        return f"Check copy {len(action.transfers)} directories"
    if isinstance(action, CopyDirectoriesAction):
        return f"Copy {len(action.transfers)} directories"
    if isinstance(action, CheckCreateDirectoryAction):
        return f"Check create directory {action.path}"
    if isinstance(action, CreateDirectoryAction):
        return f"Create directory {action.path}"
    if isinstance(action, CheckCreateDirectoriesAction):
        return f"Check create {len(action.paths)} directories"
    if isinstance(action, CreateDirectoriesAction):
        return f"Create {len(action.paths)} directories"
    if isinstance(action, CheckDeleteEmptyDirectoryAction):
        return f"Check delete empty directory {action.path}"
    if isinstance(action, DeleteEmptyDirectoryAction):
        return f"Delete empty directory {action.path}"
    if isinstance(action, CheckDeleteEmptyDirectoriesAction):
        return f"Check delete {len(action.paths)} empty directories"
    if isinstance(action, DeleteEmptyDirectoriesAction):
        return f"Delete {len(action.paths)} empty directories"
    if isinstance(action, CheckSetExecutableAction):
        state = "executable" if action.executable else "not executable"
        return f"Check set {action.path} {state}"
    if isinstance(action, SetExecutableAction):
        state = "executable" if action.executable else "not executable"
        return f"Set {action.path} {state}"
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
    if isinstance(action, CheckStopAllProcessesAction):
        return "Check stop all background processes"
    if isinstance(action, StopProcessAction):
        return f"Stop process {action.process_id}"
    if isinstance(action, StopAllProcessesAction):
        return "Stop all background processes"
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
    if isinstance(action, CodeOutlineAction):
        return f"Read code outlines for {len(action.paths)} files"
    if isinstance(action, PythonCheckAction):
        return f"Check Python {action.path or '.'}"
    if isinstance(action, ConfigCheckAction):
        return f"Check config {action.path or '.'}"
    if isinstance(action, CheckJsonSetAction):
        return f"Check JSON set {action.path} {action.pointer}"
    if isinstance(action, JsonSetAction):
        return f"Set JSON {action.path} {action.pointer}"
    if isinstance(action, CheckJsonRemoveAction):
        return f"Check JSON remove {action.path} {action.pointer}"
    if isinstance(action, JsonRemoveAction):
        return f"Remove JSON {action.path} {action.pointer}"
    if isinstance(action, CheckJsonPatchAction):
        return f"Check JSON patch {action.path}"
    if isinstance(action, JsonPatchAction):
        return f"Patch JSON {action.path}"
    if isinstance(action, PythonDependenciesAction):
        return f"Read Python dependencies {action.path or '.'}"
    if isinstance(action, PythonDefinitionsAction):
        return f"Read Python definitions {action.symbol}"
    if isinstance(action, CheckReplacePythonDefinitionAction):
        return f"Check replace Python definition {action.symbol}"
    if isinstance(action, ReplacePythonDefinitionAction):
        return f"Replace Python definition {action.symbol}"
    if isinstance(action, PythonCallsAction):
        return f"Read Python calls {action.symbol}"
    if isinstance(action, PythonCallGraphAction):
        return f"Read Python call graph {action.path or '.'}"
    if isinstance(action, PythonReferencesAction):
        return f"Find Python references {action.symbol}"
    if isinstance(action, PythonRenamePreviewAction):
        return f"Preview Python rename {action.symbol} to {action.new_name}"
    if isinstance(action, PythonRenameAction):
        return f"Rename Python symbol {action.symbol} to {action.new_name}"
    if isinstance(action, SearchAction):
        return f"Search {summarize(action.query, 80)}"
    if isinstance(action, GlobAction):
        return f"Find files {summarize(action.pattern, 80)}"
    if isinstance(action, ListTreeAction):
        return f"List tree {action.path or '.'}"
    if isinstance(action, GitStatusAction):
        return "Read git status"
    if isinstance(action, GitInfoAction):
        return "Read git info"
    if isinstance(action, GitChangesAction):
        return "Read git changes"
    if isinstance(action, GitBranchesAction):
        return "Read git branches"
    if isinstance(action, CheckGitFetchAction):
        return f"Check git fetch {action.remote or 'default remote'}"
    if isinstance(action, GitFetchAction):
        return f"Fetch git remote {action.remote or 'default remote'}"
    if isinstance(action, CheckGitPullAction):
        return "Check git pull"
    if isinstance(action, GitPullAction):
        return "Pull git upstream"
    if isinstance(action, CheckGitPushAction):
        return "Check git push"
    if isinstance(action, GitPushAction):
        return "Push git upstream"
    if isinstance(action, CheckGitRestoreAction):
        return f"Check restore {len(action.paths)} git path(s)"
    if isinstance(action, GitRestoreAction):
        return f"Restore {len(action.paths)} git path(s)"
    if isinstance(action, GitStashesAction):
        return "Read git stashes"
    if isinstance(action, CheckGitStashAction):
        return "Check git stash"
    if isinstance(action, GitStashAction):
        return "Stash git changes"
    if isinstance(action, CheckGitStashApplyAction):
        return f"Check apply {action.stash_ref}"
    if isinstance(action, GitStashApplyAction):
        return f"Apply {action.stash_ref}"
    if isinstance(action, CheckGitStashDropAction):
        return f"Check drop {action.stash_ref}"
    if isinstance(action, GitStashDropAction):
        return f"Drop {action.stash_ref}"
    if isinstance(action, CheckGitSwitchAction):
        return f"Check git switch {action.branch}"
    if isinstance(action, GitSwitchAction):
        return f"Switch git branch {action.branch}"
    if isinstance(action, CheckGitStageAction):
        return f"Check stage {len(action.paths)} git path(s)"
    if isinstance(action, GitStageAction):
        return f"Stage {len(action.paths)} git path(s)"
    if isinstance(action, CheckGitUnstageAction):
        return f"Check unstage {len(action.paths)} git path(s)"
    if isinstance(action, GitUnstageAction):
        return f"Unstage {len(action.paths)} git path(s)"
    if isinstance(action, CheckGitCommitAction):
        return "Check commit staged changes"
    if isinstance(action, GitCommitAction):
        return "Commit staged changes"
    if isinstance(action, ReviewChangesAction):
        return "Review changes"
    if isinstance(action, FinalReviewAction):
        return "Final review"
    if isinstance(action, SuggestChecksAction):
        return "Suggest checks"
    if isinstance(action, ProjectOverviewAction):
        return "Read project overview"
    if isinstance(action, CommandCheckAction):
        return f"Check command {summarize(action.command, 80)}"
    if isinstance(action, CheckRunCommandsAction):
        return f"Check {len(action.commands)} commands"
    if isinstance(action, CheckStartCommandAction):
        return f"Check start command {summarize(action.command, 80)}"
    if isinstance(action, PortCheckAction):
        return f"Check port {action.host}:{action.port}"
    if isinstance(action, HttpCheckAction):
        return f"Check HTTP {summarize(action.url, 80)}"
    if isinstance(action, CheckStopProcessAction):
        return f"Check stop process {action.process_id}"
    if isinstance(action, CheckStopAllProcessesAction):
        return "Check stop all background processes"
    if isinstance(action, WaitProcessAction):
        return f"Wait for process {action.process_id}"
    if isinstance(action, CheckWriteProcessAction):
        return f"Check process input {action.process_id}"
    if isinstance(action, WriteProcessAction):
        return f"Write process input {action.process_id}"
    if isinstance(action, EnvironmentInfoAction):
        return "Read environment info"
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
        (
            WriteFileAction,
            CheckWriteFileAction,
            CheckEditFileAction,
            EditFileAction,
            CheckMultiEditAction,
            MultiEditAction,
            CheckReplaceLinesAction,
            CheckPatchAction,
            PatchFileAction,
            CheckDeleteFileAction,
            DeleteFileAction,
            ReadFileAction,
        ),
    ):
        return action.path
    if isinstance(action, (CheckDeleteFilesAction, DeleteFilesAction)):
        return ", ".join(action.paths)
    if isinstance(action, ReplaceLinesAction):
        return f"{action.path}:{action.start_line}-{action.end_line}"
    if isinstance(action, CheckInsertLinesAction):
        return f"{action.path}:{action.line}"
    if isinstance(action, InsertLinesAction):
        return f"{action.path}:{action.line}"
    if isinstance(action, CheckAppendFileAction):
        return action.path
    if isinstance(action, AppendFileAction):
        return action.path
    if isinstance(action, RegexReplaceAction):
        return action.path
    if isinstance(action, CheckRegexReplaceAction):
        return action.path
    if isinstance(action, (CheckWriteFilesAction, WriteFilesAction)):
        return ", ".join(file.path for file in action.files)
    if isinstance(action, ReadFilesAction):
        return ", ".join(action.paths)
    if isinstance(action, ReadFileRangesAction):
        return ", ".join(f"{item.path}:{item.start_line}+{item.line_count}" for item in action.ranges)
    if isinstance(action, FileInfoAction):
        return ", ".join(action.paths)
    if isinstance(action, PythonSymbolsAction):
        return ", ".join(action.paths)
    if isinstance(action, CodeOutlineAction):
        return ", ".join(action.paths)
    if isinstance(action, PythonCheckAction):
        return action.path or "."
    if isinstance(action, ConfigCheckAction):
        return action.path or "."
    if isinstance(action, (CheckJsonSetAction, JsonSetAction, CheckJsonRemoveAction, JsonRemoveAction)):
        return f"{action.path} {action.pointer}"
    if isinstance(action, (CheckJsonPatchAction, JsonPatchAction)):
        return f"{action.path} ({len(action.operations)} operations)"
    if isinstance(action, PythonDependenciesAction):
        return action.path or "."
    if isinstance(action, PythonDefinitionsAction):
        return f"{action.symbol} in {action.path or '.'}"
    if isinstance(action, (CheckReplacePythonDefinitionAction, ReplacePythonDefinitionAction)):
        return f"{action.symbol} in {action.path or '.'}"
    if isinstance(action, PythonCallsAction):
        return f"{action.symbol} in {action.path or '.'}"
    if isinstance(action, PythonCallGraphAction):
        return action.path or "."
    if isinstance(action, PythonReferencesAction):
        return f"{action.symbol} in {action.path or '.'}"
    if isinstance(action, PythonRenamePreviewAction):
        return f"{action.symbol} -> {action.new_name} in {action.path or '.'}"
    if isinstance(action, PythonRenameAction):
        return f"{action.symbol} -> {action.new_name} in {action.path or '.'}"
    if isinstance(action, CheckMultiEditAction):
        return action.path
    if isinstance(action, CheckReplaceLinesAction):
        return f"{action.path}:{action.start_line}-{action.end_line}"
    if isinstance(action, (CheckPatchesAction, PatchFilesAction)):
        return "multiple files"
    if isinstance(action, (CheckMoveFileAction, MoveFileAction)):
        return f"{action.source} -> {action.destination}"
    if isinstance(action, (CheckMoveFilesAction, MoveFilesAction)):
        return ", ".join(f"{transfer.source} -> {transfer.destination}" for transfer in action.transfers)
    if isinstance(action, (CheckCopyFileAction, CopyFileAction)):
        return f"{action.source} -> {action.destination}"
    if isinstance(action, (CheckCopyFilesAction, CopyFilesAction)):
        return ", ".join(f"{transfer.source} -> {transfer.destination}" for transfer in action.transfers)
    if isinstance(action, (CheckMoveDirectoryAction, MoveDirectoryAction)):
        return f"{action.source} -> {action.destination}"
    if isinstance(action, (CheckMoveDirectoriesAction, MoveDirectoriesAction)):
        return ", ".join(f"{transfer.source} -> {transfer.destination}" for transfer in action.transfers)
    if isinstance(action, (CheckCopyDirectoryAction, CopyDirectoryAction)):
        return f"{action.source} -> {action.destination}"
    if isinstance(action, (CheckCopyDirectoriesAction, CopyDirectoriesAction)):
        return ", ".join(f"{transfer.source} -> {transfer.destination}" for transfer in action.transfers)
    if isinstance(action, (CheckCreateDirectoryAction, CreateDirectoryAction, CheckDeleteEmptyDirectoryAction, DeleteEmptyDirectoryAction)):
        return action.path
    if isinstance(action, (CheckCreateDirectoriesAction, CreateDirectoriesAction)):
        return ", ".join(action.paths)
    if isinstance(action, (CheckDeleteEmptyDirectoriesAction, DeleteEmptyDirectoriesAction)):
        return ", ".join(action.paths)
    if isinstance(action, (CheckSetExecutableAction, SetExecutableAction)):
        return action.path
    if isinstance(action, RunCommandAction):
        return f"{action.command} (cwd: {action.cwd or '.'})"
    if isinstance(action, RunCommandsAction):
        return ", ".join(f"{item.command} (cwd: {item.cwd or '.'})" for item in action.commands)
    if isinstance(action, StartCommandAction):
        return f"{action.command} (cwd: {action.cwd or '.'})"
    if isinstance(action, (ReadProcessAction, StopProcessAction)):
        return action.process_id
    if isinstance(action, (ListProcessesAction, CheckStopAllProcessesAction, StopAllProcessesAction)):
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
    if isinstance(action, GitInfoAction):
        return "git info"
    if isinstance(action, GitChangesAction):
        return "git changes"
    if isinstance(action, GitBranchesAction):
        return "git branches"
    if isinstance(action, (CheckGitFetchAction, GitFetchAction)):
        return action.remote or "default remote"
    if isinstance(action, (CheckGitPullAction, GitPullAction)):
        return "current branch upstream"
    if isinstance(action, (CheckGitPushAction, GitPushAction)):
        return "current branch upstream"
    if isinstance(action, (CheckGitRestoreAction, GitRestoreAction)):
        return ", ".join(action.paths)
    if isinstance(action, GitStashesAction):
        return "git stashes"
    if isinstance(action, (CheckGitStashAction, GitStashAction)):
        return action.message or "vibeagent stash"
    if isinstance(action, (CheckGitStashApplyAction, GitStashApplyAction, CheckGitStashDropAction, GitStashDropAction)):
        return action.stash_ref
    if isinstance(action, (CheckGitSwitchAction, GitSwitchAction)):
        return f"{action.branch}{' (create)' if action.create else ''}"
    if isinstance(action, ReviewChangesAction):
        return "changed files"
    if isinstance(action, FinalReviewAction):
        return "final review"
    if isinstance(action, SuggestChecksAction):
        return "check commands"
    if isinstance(action, ProjectCommandsAction):
        return "project commands"
    if isinstance(action, ProjectManifestsAction):
        return "project manifests"
    if isinstance(action, ProjectOverviewAction):
        return "project overview"
    if isinstance(action, CodeDependenciesAction):
        return action.path or "."
    if isinstance(action, CodeReferencesAction):
        return f"{action.symbol} in {action.path or '.'}"
    if isinstance(action, CodeDefinitionsAction):
        return f"{action.symbol} in {action.path or '.'}"
    if isinstance(action, CommandCheckAction):
        return f"{action.command} (cwd: {action.cwd or '.'})"
    if isinstance(action, PortCheckAction):
        return f"{action.host}:{action.port}"
    if isinstance(action, HttpCheckAction):
        return action.url
    if isinstance(action, EnvironmentInfoAction):
        return "runtime environment"
    if isinstance(action, GitDiffAction):
        return action.path or ("staged changes" if action.staged else "working tree")
    if isinstance(action, GitDiffHunksAction):
        return action.path or ("staged changes" if action.staged else "working tree")
    if isinstance(action, GitLogAction):
        return action.path or f"last {action.max_count} commits"
    if isinstance(action, GitShowAction):
        return f"{action.rev}{f' -- {action.path}' if action.path else ''}"
    if isinstance(action, GitBlameAction):
        if action.start_line is not None:
            return f"{action.path}:{action.start_line}+{action.line_count or 120}"
        return action.path
    if isinstance(action, (CheckGitStageAction, GitStageAction, CheckGitUnstageAction, GitUnstageAction)):
        return ", ".join(action.paths)
    if isinstance(action, (CheckGitCommitAction, GitCommitAction)):
        return summarize(action.message, 80)
    if isinstance(action, (RunCommandAction, CheckStartCommandAction, StartCommandAction)):
        return f"{action.command} (cwd: {action.cwd or '.'})"
    if isinstance(action, (CheckRunCommandsAction, RunCommandsAction)):
        return ", ".join(f"{item.command} (cwd: {item.cwd or '.'})" for item in action.commands)
    if isinstance(action, (WaitProcessAction, CheckStopProcessAction)):
        return action.process_id
    if isinstance(action, (CheckWriteProcessAction, WriteProcessAction)):
        return f"{action.process_id} ({len(action.content)} chars)"
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
    if isinstance(action, PythonRenameAction):
        return ApprovalRequest(
            action_type="python_rename",
            target=f"{action.symbol} -> {action.new_name} in {action.path or '.'}",
            risk="This will rename Python identifiers across matching project files.",
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
    if isinstance(action, AppendFileAction):
        return ApprovalRequest(
            action_type="append_file",
            target=action.path,
            risk="This will append text to an existing file in the active project.",
        )
    if isinstance(action, RegexReplaceAction):
        return ApprovalRequest(
            action_type="regex_replace",
            target=action.path,
            risk="This will apply a regular expression replacement to an existing file in the active project.",
        )
    if isinstance(action, JsonSetAction):
        return ApprovalRequest(
            action_type="json_set",
            target=f"{action.path} {action.pointer}",
            risk="This will update one value in an existing JSON file in the active project.",
        )
    if isinstance(action, JsonRemoveAction):
        return ApprovalRequest(
            action_type="json_remove",
            target=f"{action.path} {action.pointer}",
            risk="This will remove one value from an existing JSON file in the active project.",
        )
    if isinstance(action, JsonPatchAction):
        return ApprovalRequest(
            action_type="json_patch",
            target=f"{action.path} ({len(action.operations)} operations)",
            risk="This will apply multiple JSON changes to an existing JSON file in the active project.",
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
            risk="This will apply a multi-file unified diff patch to files in the active project.",
        )
    if isinstance(action, DeleteFileAction):
        return ApprovalRequest(
            action_type="delete_file",
            target=action.path,
            risk="This will delete an existing file in the active project.",
        )
    if isinstance(action, DeleteFilesAction):
        return ApprovalRequest(
            action_type="delete_files",
            target=", ".join(action.paths),
            risk="This will delete explicit existing files in the active project.",
        )
    if isinstance(action, MoveFileAction):
        return ApprovalRequest(
            action_type="move_file",
            target=f"{action.source} -> {action.destination}",
            risk="This will move or rename an existing file in the active project.",
        )
    if isinstance(action, MoveFilesAction):
        return ApprovalRequest(
            action_type="move_files",
            target=", ".join(f"{transfer.source} -> {transfer.destination}" for transfer in action.transfers),
            risk="This will move or rename explicit existing files in the active project.",
        )
    if isinstance(action, CopyFileAction):
        return ApprovalRequest(
            action_type="copy_file",
            target=f"{action.source} -> {action.destination}",
            risk="This will copy an existing file to a new path in the active project.",
        )
    if isinstance(action, CopyFilesAction):
        return ApprovalRequest(
            action_type="copy_files",
            target=", ".join(f"{transfer.source} -> {transfer.destination}" for transfer in action.transfers),
            risk="This will copy explicit existing files to new paths in the active project.",
        )
    if isinstance(action, MoveDirectoryAction):
        return ApprovalRequest(
            action_type="move_dir",
            target=f"{action.source} -> {action.destination}",
            risk="This will move or rename an existing directory in the active project.",
        )
    if isinstance(action, MoveDirectoriesAction):
        return ApprovalRequest(
            action_type="move_dirs",
            target=", ".join(f"{transfer.source} -> {transfer.destination}" for transfer in action.transfers),
            risk="This will move or rename one or more existing directories in the active project.",
        )
    if isinstance(action, CopyDirectoryAction):
        return ApprovalRequest(
            action_type="copy_dir",
            target=f"{action.source} -> {action.destination}",
            risk="This will copy an existing directory tree in the active project.",
        )
    if isinstance(action, CopyDirectoriesAction):
        return ApprovalRequest(
            action_type="copy_dirs",
            target=", ".join(f"{transfer.source} -> {transfer.destination}" for transfer in action.transfers),
            risk="This will copy one or more existing directory trees in the active project.",
        )
    if isinstance(action, CreateDirectoryAction):
        return ApprovalRequest(
            action_type="create_dir",
            target=action.path,
            risk="This will create a directory in the active project.",
        )
    if isinstance(action, CreateDirectoriesAction):
        return ApprovalRequest(
            action_type="create_dirs",
            target=", ".join(action.paths),
            risk="This will create one or more directories in the active project.",
        )
    if isinstance(action, DeleteEmptyDirectoryAction):
        return ApprovalRequest(
            action_type="delete_empty_dir",
            target=action.path,
            risk="This will delete one empty directory in the active project.",
        )
    if isinstance(action, DeleteEmptyDirectoriesAction):
        return ApprovalRequest(
            action_type="delete_empty_dirs",
            target=", ".join(action.paths),
            risk="This will delete one or more empty directories in the active project.",
        )
    if isinstance(action, SetExecutableAction):
        state = "add executable bits to" if action.executable else "remove executable bits from"
        return ApprovalRequest(
            action_type="set_executable",
            target=action.path,
            risk=f"This will {state} one file in the active project.",
        )
    if isinstance(action, GitStageAction):
        return ApprovalRequest(
            action_type="git_stage",
            target=", ".join(action.paths),
            risk="This will modify the git index by staging project paths.",
        )
    if isinstance(action, GitUnstageAction):
        return ApprovalRequest(
            action_type="git_unstage",
            target=", ".join(action.paths),
            risk="This will modify the git index by unstaging project paths.",
        )
    if isinstance(action, GitCommitAction):
        return ApprovalRequest(
            action_type="git_commit",
            target=summarize(action.message, 120),
            risk="This will create a local git commit from currently staged changes without running git hooks.",
        )
    if isinstance(action, GitSwitchAction):
        return ApprovalRequest(
            action_type="git_switch",
            target=f"{action.branch}{' (create)' if action.create else ''}",
            risk="This will change the current git branch in the active project.",
        )
    if isinstance(action, GitFetchAction):
        return ApprovalRequest(
            action_type="git_fetch",
            target=action.remote or "default remote",
            risk="This will contact a git remote and update local remote-tracking refs.",
        )
    if isinstance(action, GitPullAction):
        return ApprovalRequest(
            action_type="git_pull",
            target="current branch upstream",
            risk="This will contact the git remote and fast-forward the current branch.",
        )
    if isinstance(action, GitPushAction):
        return ApprovalRequest(
            action_type="git_push",
            target="current branch upstream",
            risk="This will contact the git remote and push local commits to the configured upstream.",
        )
    if isinstance(action, GitRestoreAction):
        return ApprovalRequest(
            action_type="git_restore",
            target=", ".join(action.paths),
            risk="This will discard unstaged changes in tracked project files.",
        )
    if isinstance(action, GitStashAction):
        return ApprovalRequest(
            action_type="git_stash",
            target=action.message or "vibeagent stash",
            risk="This will move current project changes into the git stash.",
        )
    if isinstance(action, GitStashApplyAction):
        return ApprovalRequest(
            action_type="git_stash_apply",
            target=action.stash_ref,
            risk="This will apply a git stash entry to the current worktree.",
        )
    if isinstance(action, GitStashDropAction):
        return ApprovalRequest(
            action_type="git_stash_drop",
            target=action.stash_ref,
            risk="This will permanently remove a git stash entry.",
        )
    if isinstance(action, RunCommandAction):
        return ApprovalRequest(
            action_type="run_command",
            target=f"{action.command} (cwd: {action.cwd or '.'})",
            risk="This will run a shell command from the active project directory.",
        )
    if isinstance(action, RunCommandsAction):
        return ApprovalRequest(
            action_type="run_commands",
            target=", ".join(f"{item.command} (cwd: {item.cwd or '.'})" for item in action.commands),
            risk="This will run several shell commands sequentially from the active project directory.",
        )
    if isinstance(action, StartCommandAction):
        return ApprovalRequest(
            action_type="start_command",
            target=f"{action.command} (cwd: {action.cwd or '.'})",
            risk="This will start a background shell command from the active project directory.",
        )
    if isinstance(action, WriteProcessAction):
        return ApprovalRequest(
            action_type="write_process",
            target=f"{action.process_id} ({len(action.content)} chars)",
            risk="This will write input to a running background process.",
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
    if observation.kind == "check_write_file":
        return not observation.ok
    if observation.kind == "write_file":
        return not observation.ok
    if observation.kind == "check_write_files":
        return not observation.ok
    if observation.kind == "write_files":
        return not observation.ok
    if observation.kind == "check_edit_file":
        return not observation.ok
    if observation.kind == "edit_file":
        return not observation.ok
    if observation.kind == "check_multi_edit_file":
        return not observation.ok
    if observation.kind == "multi_edit_file":
        return not observation.ok
    if observation.kind == "check_replace_python_definition":
        return not observation.ok
    if observation.kind == "replace_python_definition":
        return not observation.ok
    if observation.kind == "check_replace_lines":
        return not observation.ok
    if observation.kind == "replace_lines":
        return not observation.ok
    if observation.kind == "check_insert_lines":
        return not observation.ok
    if observation.kind == "insert_lines":
        return not observation.ok
    if observation.kind == "check_append_file":
        return not observation.ok
    if observation.kind == "append_file":
        return not observation.ok
    if observation.kind == "regex_replace":
        return not observation.ok
    if observation.kind == "check_regex_replace":
        return not observation.ok
    if observation.kind == "check_json_set":
        return not observation.ok
    if observation.kind == "json_set":
        return not observation.ok
    if observation.kind == "check_json_remove":
        return not observation.ok
    if observation.kind == "json_remove":
        return not observation.ok
    if observation.kind == "check_json_patch":
        return not observation.ok
    if observation.kind == "json_patch":
        return not observation.ok
    if observation.kind == "check_patch":
        return not observation.ok
    if observation.kind == "check_patches":
        return not observation.ok
    if observation.kind == "patch_file":
        return not observation.ok
    if observation.kind == "patch_files":
        return not observation.ok
    if observation.kind == "check_delete_file":
        return not observation.ok
    if observation.kind == "delete_file":
        return not observation.ok
    if observation.kind == "check_delete_files":
        return not observation.ok
    if observation.kind == "delete_files":
        return not observation.ok
    if observation.kind == "check_move_file":
        return not observation.ok
    if observation.kind == "move_file":
        return not observation.ok
    if observation.kind == "check_move_files":
        return not observation.ok
    if observation.kind == "move_files":
        return not observation.ok
    if observation.kind == "check_copy_file":
        return not observation.ok
    if observation.kind == "copy_file":
        return not observation.ok
    if observation.kind == "check_copy_files":
        return not observation.ok
    if observation.kind == "copy_files":
        return not observation.ok
    if observation.kind == "check_move_dir":
        return not observation.ok
    if observation.kind == "move_dir":
        return not observation.ok
    if observation.kind == "check_move_dirs":
        return not observation.ok
    if observation.kind == "move_dirs":
        return not observation.ok
    if observation.kind == "check_copy_dir":
        return not observation.ok
    if observation.kind == "copy_dir":
        return not observation.ok
    if observation.kind == "check_copy_dirs":
        return not observation.ok
    if observation.kind == "copy_dirs":
        return not observation.ok
    if observation.kind == "check_create_dir":
        return not observation.ok
    if observation.kind == "create_dir":
        return not observation.ok
    if observation.kind == "check_create_dirs":
        return not observation.ok
    if observation.kind == "create_dirs":
        return not observation.ok
    if observation.kind == "check_delete_empty_dir":
        return not observation.ok
    if observation.kind == "delete_empty_dir":
        return not observation.ok
    if observation.kind == "check_delete_empty_dirs":
        return not observation.ok
    if observation.kind == "delete_empty_dirs":
        return not observation.ok
    if observation.kind == "check_set_executable":
        return not observation.ok
    if observation.kind == "set_executable":
        return not observation.ok
    if observation.kind == "run_command":
        return observation.result.exit_code != 0 or observation.result.timed_out
    if observation.kind == "run_commands":
        return not observation.ok
    if observation.kind == "port_check":
        return not observation.ok
    if observation.kind == "http_check":
        return not observation.ok
    if observation.kind in {
        "start_command",
        "read_process",
        "wait_process",
        "check_write_process",
        "write_process",
        "check_stop_all_processes",
        "check_stop_process",
        "stop_all_processes",
        "stop_process",
    }:
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
    if observation.kind == "code_outline":
        return any(not item.ok for item in observation.files)
    if observation.kind == "python_check":
        return not observation.ok
    if observation.kind == "config_check":
        return not observation.ok
    if observation.kind == "python_dependencies":
        return not observation.ok
    if observation.kind == "code_dependencies":
        return not observation.ok
    if observation.kind == "code_references":
        return not observation.ok
    if observation.kind == "code_definitions":
        return not observation.ok
    if observation.kind == "python_definitions":
        return not observation.ok
    if observation.kind == "python_calls":
        return not observation.ok
    if observation.kind == "python_call_graph":
        return not observation.ok
    if observation.kind == "python_references":
        return not observation.ok
    if observation.kind == "python_rename_preview":
        return not observation.ok
    if observation.kind == "python_rename":
        return not observation.ok
    if observation.kind == "search":
        return not observation.ok
    if observation.kind == "glob":
        return not observation.ok
    if observation.kind == "list_tree":
        return not observation.ok
    if observation.kind == "list_files":
        return not observation.message.startswith(("Found ", "Already listed "))
    if observation.kind == "git_status":
        return not observation.ok
    if observation.kind == "git_info":
        return not observation.ok
    if observation.kind == "git_changes":
        return not observation.ok
    if observation.kind == "git_branches":
        return not observation.ok
    if observation.kind == "check_git_fetch":
        return not observation.ok
    if observation.kind == "git_fetch":
        return not observation.ok
    if observation.kind == "check_git_pull":
        return not observation.ok
    if observation.kind == "git_pull":
        return not observation.ok
    if observation.kind == "check_git_push":
        return not observation.ok
    if observation.kind == "git_push":
        return not observation.ok
    if observation.kind == "check_git_restore":
        return not observation.ok
    if observation.kind == "git_restore":
        return not observation.ok
    if observation.kind == "git_stashes":
        return not observation.ok
    if observation.kind == "check_git_stash":
        return not observation.ok
    if observation.kind == "git_stash":
        return not observation.ok
    if observation.kind == "check_git_stash_apply":
        return not observation.ok
    if observation.kind == "git_stash_apply":
        return not observation.ok
    if observation.kind == "check_git_stash_drop":
        return not observation.ok
    if observation.kind == "git_stash_drop":
        return not observation.ok
    if observation.kind == "check_git_switch":
        return not observation.ok
    if observation.kind == "git_switch":
        return not observation.ok
    if observation.kind == "check_git_stage":
        return not observation.ok
    if observation.kind == "git_stage":
        return not observation.ok
    if observation.kind == "check_git_unstage":
        return not observation.ok
    if observation.kind == "git_unstage":
        return not observation.ok
    if observation.kind == "check_git_commit":
        return not observation.ok
    if observation.kind == "git_commit":
        return not observation.ok
    if observation.kind == "review_changes":
        return not observation.ok
    if observation.kind == "final_review":
        return not observation.ok
    if observation.kind == "suggest_checks":
        return not observation.ok
    if observation.kind == "project_commands":
        return not observation.ok
    if observation.kind == "project_manifests":
        return not observation.ok
    if observation.kind == "project_overview":
        return not observation.ok
    if observation.kind == "command_check":
        return not observation.ok
    if observation.kind == "check_run_commands":
        return not observation.ok
    if observation.kind == "check_start_command":
        return not observation.ok
    if observation.kind == "environment_info":
        return not observation.ok
    if observation.kind == "git_diff":
        return not observation.ok
    if observation.kind == "git_diff_hunks":
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
    if observation.kind == "run_commands":
        return observation.message
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
    elif action_type == "code_outline":
        logger("reading code outline", build_action_target(action))
    elif action_type == "python_check":
        logger("checking python", build_action_target(action))
    elif action_type == "config_check":
        logger("checking config", build_action_target(action))
    elif action_type == "python_dependencies":
        logger("reading python dependencies", build_action_target(action))
    elif action_type == "code_dependencies":
        logger("reading code dependencies", build_action_target(action))
    elif action_type == "code_references":
        logger("reading code references", build_action_target(action))
    elif action_type == "code_definitions":
        logger("reading code definitions", build_action_target(action))
    elif action_type == "python_definitions":
        logger("reading python definitions", build_action_target(action))
    elif action_type == "python_calls":
        logger("reading python calls", build_action_target(action))
    elif action_type == "python_call_graph":
        logger("reading python call graph", build_action_target(action))
    elif action_type == "python_references":
        logger("reading python references", build_action_target(action))
    elif action_type == "python_rename_preview":
        logger("previewing python rename", build_action_target(action))
    elif action_type == "python_rename":
        logger("renaming python symbol", build_action_target(action))
    elif action_type == "search":
        logger("searching", getattr(action, "query"))
    elif action_type == "glob":
        logger("globbing", getattr(action, "pattern"))
    elif action_type == "git_status":
        logger("checking git status", None)
    elif action_type == "git_info":
        logger("reading git info", None)
    elif action_type == "git_changes":
        logger("reading git changes", None)
    elif action_type == "git_branches":
        logger("reading git branches", None)
    elif action_type == "check_git_fetch":
        logger("checking git fetch", build_action_target(action))
    elif action_type == "git_fetch":
        logger("fetching git remote", build_action_target(action))
    elif action_type == "check_git_pull":
        logger("checking git pull", build_action_target(action))
    elif action_type == "git_pull":
        logger("pulling git upstream", build_action_target(action))
    elif action_type == "check_git_push":
        logger("checking git push", build_action_target(action))
    elif action_type == "git_push":
        logger("pushing git upstream", build_action_target(action))
    elif action_type == "check_git_restore":
        logger("checking git restore", build_action_target(action))
    elif action_type == "git_restore":
        logger("restoring git paths", build_action_target(action))
    elif action_type == "git_stashes":
        logger("reading git stashes", build_action_target(action))
    elif action_type == "check_git_stash":
        logger("checking git stash", build_action_target(action))
    elif action_type == "git_stash":
        logger("stashing git changes", build_action_target(action))
    elif action_type == "check_git_stash_apply":
        logger("checking git stash apply", build_action_target(action))
    elif action_type == "git_stash_apply":
        logger("applying git stash", build_action_target(action))
    elif action_type == "check_git_stash_drop":
        logger("checking git stash drop", build_action_target(action))
    elif action_type == "git_stash_drop":
        logger("dropping git stash", build_action_target(action))
    elif action_type == "check_git_switch":
        logger("checking git switch", build_action_target(action))
    elif action_type == "git_switch":
        logger("switching git branch", build_action_target(action))
    elif action_type == "check_git_stage":
        logger("checking git stage", build_action_target(action))
    elif action_type == "git_stage":
        logger("staging git paths", build_action_target(action))
    elif action_type == "check_git_unstage":
        logger("checking git unstage", build_action_target(action))
    elif action_type == "git_unstage":
        logger("unstaging git paths", build_action_target(action))
    elif action_type == "check_git_commit":
        logger("checking git commit", build_action_target(action))
    elif action_type == "git_commit":
        logger("committing staged changes", build_action_target(action))
    elif action_type == "review_changes":
        logger("reviewing changes", None)
    elif action_type == "final_review":
        logger("final reviewing changes", None)
    elif action_type == "suggest_checks":
        logger("suggesting checks", None)
    elif action_type == "project_commands":
        logger("reading project commands", None)
    elif action_type == "project_manifests":
        logger("reading project manifests", None)
    elif action_type == "project_overview":
        logger("reading project overview", None)
    elif action_type == "command_check":
        logger("checking command", build_action_target(action))
    elif action_type == "check_run_commands":
        logger("checking commands", build_action_target(action))
    elif action_type == "environment_info":
        logger("reading environment info", None)
    elif action_type == "git_diff":
        logger("reading git diff", build_action_target(action))
    elif action_type == "git_diff_hunks":
        logger("reading git diff hunks", build_action_target(action))
    elif action_type == "git_log":
        logger("reading git log", build_action_target(action))
    elif action_type == "git_show":
        logger("reading git show", build_action_target(action))
    elif action_type == "git_blame":
        logger("reading git blame", build_action_target(action))
    elif action_type == "session_summary":
        logger("reading session summary", build_action_target(action))
    elif action_type == "check_edit_file":
        logger("checking file edit", build_action_target(action))
    elif action_type == "edit_file":
        logger("editing file", getattr(action, "path"))
    elif action_type == "check_multi_edit_file":
        logger("checking multi-edit", build_action_target(action))
    elif action_type == "multi_edit_file":
        logger("multi-editing file", getattr(action, "path"))
    elif action_type == "check_replace_python_definition":
        logger("checking python definition replacement", build_action_target(action))
    elif action_type == "replace_python_definition":
        logger("replacing python definition", build_action_target(action))
    elif action_type == "check_replace_lines":
        logger("checking replace lines", build_action_target(action))
    elif action_type == "replace_lines":
        logger("replacing lines", build_action_target(action))
    elif action_type == "check_insert_lines":
        logger("checking insert lines", build_action_target(action))
    elif action_type == "insert_lines":
        logger("inserting lines", build_action_target(action))
    elif action_type == "check_append_file":
        logger("checking append file", build_action_target(action))
    elif action_type == "append_file":
        logger("appending file", build_action_target(action))
    elif action_type == "regex_replace":
        logger("regex replacing", build_action_target(action))
    elif action_type == "check_regex_replace":
        logger("checking regex replace", build_action_target(action))
    elif action_type == "check_json_set":
        logger("checking json set", build_action_target(action))
    elif action_type == "json_set":
        logger("setting json", build_action_target(action))
    elif action_type == "check_json_remove":
        logger("checking json remove", build_action_target(action))
    elif action_type == "json_remove":
        logger("removing json", build_action_target(action))
    elif action_type == "check_json_patch":
        logger("checking json patch", build_action_target(action))
    elif action_type == "json_patch":
        logger("patching json", build_action_target(action))
    elif action_type == "check_patch":
        logger("checking patch", getattr(action, "path"))
    elif action_type == "check_patches":
        logger("checking patches", "multiple files")
    elif action_type == "patch_file":
        logger("patching file", getattr(action, "path"))
    elif action_type == "patch_files":
        logger("patching files", "multiple files")
    elif action_type == "check_delete_file":
        logger("checking delete file", build_action_target(action))
    elif action_type == "delete_file":
        logger("deleting file", getattr(action, "path"))
    elif action_type == "check_delete_files":
        logger("checking file deletes", build_action_target(action))
    elif action_type == "delete_files":
        logger("deleting files", build_action_target(action))
    elif action_type == "check_move_file":
        logger("checking move file", build_action_target(action))
    elif action_type == "move_file":
        logger("moving file", build_action_target(action))
    elif action_type == "check_move_files":
        logger("checking file moves", build_action_target(action))
    elif action_type == "move_files":
        logger("moving files", build_action_target(action))
    elif action_type == "check_copy_file":
        logger("checking copy file", build_action_target(action))
    elif action_type == "copy_file":
        logger("copying file", build_action_target(action))
    elif action_type == "check_copy_files":
        logger("checking file copies", build_action_target(action))
    elif action_type == "copy_files":
        logger("copying files", build_action_target(action))
    elif action_type == "check_move_dir":
        logger("checking move directory", build_action_target(action))
    elif action_type == "move_dir":
        logger("moving directory", build_action_target(action))
    elif action_type == "check_move_dirs":
        logger("checking directory moves", build_action_target(action))
    elif action_type == "move_dirs":
        logger("moving directories", build_action_target(action))
    elif action_type == "check_copy_dir":
        logger("checking copy directory", build_action_target(action))
    elif action_type == "copy_dir":
        logger("copying directory", build_action_target(action))
    elif action_type == "check_copy_dirs":
        logger("checking directory copies", build_action_target(action))
    elif action_type == "copy_dirs":
        logger("copying directories", build_action_target(action))
    elif action_type == "check_create_dir":
        logger("checking create directory", build_action_target(action))
    elif action_type == "create_dir":
        logger("creating directory", build_action_target(action))
    elif action_type == "check_create_dirs":
        logger("checking directory creates", build_action_target(action))
    elif action_type == "create_dirs":
        logger("creating directories", build_action_target(action))
    elif action_type == "check_delete_empty_dir":
        logger("checking delete empty directory", build_action_target(action))
    elif action_type == "delete_empty_dir":
        logger("deleting empty directory", build_action_target(action))
    elif action_type == "check_delete_empty_dirs":
        logger("checking empty directory deletes", build_action_target(action))
    elif action_type == "delete_empty_dirs":
        logger("deleting empty directories", build_action_target(action))
    elif action_type == "check_set_executable":
        logger("checking executable bit", build_action_target(action))
    elif action_type == "set_executable":
        logger("setting executable bit", build_action_target(action))
    elif action_type == "check_write_file":
        logger("checking file write", build_action_target(action))
    elif action_type == "write_file":
        logger("writing file", getattr(action, "path"))
    elif action_type == "check_write_files":
        logger("checking file writes", build_action_target(action))
    elif action_type == "write_files":
        logger("writing files", build_action_target(action))
    elif action_type == "run_command":
        logger("running command", build_action_target(action))
    elif action_type == "run_commands":
        logger("running commands", build_action_target(action))
    elif action_type == "check_start_command":
        logger("checking start command", build_action_target(action))
    elif action_type == "port_check":
        logger("checking port", build_action_target(action))
    elif action_type == "http_check":
        logger("checking http", build_action_target(action))
    elif action_type == "start_command":
        logger("starting command", build_action_target(action))
    elif action_type == "read_process":
        logger("reading process", getattr(action, "process_id"))
    elif action_type == "wait_process":
        logger("waiting process", getattr(action, "process_id"))
    elif action_type == "check_write_process":
        logger("checking process write", build_action_target(action))
    elif action_type == "write_process":
        logger("writing process", build_action_target(action))
    elif action_type == "list_processes":
        logger("listing processes", None)
    elif action_type == "check_stop_all_processes":
        logger("checking stop all processes", None)
    elif action_type == "check_stop_process":
        logger("checking stop process", getattr(action, "process_id"))
    elif action_type == "stop_all_processes":
        logger("stopping all processes", None)
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
