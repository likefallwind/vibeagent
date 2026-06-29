from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from dataclasses import asdict, dataclass, field, is_dataclass, replace
from pathlib import Path
import time
from typing import Any

from .actions import AGENT_TOOL_DEFINITIONS, ActionParseError, execute_action, parse_tool_action, read_checkpoint_git_head
from .prompts import build_messages
from .session import summarize_session
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
    CheckCheckpointDeleteAction,
    CheckCheckpointPruneAction,
    CheckCheckpointRestoreAction,
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
    CheckpointCreateAction,
    CheckpointDeleteAction,
    CheckpointDiffAction,
    CheckpointListAction,
    CheckpointPruneAction,
    CheckpointRestoreAction,
    CheckpointShowAction,
    CheckpointStatusAction,
    CheckWriteFileAction,
    CheckWriteFilesAction,
    CodeDependenciesAction,
    CodeDefinitionsAction,
    CodeReferenceContextsAction,
    CodeReferencesAction,
    CodeRenameAction,
    CodeRenamePreviewAction,
    CodeOutlineAction,
    CheckRunCommandsAction,
    CheckFocusedTestCommandsAction,
    CheckSuggestedChecksAction,
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
    ImageInfoAction,
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
    GitConflictsAction,
    GitDiffContextsAction,
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
    HttpFetchAction,
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
    OutputContextsAction,
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
    PythonReferenceContextsAction,
    PythonReferencesAction,
    PythonRenameAction,
    PythonRenamePreviewAction,
    PythonSymbolsAction,
    ProjectCommandsAction,
    FocusedTestCommandsAction,
    RelatedTestsAction,
    ProjectInstructionsAction,
    ProjectManifestsAction,
    ReadFileAction,
    ReadFileContextAction,
    ReadFileContextsAction,
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
    RunFocusedTestCommandsAction,
    RunSuggestedChecksAction,
    SearchAction,
    SearchContextsAction,
    SessionAuditAction,
    SessionCommandsAction,
    SessionFilesAction,
    SessionFailuresAction,
    SessionVerificationAction,
    SessionHandoffAction,
    SessionOutputContextsAction,
    SessionOutputDiagnosticsAction,
    SessionPlanAction,
    SessionSearchAction,
    SessionSummaryAction,
    SessionTranscriptAction,
    SetExecutableAction,
    StartCommandAction,
    StopAllProcessesAction,
    StopProcessAction,
    SuggestChecksAction,
    TailFileAction,
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
    status: str = ""
    completion_ready: bool = True
    completion_blockers: list[str] = field(default_factory=list)
    completion_warnings: list[str] = field(default_factory=list)
    verification_checks: list[str] = field(default_factory=list)
    pending_verification_checks: list[str] = field(default_factory=list)
    failed_verification_checks: list[str] = field(default_factory=list)
    completion_blocked_count: int = 0
    latest_completion_blockers: list[str] = field(default_factory=list)
    latest_completion_pending_verification_checks: list[str] = field(default_factory=list)
    latest_completion_failed_verification_checks: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.status:
            return
        status = "failed"
        if self.success:
            status = "completed" if self.completion_ready else "blocked"
        object.__setattr__(self, "status", status)


@dataclass(frozen=True)
class PreparedParallelToolCall:
    tool_id: str
    tool_name: str
    action: object
    step: TaskStep
    repeated_observation: Observation | None = None


PARALLEL_SAFE_TOOL_NAMES = {
    "list_files",
    "list_tree",
    "repo_map",
    "read_file",
    "read_file_context",
    "read_file_contexts",
    "output_contexts",
    "python_traceback",
    "tail_file",
    "read_files",
    "read_file_ranges",
    "file_info",
    "image_info",
    "search",
    "search_contexts",
    "glob",
    "python_symbols",
    "code_outline",
    "python_check",
    "config_check",
    "python_dependencies",
    "code_dependencies",
    "code_references",
    "code_reference_contexts",
    "code_definitions",
    "python_definitions",
    "python_calls",
    "python_call_graph",
    "python_references",
    "python_reference_contexts",
    "git_status",
    "git_conflicts",
    "git_info",
    "git_changes",
    "git_branches",
    "git_stashes",
    "git_diff",
    "git_diff_hunks",
    "git_diff_contexts",
    "git_log",
    "git_show",
    "git_blame",
    "review_changes",
    "final_review",
    "suggest_checks",
    "project_commands",
    "related_tests",
    "focused_test_commands",
    "project_manifests",
    "project_instructions",
    "project_overview",
    "environment_info",
    "command_check",
    "check_run_commands",
    "check_focused_test_commands",
    "check_suggested_checks",
    "check_start_command",
    "port_check",
    "http_check",
    "http_fetch",
    "session_summary",
    "session_plan",
    "session_transcript",
    "session_search",
    "session_commands",
    "session_output_contexts",
    "session_output_diagnostics",
    "session_files",
    "session_failures",
    "session_verification",
    "session_audit",
    "session_handoff",
    "checkpoint_list",
    "checkpoint_show",
    "checkpoint_diff",
    "checkpoint_status",
    "check_checkpoint_restore",
    "check_checkpoint_delete",
    "check_checkpoint_prune",
    "check_write_file",
    "check_write_files",
    "check_edit_file",
    "check_multi_edit_file",
    "check_replace_python_definition",
    "code_rename_preview",
    "python_rename_preview",
    "check_replace_lines",
    "check_insert_lines",
    "check_append_file",
    "check_regex_replace",
    "check_patch",
    "check_patches",
    "check_delete_file",
    "check_delete_files",
    "check_move_file",
    "check_move_files",
    "check_copy_file",
    "check_copy_files",
    "check_move_dir",
    "check_move_dirs",
    "check_copy_dir",
    "check_copy_dirs",
    "check_create_dir",
    "check_create_dirs",
    "check_delete_empty_dir",
    "check_delete_empty_dirs",
    "check_set_executable",
    "check_git_fetch",
    "check_git_pull",
    "check_git_push",
    "check_git_switch",
    "check_git_stage",
    "check_git_unstage",
    "check_git_restore",
    "check_git_stash",
    "check_git_stash_apply",
    "check_git_stash_drop",
    "check_git_commit",
}


PROJECT_CHANGE_OBSERVATION_KINDS = {
    "write_file",
    "write_files",
    "edit_file",
    "multi_edit_file",
    "replace_python_definition",
    "code_rename",
    "python_rename",
    "replace_lines",
    "insert_lines",
    "append_file",
    "regex_replace",
    "json_set",
    "json_remove",
    "json_patch",
    "patch_file",
    "patch_files",
    "delete_file",
    "delete_files",
    "move_file",
    "move_files",
    "copy_file",
    "copy_files",
    "move_dir",
    "move_dirs",
    "copy_dir",
    "copy_dirs",
    "create_dir",
    "create_dirs",
    "delete_empty_dir",
    "delete_empty_dirs",
    "set_executable",
    "git_stage",
    "git_unstage",
    "git_commit",
    "git_restore",
    "checkpoint_restore",
}


MULTISTEP_CODING_FOLLOWUP_KINDS = {
    "run_command",
    "run_commands",
    "run_suggested_checks",
    "run_focused_test_commands",
    "python_check",
    "config_check",
    "command_check",
    "check_run_commands",
    "check_suggested_checks",
    "check_focused_test_commands",
}


def run_agent(
    task: str,
    client: ChatClient,
    base_dir: str | Path | None = None,
    max_iterations: int = 20,
    command_timeout_ms: int = 30_000,
    max_output_tokens: int = 4096,
    model_retries: int = 1,
    model_retry_delay_ms: int = 250,
    model_timeout_ms: int = 120_000,
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
    auto_checkpoint_attempted = False
    append_session_event(
        current_workspace.session_dir,
        "task",
        {"task": task, "prior_context": compact_session_context(prior_context) if prior_context else None},
    )

    for iteration in range(1, max_iterations + 1):
        # Tool loop: provider-neutral tool_call blocks -> local execution -> tool_result blocks.
        if logger:
            logger("thinking", f"iteration {iteration}/{max_iterations}")

        response, model_error_message = complete_with_retries(
            client,
            messages,
            tools=AGENT_TOOL_DEFINITIONS,
            max_output_tokens=max_output_tokens,
            model_retries=model_retries,
            model_retry_delay_ms=model_retry_delay_ms,
            model_timeout_ms=model_timeout_ms,
            iteration=iteration,
            session_dir=current_workspace.session_dir,
            logger=logger,
        )
        if response is None:
            return finish_agent_run(
                current_workspace,
                success=False,
                message=model_error_message or "Model request failed.",
                iterations=iteration,
                observations=observations,
                steps=steps,
                plan=plan,
                command_timeout_ms=command_timeout_ms,
                logger=logger,
            )
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
                feedback = completion_blocked_feedback_if_needed(
                    current_workspace,
                    success=True,
                    message=text,
                    iteration=iteration,
                    max_iterations=max_iterations,
                    observations=observations,
                    plan=plan,
                    command_timeout_ms=command_timeout_ms,
                    logger=logger,
                )
                if feedback is not None:
                    messages.append(ChatMessage(role="user", content=feedback))
                    continue
                if logger:
                    logger("finished", text)
                return finish_agent_run(
                    current_workspace,
                    success=True,
                    message=text,
                    iterations=iteration,
                    observations=observations,
                    steps=steps,
                    plan=plan,
                    command_timeout_ms=command_timeout_ms,
                    logger=logger,
                )
            return finish_agent_run(
                current_workspace,
                success=False,
                message="Model response did not include text or a tool call.",
                iterations=iteration,
                observations=observations,
                steps=steps,
                plan=plan,
                command_timeout_ms=command_timeout_ms,
                logger=logger,
            )

        parallel_tool_results = execute_parallel_tool_call_batch(
            current_workspace,
            tool_calls,
            observations,
            steps,
            iteration,
            command_timeout_ms,
            logger,
        )
        if parallel_tool_results is not None:
            messages.append(ChatMessage(role="user", content=parallel_tool_results))
            continue

        tool_results: list[ContentBlock] = []
        blocked_completion_feedback: str | None = None
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
                        approval_request = attach_approval_preview(approval_request, action, observations)
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
                            if not auto_checkpoint_attempted and should_auto_checkpoint_before_action(current_workspace, action):
                                auto_checkpoint_attempted = True
                                auto_checkpoint = create_auto_checkpoint_before_action(
                                    current_workspace,
                                    action,
                                    steps,
                                    iteration,
                                    command_timeout_ms,
                                    logger,
                                )
                                if auto_checkpoint is not None:
                                    observations.append(auto_checkpoint)
                            observation = execute_action_safely(current_workspace, action, command_timeout_ms, tool_name)
                    else:
                        if not auto_checkpoint_attempted and should_auto_checkpoint_before_action(current_workspace, action):
                            auto_checkpoint_attempted = True
                            auto_checkpoint = create_auto_checkpoint_before_action(
                                current_workspace,
                                action,
                                steps,
                                iteration,
                                command_timeout_ms,
                                logger,
                            )
                            if auto_checkpoint is not None:
                                observations.append(auto_checkpoint)
                        observation = execute_action_safely(current_workspace, action, command_timeout_ms, tool_name)
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
                blocked_completion_feedback = completion_blocked_feedback_if_needed(
                    current_workspace,
                    success=True,
                    message=observation.message,
                    iteration=iteration,
                    max_iterations=max_iterations,
                    observations=observations,
                    plan=plan,
                    command_timeout_ms=command_timeout_ms,
                    logger=logger,
                )
                if blocked_completion_feedback is not None:
                    break
                if logger:
                    logger("finished", observation.message)
                return finish_agent_run(
                    current_workspace,
                    success=True,
                    message=observation.message,
                    iterations=iteration,
                    observations=observations,
                    steps=steps,
                    plan=plan,
                    command_timeout_ms=command_timeout_ms,
                    logger=logger,
                )

            if isinstance(observation, RunCommandObservation) and logger:
                ok = observation.result.exit_code == 0 and not observation.result.timed_out
                logger("observed success" if ok else "observed failure", summarize_command(observation.result))

        if blocked_completion_feedback is not None:
            messages.append(ChatMessage(role="user", content=tool_results))
            messages.append(ChatMessage(role="user", content=blocked_completion_feedback))
            continue

        messages.append(ChatMessage(role="user", content=tool_results))

    # Return failure only after exhausting max iterations without an explicit finish action.
    return finish_agent_run(
        current_workspace,
        success=False,
        message=f"Reached iteration limit ({max_iterations}) before finish.",
        iterations=max_iterations,
        observations=observations,
        steps=steps,
        plan=plan,
        command_timeout_ms=command_timeout_ms,
        logger=logger,
    )


def completion_blocked_feedback_if_needed(
    workspace: RunWorkspace,
    success: bool,
    message: str,
    iteration: int,
    max_iterations: int,
    observations: list[Observation],
    plan: list[PlanItem],
    command_timeout_ms: int,
    logger: AgentLogger | None,
) -> str | None:
    if not success or iteration >= max_iterations:
        return None
    auto_run_final_review_if_needed(workspace, success, observations, iteration, command_timeout_ms, logger)
    blockers = build_completion_blockers(success, observations, plan)
    if not blockers:
        return None
    details = build_completion_blocker_details(success, observations)
    append_session_event(
        workspace.session_dir,
        "completion_blocked",
        {
            "iteration": iteration,
            "message": message,
            "blockers": blockers,
            "details": details,
        },
    )
    if logger:
        logger("completion blocked", summarize("; ".join(blockers), 500))
    return format_completion_blocked_feedback(blockers, details)


def build_completion_blocker_details(success: bool, observations: list[Observation]) -> dict[str, list[str]]:
    details: dict[str, list[str]] = {}
    failed_verification_checks = build_failed_verification_checks(success, observations)
    if failed_verification_checks:
        details["failedVerificationChecks"] = failed_verification_checks
    pending_verification_checks = build_pending_verification_checks(success, observations)
    if pending_verification_checks:
        details["pendingVerificationChecks"] = pending_verification_checks
    return details


def format_completion_blocked_feedback(blockers: list[str], details: dict[str, list[str]] | None = None) -> str:
    lines = [
        "Completion is not ready. Continue working before giving a final answer.",
        "Resolve these blockers first:",
    ]
    lines.extend(f"- {blocker}" for blocker in blockers)
    details = details or {}
    failed_verification_checks = details.get("failedVerificationChecks", [])
    if failed_verification_checks:
        lines.append("Failed verification checks:")
        lines.extend(f"- {check}" for check in failed_verification_checks)
    pending_verification_checks = details.get("pendingVerificationChecks", [])
    if pending_verification_checks:
        lines.append("Pending verification checks:")
        lines.extend(f"- {check}" for check in pending_verification_checks)
    lines.append("When the blockers are resolved, finish with a concise final answer.")
    return "\n".join(lines)


def finish_agent_run(
    workspace: RunWorkspace,
    success: bool,
    message: str,
    iterations: int,
    observations: list[Observation],
    steps: list[TaskStep],
    plan: list[PlanItem],
    command_timeout_ms: int,
    logger: AgentLogger | None,
) -> AgentResult:
    auto_run_final_review_if_needed(workspace, success, observations, iterations, command_timeout_ms, logger)
    completion_blockers = build_completion_blockers(success, observations, plan)
    completion_ready = success and not completion_blockers
    result_status = session_result_status(success, completion_ready)
    completion_warnings = build_completion_warnings(success, observations, plan)
    verification_checks = build_verification_checks(success, observations)
    pending_verification_checks = build_pending_verification_checks(success, observations)
    failed_verification_checks = build_failed_verification_checks(success, observations)
    append_session_event(
        workspace.session_dir,
        "result",
        {
            "success": success,
            "status": result_status,
            "message": message,
            "iterations": iterations,
            "observations": len(observations),
            "steps": len(steps),
            "plan": to_jsonable(plan),
            "completion_ready": completion_ready,
            "completion_blockers": completion_blockers,
            "completion_warnings": completion_warnings,
            "verification_checks": verification_checks,
            "pending_verification_checks": pending_verification_checks,
            "failed_verification_checks": failed_verification_checks,
        },
    )
    session_summary = summarize_session(workspace.root, workspace.run_id)
    return AgentResult(
        success=success,
        message=message,
        run_dir=workspace.root,
        run_id=workspace.run_id,
        iterations=iterations,
        observations=observations,
        steps=steps,
        plan=plan,
        status=result_status,
        completion_ready=completion_ready,
        completion_blockers=completion_blockers,
        completion_warnings=completion_warnings,
        verification_checks=verification_checks,
        pending_verification_checks=pending_verification_checks,
        failed_verification_checks=failed_verification_checks,
        completion_blocked_count=session_summary.completion_blocked_count,
        latest_completion_blockers=session_summary.latest_completion_blockers,
        latest_completion_pending_verification_checks=session_summary.latest_completion_pending_verification_checks,
        latest_completion_failed_verification_checks=session_summary.latest_completion_failed_verification_checks,
    )


def session_result_status(success: bool, completion_ready: bool) -> str:
    if not success:
        return "failed"
    if completion_ready:
        return "completed"
    return "blocked"


def complete_with_retries(
    client: ChatClient,
    messages: list[ChatMessage],
    *,
    tools: list[dict[str, Any]] | None,
    max_output_tokens: int,
    model_retries: int,
    model_retry_delay_ms: int,
    model_timeout_ms: int,
    iteration: int,
    session_dir: Path,
    logger: AgentLogger | None,
) -> tuple[Any | None, str | None]:
    attempts = max(0, model_retries) + 1
    last_message: str | None = None
    for attempt in range(1, attempts + 1):
        try:
            return client.complete(messages, tools=tools, max_tokens=max_output_tokens, timeout_ms=model_timeout_ms), None
        except Exception as error:
            will_retry = attempt < attempts
            last_message = f"Model request failed: {format_exception(error)}"
            append_session_event(
                session_dir,
                "model_error",
                {
                    "iteration": iteration,
                    "attempt": attempt,
                    "attempts": attempts,
                    "will_retry": will_retry,
                    "retry_delay_ms": model_retry_delay_ms if will_retry else 0,
                    "error_type": type(error).__name__,
                    "message": last_message,
                },
            )
            if logger:
                logger("model retry" if will_retry else "model error", last_message)
            if will_retry:
                if model_retry_delay_ms > 0:
                    time.sleep(model_retry_delay_ms / 1000)
                continue
            return None, last_message
    return None, last_message or "Model request failed."


def auto_run_final_review_if_needed(
    workspace: RunWorkspace,
    success: bool,
    observations: list[Observation],
    iteration: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
) -> None:
    reason = auto_final_review_reason(success, observations)
    if reason is None:
        return

    if logger:
        logger("auto final_review", f"{reason}; running read-only final review.")
    action = FinalReviewAction(type="final_review")
    observation = execute_action_safely(workspace, action, command_timeout_ms, "final_review")
    observations.append(observation)
    append_session_event(
        workspace.session_dir,
        "tool_result",
        {
            "iteration": iteration,
            "id": "auto-final-review",
            "name": "final_review",
            "auto": True,
            "result": to_jsonable(observation),
        },
    )
    if logger:
        logger("auto final_review result", observation_summary(observation))


def should_auto_run_final_review(success: bool, observations: list[Observation]) -> bool:
    return auto_final_review_reason(success, observations) is not None


def auto_final_review_reason(success: bool, observations: list[Observation]) -> str | None:
    if not success:
        return None
    final_review_index = latest_observation_index(observations, {"final_review"})
    project_change_index = latest_successful_project_change_index(observations)
    if project_change_index is not None:
        if final_review_index is None:
            return "Project changes completed without final_review"
        if project_change_index > final_review_index:
            return "Project changes completed after final_review"
    process_start_index = latest_successful_process_start_index(observations)
    if process_start_index is not None:
        if final_review_index is None:
            return "Background command started without final_review"
        if process_start_index > final_review_index:
            return "Background command started after final_review"
    return None


def latest_observation_index(observations: list[Observation], kinds: set[str]) -> int | None:
    for index in range(len(observations) - 1, -1, -1):
        if observations[index].kind in kinds:
            return index
    return None


def latest_successful_process_start_index(observations: list[Observation]) -> int | None:
    for index in range(len(observations) - 1, -1, -1):
        observation = observations[index]
        if observation.kind == "start_command" and bool(getattr(observation, "ok", False)):
            return index
    return None


def build_completion_warnings(
    success: bool,
    observations: list[Observation],
    plan: list[PlanItem] | None = None,
) -> list[str]:
    if not success:
        return []
    warnings: list[str] = []
    unfinished_plan_warning = build_unfinished_plan_warning(plan or [])
    if unfinished_plan_warning is not None:
        warnings.append(unfinished_plan_warning)
    missing_plan_warning = build_missing_plan_warning(success, observations, plan or [])
    if missing_plan_warning is not None:
        warnings.append(missing_plan_warning)
    reason = auto_final_review_reason(success, observations)
    if reason is not None:
        warnings.append(f"{reason} observation.")
    final_review = next((observation for observation in reversed(observations) if observation.kind == "final_review"), None)
    failed_verification_checks = build_failed_verification_checks(success, observations)
    pending_verification_checks = build_pending_verification_checks(success, observations)
    if final_review_has_active_completion_blocker(final_review, failed_verification_checks, pending_verification_checks):
        warnings.append("Final review did not report ready.")
    if any(observation.kind == "checkpoint_create" and observation_failed(observation) for observation in observations):
        warnings.append("Checkpoint creation failed; restore point may be unavailable.")
    running_process_count = final_review_running_process_count(final_review)
    if running_process_count:
        warnings.append(
            f"Final review reported {running_process_count} running background process(es). "
            "Stop them before finishing if they are no longer needed."
        )
    if failed_verification_checks:
        warnings.append("Suggested verification checks failed after the latest project change.")
    if pending_verification_checks:
        warnings.append("Suggested verification checks are still pending after the latest project change.")
    return warnings


def build_completion_blockers(success: bool, observations: list[Observation], plan: list[PlanItem]) -> list[str]:
    blockers: list[str] = []
    if not success:
        blockers.append("Run did not complete successfully.")
    unfinished_plan_warning = build_unfinished_plan_warning(plan)
    if unfinished_plan_warning is not None:
        blockers.append(unfinished_plan_warning)
    missing_plan_warning = build_missing_plan_warning(success, observations, plan)
    if missing_plan_warning is not None:
        blockers.append(missing_plan_warning)
    reason = auto_final_review_reason(success, observations)
    if reason is not None:
        blockers.append(f"{reason} observation.")
    final_review = next((observation for observation in reversed(observations) if observation.kind == "final_review"), None)
    failed_verification_checks = build_failed_verification_checks(success, observations)
    pending_verification_checks = build_pending_verification_checks(success, observations)
    if final_review_has_active_completion_blocker(final_review, failed_verification_checks, pending_verification_checks):
        blockers.append("Final review did not report ready.")
    denied_approvals = sum(1 for observation in observations if observation.kind == "approval_denied")
    if denied_approvals:
        blockers.append(f"{denied_approvals} approval request(s) were denied.")
    if any(observation.kind == "checkpoint_create" and observation_failed(observation) for observation in observations):
        blockers.append("Checkpoint creation failed; restore point may be unavailable.")
    running_process_count = final_review_running_process_count(final_review)
    if running_process_count:
        blockers.append(f"Final review reported {running_process_count} running background process(es).")
    if failed_verification_checks:
        blockers.append(f"{len(failed_verification_checks)} suggested verification check(s) failed after the latest project change.")
    if pending_verification_checks:
        blockers.append(f"{len(pending_verification_checks)} suggested verification check(s) are still pending after the latest project change.")
    return blockers


def final_review_has_active_completion_blocker(
    final_review: Observation | None,
    failed_verification_checks: list[str],
    pending_verification_checks: list[str],
) -> bool:
    if final_review is None or getattr(final_review, "ready", None) is not False:
        return False
    if failed_verification_checks or pending_verification_checks:
        return True
    blocking_issues = getattr(final_review, "blocking_issues", None)
    if not isinstance(blocking_issues, list) or not blocking_issues:
        return True
    return any(not final_review_issue_is_verification_only(str(issue)) for issue in blocking_issues)


def final_review_issue_is_verification_only(issue: str) -> bool:
    normalized = issue.casefold()
    return "suggested verification check" in normalized


def build_unfinished_plan_warning(plan: list[PlanItem]) -> str | None:
    unfinished = [item for item in plan if item.status != "completed"]
    if not unfinished:
        return None
    in_progress = [item for item in unfinished if item.status == "in_progress"]
    pending = [item for item in unfinished if item.status == "pending"]
    labels = [f"{item.status}: {summarize(item.step, 80)}" for item in unfinished[:3]]
    suffix = f"; {'; '.join(labels)}" if labels else ""
    status_parts: list[str] = []
    if in_progress:
        status_parts.append(f"{len(in_progress)} in_progress")
    if pending:
        status_parts.append(f"{len(pending)} pending")
    status_text = ", ".join(status_parts) if status_parts else f"{len(unfinished)} unfinished"
    return f"Task plan still has unfinished item(s): {status_text}{suffix}."


def build_missing_plan_warning(success: bool, observations: list[Observation], plan: list[PlanItem]) -> str | None:
    if not success or plan:
        return None
    if not observations_show_multistep_coding_work(observations):
        return None
    return "Task plan is missing for multi-step coding work; call update_plan with a short checklist before finishing."


def observations_show_multistep_coding_work(observations: list[Observation]) -> bool:
    successful_project_changes = [
        observation
        for observation in observations
        if observation.kind in PROJECT_CHANGE_OBSERVATION_KINDS and not observation_failed(observation)
    ]
    if not successful_project_changes:
        return False
    if len(successful_project_changes) >= 2:
        return True
    first_change_index = next(
        index
        for index, observation in enumerate(observations)
        if observation.kind in PROJECT_CHANGE_OBSERVATION_KINDS and not observation_failed(observation)
    )
    return any(observation.kind in MULTISTEP_CODING_FOLLOWUP_KINDS for observation in observations[first_change_index + 1 :])


def final_review_running_process_count(final_review: Observation | None) -> int:
    if final_review is None:
        return 0
    running_processes = getattr(final_review, "running_processes", [])
    return sum(1 for process in running_processes if getattr(process, "running", False))


def build_verification_checks(success: bool, observations: list[Observation]) -> list[str]:
    if not success:
        return []
    final_review = next((observation for observation in reversed(observations) if observation.kind == "final_review"), None)
    if final_review is None:
        return []
    suggested_commands = final_review_suggested_commands(final_review)
    if not suggested_commands:
        return []
    last_change_index = latest_successful_project_change_index(observations)
    if last_change_index is None:
        return []

    checks: list[str] = []
    seen: set[str] = set()
    for observation in observations[last_change_index + 1 :]:
        for label in successful_suggested_check_labels(observation, suggested_commands):
            if label not in seen:
                checks.append(label)
                seen.add(label)
    return checks


def build_pending_verification_checks(success: bool, observations: list[Observation]) -> list[str]:
    suggested_commands, statuses = suggested_check_statuses_after_latest_change(success, observations)
    if not suggested_commands:
        return []
    completed_commands = set(statuses)
    return [suggested_check_label(command, cwd) for command, cwd in sorted(suggested_commands - completed_commands)]


def build_failed_verification_checks(success: bool, observations: list[Observation]) -> list[str]:
    _, statuses = suggested_check_statuses_after_latest_change(success, observations)
    return [label for _, (passed, label) in sorted(statuses.items()) if not passed]


def suggested_check_statuses_after_latest_change(
    success: bool,
    observations: list[Observation],
) -> tuple[set[tuple[str, str]], dict[tuple[str, str], tuple[bool, str]]]:
    if not success:
        return set(), {}
    final_review = next((observation for observation in reversed(observations) if observation.kind == "final_review"), None)
    if final_review is None:
        return set(), {}
    suggested_commands = final_review_suggested_commands(final_review)
    if not suggested_commands:
        return set(), {}
    last_change_index = latest_successful_project_change_index(observations)
    if last_change_index is None:
        return suggested_commands, {}

    statuses: dict[tuple[str, str], tuple[bool, str]] = {}
    for observation in observations[last_change_index + 1 :]:
        for command, cwd in successful_suggested_check_commands(observation, suggested_commands):
            statuses[(command, cwd)] = (True, suggested_check_label(command, cwd))
        for command, cwd, label in failed_suggested_check_results(observation, suggested_commands):
            statuses[(command, cwd)] = (False, label)
    return suggested_commands, statuses


def final_review_suggested_commands(final_review: Observation) -> set[tuple[str, str]]:
    return {
        (str(getattr(check, "command", "")), str(getattr(check, "cwd", ".") or "."))
        for check in getattr(final_review, "suggested_checks", [])
        if getattr(check, "command", None)
    }


def latest_successful_project_change_index(observations: list[Observation]) -> int | None:
    for index in range(len(observations) - 1, -1, -1):
        observation = observations[index]
        if observation.kind in PROJECT_CHANGE_OBSERVATION_KINDS and not observation_failed(observation):
            return index
    return None


def observation_runs_suggested_check_successfully(
    observation: Observation,
    suggested_commands: set[tuple[str, str]],
) -> bool:
    return bool(successful_suggested_check_commands(observation, suggested_commands))


def successful_suggested_check_commands(
    observation: Observation,
    suggested_commands: set[tuple[str, str]],
) -> set[tuple[str, str]]:
    if observation.kind == "run_command":
        return command_result_suggested_check_commands(observation.result, suggested_commands)
    if observation.kind in {"run_commands", "run_suggested_checks", "run_focused_test_commands"}:
        commands: set[tuple[str, str]] = set()
        for result in observation.results:
            commands.update(command_result_suggested_check_commands(result, suggested_commands))
        return commands
    return set()


def successful_suggested_check_labels(
    observation: Observation,
    suggested_commands: set[tuple[str, str]],
) -> list[str]:
    return [suggested_check_label(command, cwd) for command, cwd in successful_suggested_check_commands(observation, suggested_commands)]


def failed_suggested_check_labels(
    observation: Observation,
    suggested_commands: set[tuple[str, str]],
) -> list[str]:
    return [label for _, _, label in failed_suggested_check_results(observation, suggested_commands)]


def failed_suggested_check_results(
    observation: Observation,
    suggested_commands: set[tuple[str, str]],
) -> list[tuple[str, str, str]]:
    if observation.kind == "run_command":
        result = command_result_failed_suggested_check_result(observation.result, suggested_commands)
        return [result] if result is not None else []
    if observation.kind in {"run_commands", "run_suggested_checks", "run_focused_test_commands"}:
        failures: list[tuple[str, str, str]] = []
        for result in observation.results:
            failure = command_result_failed_suggested_check_result(result, suggested_commands)
            if failure is not None:
                failures.append(failure)
        return failures
    return []


def command_result_suggested_check_commands(
    result: object,
    suggested_commands: set[tuple[str, str]],
) -> set[tuple[str, str]]:
    if not command_result_matches_successful_suggested_check(result, suggested_commands):
        return set()
    command = str(getattr(result, "command", ""))
    cwd = str(getattr(result, "cwd", ".") or ".")
    return {(command, cwd)}


def command_result_failed_suggested_check_labels(
    result: object,
    suggested_commands: set[tuple[str, str]],
) -> list[str]:
    failure = command_result_failed_suggested_check_result(result, suggested_commands)
    return [failure[2]] if failure is not None else []


def command_result_failed_suggested_check_result(
    result: object,
    suggested_commands: set[tuple[str, str]],
) -> tuple[str, str, str] | None:
    command = str(getattr(result, "command", ""))
    cwd = str(getattr(result, "cwd", ".") or ".")
    if (command, cwd) not in suggested_commands:
        return None
    if getattr(result, "exit_code", None) == 0 and not getattr(result, "timed_out", False):
        return None
    if getattr(result, "timed_out", False):
        reason = "timed out"
    else:
        exit_code = getattr(result, "exit_code", None)
        reason = f"exit={exit_code}" if exit_code is not None else "no exit code"
    return command, cwd, f"{suggested_check_label(command, cwd)} ({reason})"


def suggested_check_label(command: str, cwd: str) -> str:
    if cwd == ".":
        return command
    return f"{command} (cwd: {cwd})"


def command_result_matches_successful_suggested_check(
    result: object,
    suggested_commands: set[tuple[str, str]],
) -> bool:
    if getattr(result, "exit_code", None) != 0 or getattr(result, "timed_out", False):
        return False
    command = str(getattr(result, "command", ""))
    cwd = str(getattr(result, "cwd", ".") or ".")
    return (command, cwd) in suggested_commands


def execute_parallel_tool_call_batch(
    workspace: RunWorkspace,
    tool_calls: list[ContentBlock],
    observations: list[Observation],
    steps: list[TaskStep],
    iteration: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
) -> list[ContentBlock] | None:
    if len(tool_calls) < 2:
        return None

    parsed: list[tuple[str, str, object, object]] = []
    for block in tool_calls:
        tool_id = str(block.get("id") or "")
        tool_name = str(block.get("name") or "")
        tool_input = block.get("input") or {}
        try:
            action = parse_tool_action(tool_name, tool_input)
        except ActionParseError:
            return None
        if not is_parallel_safe_action(action):
            return None
        parsed.append((tool_id, tool_name, tool_input, action))

    prepared: list[PreparedParallelToolCall] = []
    for tool_id, tool_name, tool_input, action in parsed:
        append_session_event(
            workspace.session_dir,
            "tool_call",
            {"iteration": iteration, "id": tool_id, "name": tool_name, "input": tool_input},
        )
        step = start_task_step(workspace, steps, iteration, action, logger)
        log_action(logger, action)
        prepared.append(
            PreparedParallelToolCall(
                tool_id=tool_id,
                tool_name=tool_name,
                action=action,
                step=step,
                repeated_observation=find_repeated_list_observation(action, observations),
            )
        )

    batch_observations: list[Observation | None] = [None] * len(prepared)
    with ThreadPoolExecutor(max_workers=min(len(prepared), 8)) as executor:
        futures = {}
        for index, item in enumerate(prepared):
            if item.repeated_observation is not None:
                repeated = item.repeated_observation
                batch_observations[index] = ListFilesObservation(
                    kind="list_files",
                    path=repeated.path,
                    files=repeated.files,
                    total=repeated.total,
                    truncated=repeated.truncated,
                    message=(
                        f"Already listed {repeated.path}: {repeated.message} "
                        "Do not call list_files for this path again. Choose a useful tool call or answer directly."
                    ),
                )
                continue
            futures[executor.submit(execute_action, workspace, item.action, command_timeout_ms)] = index

        for future in as_completed(futures):
            index = futures[future]
            item = prepared[index]
            try:
                batch_observations[index] = future.result()
            except Exception as error:  # pragma: no cover - defensive guard for unexpected tool bugs.
                batch_observations[index] = ToolErrorObservation(
                    kind="tool_error",
                    tool=item.tool_name or "unknown",
                    message=f"Tool execution failed: {error}",
                )

    tool_results: list[ContentBlock] = []
    for item, observation in zip(prepared, batch_observations):
        if observation is None:
            observation = ToolErrorObservation(kind="tool_error", tool=item.tool_name or "unknown", message="Tool execution failed.")
        complete_task_step(workspace, item.step, observation, iteration, logger)
        observations.append(observation)
        result_payload = to_jsonable(observation)
        append_session_event(
            workspace.session_dir,
            "tool_result",
            {"iteration": iteration, "id": item.tool_id, "name": item.tool_name, "result": result_payload},
        )
        tool_results.append(
            {
                "type": "tool_result",
                "tool_call_id": item.tool_id,
                "content": json.dumps(result_payload, ensure_ascii=False),
            }
        )
    return tool_results


def is_parallel_safe_action(action: object) -> bool:
    action_type = str(getattr(action, "type", ""))
    return action_type in PARALLEL_SAFE_TOOL_NAMES and build_approval_request(action) is None


def execute_action_safely(
    workspace: RunWorkspace,
    action: object,
    command_timeout_ms: int,
    tool_name: str,
) -> Observation:
    try:
        return execute_action(workspace, action, command_timeout_ms)
    except Exception as error:
        return ToolErrorObservation(
            kind="tool_error",
            tool=tool_name or str(getattr(action, "type", "unknown")) or "unknown",
            message=f"Tool execution failed: {error}",
        )


def should_auto_checkpoint_before_action(workspace: RunWorkspace, action: object) -> bool:
    action_type = str(getattr(action, "type", ""))
    if action_type not in PROJECT_CHANGE_OBSERVATION_KINDS:
        return False
    return bool(read_checkpoint_git_head(workspace.root))


def create_auto_checkpoint_before_action(
    workspace: RunWorkspace,
    action: object,
    steps: list[TaskStep],
    iteration: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
) -> Observation | None:
    action_type = str(getattr(action, "type", "project change"))
    checkpoint_action = CheckpointCreateAction(type="checkpoint_create", label=f"auto before {action_type}")
    if logger:
        logger("auto checkpoint", f"Creating checkpoint before {action_type}.")
    step = start_task_step(workspace, steps, iteration, checkpoint_action, logger)
    observation = execute_action_safely(workspace, checkpoint_action, command_timeout_ms, "checkpoint_create")
    complete_task_step(workspace, step, observation, iteration, logger)
    result_payload = to_jsonable(observation)
    append_session_event(
        workspace.session_dir,
        "tool_result",
        {
            "iteration": iteration,
            "id": "auto-checkpoint",
            "name": "checkpoint_create",
            "auto": True,
            "before_action_type": action_type,
            "result": result_payload,
        },
    )
    if observation_failed(observation):
        if logger:
            logger("auto checkpoint skipped", observation_summary(observation))
    return observation


def summarize(value: str, max_length: int = 500) -> str:
    compact = " ".join(value.split())
    if len(compact) <= max_length:
        return compact
    return f"{compact[:max_length]}..."


def format_exception(error: Exception) -> str:
    text = str(error).strip()
    if not text:
        return type(error).__name__
    return f"{type(error).__name__}: {summarize(text, 1000)}"


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
    if isinstance(action, ReadFileContextAction):
        return f"Read {action.path}:{action.line}"
    if isinstance(action, ReadFileContextsAction):
        return f"Read {len(action.contexts)} file contexts"
    if isinstance(action, OutputContextsAction):
        return f"Read output contexts from {action.max_contexts} reference(s)"
    if isinstance(action, SessionOutputContextsAction):
        return f"Read session output contexts for {action.run_id or 'current session'}"
    if isinstance(action, SessionOutputDiagnosticsAction):
        return f"Read session output diagnostics for {action.run_id or 'current session'}"
    if isinstance(action, TailFileAction):
        return f"Tail {action.path}"
    if isinstance(action, ReadFilesAction):
        return f"Read {len(action.paths)} files"
    if isinstance(action, ReadFileRangesAction):
        return f"Read {len(action.ranges)} file ranges"
    if isinstance(action, FileInfoAction):
        return f"Inspect {len(action.paths)} paths"
    if isinstance(action, ImageInfoAction):
        return f"Inspect {len(action.paths)} images"
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
    if isinstance(action, CodeDependenciesAction):
        return f"Read code dependencies {action.path or '.'}"
    if isinstance(action, CodeReferencesAction):
        return f"Find code references {action.symbol}"
    if isinstance(action, CodeReferenceContextsAction):
        return f"Read code reference contexts {action.symbol}"
    if isinstance(action, CodeDefinitionsAction):
        return f"Find code definitions {action.symbol}"
    if isinstance(action, CodeRenamePreviewAction):
        return f"Preview code rename {action.symbol} to {action.new_name}"
    if isinstance(action, CodeRenameAction):
        return f"Rename code symbol {action.symbol} to {action.new_name}"
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
    if isinstance(action, PythonReferenceContextsAction):
        return f"Read Python reference contexts {action.symbol}"
    if isinstance(action, PythonRenamePreviewAction):
        return f"Preview Python rename {action.symbol} to {action.new_name}"
    if isinstance(action, PythonRenameAction):
        return f"Rename Python symbol {action.symbol} to {action.new_name}"
    if isinstance(action, SearchAction):
        return f"Search {summarize(action.query, 80)}"
    if isinstance(action, SearchContextsAction):
        return f"Search contexts {summarize(action.query, 80)} in {action.path or '.'}"
    if isinstance(action, GlobAction):
        return f"Find files {summarize(action.pattern, 80)}"
    if isinstance(action, ListTreeAction):
        return f"List tree {action.path or '.'}"
    if isinstance(action, GitStatusAction):
        return "Read git status"
    if isinstance(action, GitConflictsAction):
        return f"Scan git conflicts {action.path or '.'}"
    if isinstance(action, GitDiffContextsAction):
        return f"Read git diff contexts {action.path or '.'}"
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
    if isinstance(action, HttpFetchAction):
        return f"Fetch HTTP {summarize(action.url, 80)}"
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
    if isinstance(action, SessionPlanAction):
        return f"Read session plan {action.run_id or 'current'}"
    if isinstance(action, SessionTranscriptAction):
        return f"Read session transcript {action.run_id or 'current'}"
    if isinstance(action, SessionSearchAction):
        return f"Search session {action.run_id or 'current'}"
    if isinstance(action, SessionCommandsAction):
        return f"Read session commands {action.run_id or 'current'}"
    if isinstance(action, SessionFilesAction):
        return f"Read session files {action.run_id or 'current'}"
    if isinstance(action, SessionFailuresAction):
        return f"Read session failures {action.run_id or 'current'}"
    if isinstance(action, SessionVerificationAction):
        return f"Read session verification {action.run_id or 'current'}"
    if isinstance(action, SessionAuditAction):
        return f"Read session audit {action.run_id or 'current'}"
    if isinstance(action, SessionHandoffAction):
        return f"Read session handoff {action.run_id or 'current'}"
    if isinstance(action, CheckpointCreateAction):
        return f"Create checkpoint {action.label or ''}".strip()
    if isinstance(action, CheckpointListAction):
        return "List checkpoints"
    if isinstance(action, CheckpointShowAction):
        return f"Show checkpoint {action.checkpoint_id}"
    if isinstance(action, CheckpointDiffAction):
        return f"Read checkpoint diff {action.checkpoint_id}"
    if isinstance(action, CheckpointStatusAction):
        return f"Check checkpoint status {action.checkpoint_id}"
    if isinstance(action, CheckCheckpointRestoreAction):
        return f"Check checkpoint restore {action.checkpoint_id}"
    if isinstance(action, CheckpointRestoreAction):
        return f"Restore checkpoint {action.checkpoint_id}"
    if isinstance(action, CheckpointDeleteAction):
        return f"Delete checkpoint {action.checkpoint_id}"
    if isinstance(action, CheckCheckpointPruneAction):
        return f"Check checkpoint prune keep {action.keep_last}"
    if isinstance(action, CheckpointPruneAction):
        return f"Prune checkpoints keep {action.keep_last}"
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
    if isinstance(action, ImageInfoAction):
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
    if isinstance(action, PythonReferenceContextsAction):
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
    if isinstance(action, SearchContextsAction):
        return f"{action.query} in {action.path or '.'}"
    if isinstance(action, GlobAction):
        return action.pattern
    if isinstance(action, ListTreeAction):
        return action.path or "."
    if isinstance(action, GitStatusAction):
        return "git status"
    if isinstance(action, GitConflictsAction):
        return action.path or "."
    if isinstance(action, GitDiffContextsAction):
        return action.path or "."
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
    if isinstance(action, RelatedTestsAction):
        return "related tests"
    if isinstance(action, FocusedTestCommandsAction):
        return "focused test commands"
    if isinstance(action, (CheckFocusedTestCommandsAction, RunFocusedTestCommandsAction)):
        return f"up to {action.max_commands} focused test command(s)"
    if isinstance(action, ProjectManifestsAction):
        return "project manifests"
    if isinstance(action, ProjectInstructionsAction):
        return "project instructions"
    if isinstance(action, ProjectOverviewAction):
        return "project overview"
    if isinstance(action, CodeDependenciesAction):
        return action.path or "."
    if isinstance(action, CodeReferencesAction):
        return f"{action.symbol} in {action.path or '.'}"
    if isinstance(action, CodeReferenceContextsAction):
        return f"{action.symbol} in {action.path or '.'}"
    if isinstance(action, CodeDefinitionsAction):
        return f"{action.symbol} in {action.path or '.'}"
    if isinstance(action, CodeRenamePreviewAction):
        return f"{action.symbol} -> {action.new_name} in {action.path or '.'}"
    if isinstance(action, CodeRenameAction):
        return f"{action.symbol} -> {action.new_name} in {action.path or '.'}"
    if isinstance(action, CommandCheckAction):
        return f"{action.command} (cwd: {action.cwd or '.'})"
    if isinstance(action, PortCheckAction):
        return f"{action.host}:{action.port}"
    if isinstance(action, HttpCheckAction):
        return action.url
    if isinstance(action, HttpFetchAction):
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
    if isinstance(action, (CheckSuggestedChecksAction, RunSuggestedChecksAction)):
        return f"up to {action.max_commands} suggested checks"
    if isinstance(action, (WaitProcessAction, CheckStopProcessAction)):
        return action.process_id
    if isinstance(action, (CheckWriteProcessAction, WriteProcessAction)):
        return f"{action.process_id} ({len(action.content)} chars)"
    if isinstance(action, SessionSummaryAction):
        return action.run_id or "current session"
    if isinstance(action, SessionPlanAction):
        return action.run_id or "current session"
    if isinstance(action, SessionTranscriptAction):
        return action.run_id or "current session"
    if isinstance(action, (SessionVerificationAction, SessionAuditAction, SessionHandoffAction)):
        return action.run_id or "current session"
    if isinstance(action, CheckpointCreateAction):
        return action.label or "checkpoint"
    if isinstance(action, CheckpointListAction):
        return "checkpoints"
    if isinstance(action, (CheckCheckpointPruneAction, CheckpointPruneAction)):
        return f"keep_last={action.keep_last}"
    if isinstance(action, (CheckpointShowAction, CheckpointDiffAction, CheckpointStatusAction, CheckCheckpointRestoreAction, CheckpointRestoreAction, CheckCheckpointDeleteAction, CheckpointDeleteAction)):
        return action.checkpoint_id
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
    if isinstance(action, CodeRenameAction):
        return ApprovalRequest(
            action_type="code_rename",
            target=f"{action.symbol} -> {action.new_name} in {action.path or '.'}",
            risk="This will rename non-Python source symbols or literals across matching project files.",
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
    if isinstance(action, CheckpointRestoreAction):
        return ApprovalRequest(
            action_type="checkpoint_restore",
            target=action.checkpoint_id,
            risk="This will discard current tracked staged and unstaged changes, then restore tracked changes and saved untracked file contents from a checkpoint.",
        )
    if isinstance(action, CheckpointDeleteAction):
        return ApprovalRequest(
            action_type="checkpoint_delete",
            target=action.checkpoint_id,
            risk="This will permanently delete one saved checkpoint snapshot from the local runtime directory.",
        )
    if isinstance(action, CheckpointPruneAction):
        return ApprovalRequest(
            action_type="checkpoint_prune",
            target=f"keep_last={action.keep_last}",
            risk="This will permanently delete older saved checkpoint snapshots from the local runtime directory.",
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
    if isinstance(action, RunSuggestedChecksAction):
        return ApprovalRequest(
            action_type="run_suggested_checks",
            target=f"up to {action.max_commands} suggested check command(s)",
            risk="This will discover and run project test/build/lint check commands from the active project directory.",
        )
    if isinstance(action, RunFocusedTestCommandsAction):
        return ApprovalRequest(
            action_type="run_focused_test_commands",
            target=f"up to {action.max_commands} focused test command(s)",
            risk="This will discover and run focused project test commands from the active project directory.",
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


PREVIEW_KIND_BY_ACTION_TYPE = {
    "write_file": "check_write_file",
    "write_files": "check_write_files",
    "edit_file": "check_edit_file",
    "multi_edit_file": "check_multi_edit_file",
    "replace_python_definition": "check_replace_python_definition",
    "code_rename": "code_rename_preview",
    "python_rename": "python_rename_preview",
    "replace_lines": "check_replace_lines",
    "insert_lines": "check_insert_lines",
    "append_file": "check_append_file",
    "regex_replace": "check_regex_replace",
    "json_set": "check_json_set",
    "json_remove": "check_json_remove",
    "json_patch": "check_json_patch",
    "patch_file": "check_patch",
    "patch_files": "check_patches",
    "delete_file": "check_delete_file",
    "delete_files": "check_delete_files",
    "move_file": "check_move_file",
    "move_files": "check_move_files",
    "copy_file": "check_copy_file",
    "copy_files": "check_copy_files",
    "move_dir": "check_move_dir",
    "move_dirs": "check_move_dirs",
    "copy_dir": "check_copy_dir",
    "copy_dirs": "check_copy_dirs",
    "create_dir": "check_create_dir",
    "create_dirs": "check_create_dirs",
    "delete_empty_dir": "check_delete_empty_dir",
    "delete_empty_dirs": "check_delete_empty_dirs",
    "set_executable": "check_set_executable",
    "git_stage": "check_git_stage",
    "git_unstage": "check_git_unstage",
    "git_commit": "check_git_commit",
    "git_fetch": "check_git_fetch",
    "git_pull": "check_git_pull",
    "git_push": "check_git_push",
    "git_restore": "check_git_restore",
    "git_switch": "check_git_switch",
    "git_stash": "check_git_stash",
    "git_stash_apply": "check_git_stash_apply",
    "git_stash_drop": "check_git_stash_drop",
    "checkpoint_restore": "check_checkpoint_restore",
    "checkpoint_delete": "check_checkpoint_delete",
    "checkpoint_prune": "check_checkpoint_prune",
    "run_command": "command_check",
    "run_commands": "check_run_commands",
    "run_suggested_checks": "check_suggested_checks",
    "run_focused_test_commands": "check_focused_test_commands",
    "start_command": "check_start_command",
    "write_process": "check_write_process",
    "stop_process": "check_stop_process",
    "stop_all_processes": "check_stop_all_processes",
}


def attach_approval_preview(
    request: ApprovalRequest,
    action: object,
    observations: list[Observation],
) -> ApprovalRequest:
    preview = approval_preview_summary(action, observations)
    if not preview:
        return request
    return replace(request, preview=preview)


def approval_preview_summary(action: object, observations: list[Observation]) -> str | None:
    expected_kind = PREVIEW_KIND_BY_ACTION_TYPE.get(str(getattr(action, "type", "")))
    if not expected_kind:
        return None
    expected_key = approval_preview_key(action)
    for observation in reversed(observations):
        if getattr(observation, "kind", None) != expected_kind:
            continue
        if getattr(observation, "ok", True) is not True:
            continue
        if approval_preview_key(observation) != expected_key:
            continue
        return summarize_preview_observation(observation)
    return None


def summarize_preview_observation(observation: object) -> str:
    message = getattr(observation, "message", "")
    parts = [summarize(message, 160) if isinstance(message, str) and message.strip() else "Matching preview completed."]
    diff = getattr(observation, "diff", None)
    if isinstance(diff, str) and diff:
        parts.append(f"diffChars={len(diff)}")
    checks = getattr(observation, "checks", None)
    if isinstance(checks, list):
        parts.append(f"commands={len(checks)}")
    return "; ".join(parts)


def approval_preview_key(value: object) -> tuple[Any, ...]:
    kind = str(getattr(value, "kind", getattr(value, "type", "")))
    if kind in {"write_file", "check_write_file", "edit_file", "check_edit_file", "multi_edit_file", "check_multi_edit_file", "append_file", "check_append_file", "regex_replace", "check_regex_replace", "patch_file", "check_patch", "delete_file", "check_delete_file", "create_dir", "check_create_dir", "delete_empty_dir", "check_delete_empty_dir", "set_executable", "check_set_executable"}:
        return (kind.replace("check_", ""), getattr(value, "path", ""), getattr(value, "executable", None))
    if kind in {"json_set", "check_json_set", "json_remove", "check_json_remove"}:
        return (kind.replace("check_", ""), getattr(value, "path", ""), getattr(value, "pointer", ""))
    if kind in {"json_patch", "check_json_patch"}:
        return ("json_patch", getattr(value, "path", ""), getattr(value, "operation_count", len(getattr(value, "operations", []))))
    if kind in {"replace_lines", "check_replace_lines"}:
        return ("replace_lines", getattr(value, "path", ""), getattr(value, "start_line", None), getattr(value, "end_line", None))
    if kind in {"insert_lines", "check_insert_lines"}:
        return ("insert_lines", getattr(value, "path", ""), getattr(value, "line", None))
    if kind in {"replace_python_definition", "check_replace_python_definition"}:
        return ("replace_python_definition", getattr(value, "symbol", ""), getattr(value, "path", None))
    if kind in {"python_rename", "python_rename_preview"}:
        return ("python_rename", getattr(value, "symbol", ""), getattr(value, "new_name", ""), getattr(value, "path", None))
    if kind in {"code_rename", "code_rename_preview"}:
        return ("code_rename", getattr(value, "symbol", ""), getattr(value, "new_name", ""), getattr(value, "path", None))
    if kind in {"write_files", "check_write_files"}:
        return ("write_files", tuple(getattr(item, "path", "") for item in getattr(value, "files", [])))
    if kind in {"delete_files", "check_delete_files", "create_dirs", "check_create_dirs", "delete_empty_dirs", "check_delete_empty_dirs", "git_stage", "check_git_stage", "git_unstage", "check_git_unstage", "git_restore", "check_git_restore"}:
        return (kind.replace("check_", ""), tuple(getattr(value, "paths", [])))
    if kind in {"move_file", "check_move_file", "copy_file", "check_copy_file", "move_dir", "check_move_dir", "copy_dir", "check_copy_dir"}:
        return (kind.replace("check_", ""), getattr(value, "source", ""), getattr(value, "destination", ""))
    if kind in {"move_files", "check_move_files", "copy_files", "check_copy_files", "move_dirs", "check_move_dirs", "copy_dirs", "check_copy_dirs"}:
        return (
            kind.replace("check_", ""),
            tuple((getattr(item, "source", ""), getattr(item, "destination", "")) for item in getattr(value, "transfers", [])),
        )
    if kind in {"patch_files", "check_patches"}:
        return ("patch_files",)
    if kind in {"git_fetch", "check_git_fetch"}:
        return ("git_fetch", getattr(value, "remote", None) or "default remote")
    if kind in {"git_pull", "check_git_pull", "git_push", "check_git_push"}:
        return (kind.replace("check_", ""),)
    if kind in {"git_commit", "check_git_commit"}:
        return ("git_commit",)
    if kind in {"git_switch", "check_git_switch"}:
        return ("git_switch", getattr(value, "branch", ""), getattr(value, "create", False))
    if kind in {"git_stash", "check_git_stash"}:
        return ("git_stash", getattr(value, "message_text", getattr(value, "message", None)), getattr(value, "include_untracked", False))
    if kind in {"git_stash_apply", "check_git_stash_apply", "git_stash_drop", "check_git_stash_drop"}:
        return (kind.replace("check_", ""), getattr(value, "stash_ref", ""))
    if kind in {"checkpoint_restore", "check_checkpoint_restore", "checkpoint_delete", "check_checkpoint_delete"}:
        return (kind.replace("check_", ""), getattr(value, "checkpoint_id", ""))
    if kind in {"checkpoint_prune", "check_checkpoint_prune"}:
        return ("checkpoint_prune", getattr(value, "keep_last", None))
    if kind in {"run_command", "command_check", "start_command", "check_start_command"}:
        normalized = "run_command" if kind == "command_check" else kind.replace("check_", "")
        return (normalized, getattr(value, "command", ""), getattr(value, "cwd", None) or ".")
    if kind in {"run_commands", "check_run_commands"}:
        commands = getattr(value, "commands", None)
        if commands is None:
            commands = getattr(value, "checks", [])
        return ("run_commands", tuple((getattr(item, "command", ""), getattr(item, "cwd", None) or ".") for item in commands))
    if kind in {"run_suggested_checks", "check_suggested_checks"}:
        return ("run_suggested_checks", getattr(value, "max_commands", None))
    if kind in {"run_focused_test_commands", "check_focused_test_commands"}:
        paths = tuple(getattr(value, "paths", None) or ())
        return ("run_focused_test_commands", paths, getattr(value, "max_commands", None))
    if kind in {"write_process", "check_write_process"}:
        return ("write_process", getattr(value, "process_id", ""), getattr(value, "content_chars", len(getattr(value, "content", ""))))
    if kind in {"stop_process", "check_stop_process"}:
        return ("stop_process", getattr(value, "process_id", ""))
    if kind in {"stop_all_processes", "check_stop_all_processes"}:
        return ("stop_all_processes",)
    return (kind,)


def request_approval(handler: ApprovalHandler | None, request: ApprovalRequest) -> ApprovalDecision:
    if handler is None:
        return ApprovalDecision(approved=False, message="No approval handler configured.")
    return handler(request)


def summarize_approval_request(request: ApprovalRequest) -> str:
    suffix = " (previewed)" if request.preview else ""
    return f"{request.action_type} {summarize(request.target, 120)}{suffix}"


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
    if observation.kind == "checkpoint_create":
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
    if observation.kind == "run_focused_test_commands":
        return not observation.ok
    if observation.kind == "port_check":
        return not observation.ok
    if observation.kind == "http_check":
        return not observation.ok
    if observation.kind == "http_fetch":
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
    if observation.kind == "read_file_context":
        return not observation.ok
    if observation.kind == "read_file_contexts":
        return any(not item.ok for item in observation.contexts)
    if observation.kind == "output_contexts":
        return any(not item.ok for item in observation.contexts)
    if observation.kind == "output_diagnostics":
        return any(not item.ok for item in observation.contexts)
    if observation.kind == "tail_file":
        return not observation.ok
    if observation.kind == "read_files":
        return any(not item.ok for item in observation.files)
    if observation.kind == "read_file_ranges":
        return any(not item.ok for item in observation.ranges)
    if observation.kind == "file_info":
        return any(not item.ok for item in observation.files)
    if observation.kind == "image_info":
        return any(not item.ok for item in observation.images)
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
    if observation.kind == "code_reference_contexts":
        return not observation.ok
    if observation.kind == "code_definitions":
        return not observation.ok
    if observation.kind == "code_rename_preview":
        return not observation.ok
    if observation.kind == "code_rename":
        return not observation.ok
    if observation.kind == "python_definitions":
        return not observation.ok
    if observation.kind == "python_calls":
        return not observation.ok
    if observation.kind == "python_call_graph":
        return not observation.ok
    if observation.kind == "python_references":
        return not observation.ok
    if observation.kind == "python_reference_contexts":
        return not observation.ok
    if observation.kind == "python_rename_preview":
        return not observation.ok
    if observation.kind == "python_rename":
        return not observation.ok
    if observation.kind == "search":
        return not observation.ok
    if observation.kind == "search_contexts":
        return not observation.ok
    if observation.kind == "glob":
        return not observation.ok
    if observation.kind == "list_tree":
        return not observation.ok
    if observation.kind == "list_files":
        return not observation.message.startswith(("Found ", "Already listed "))
    if observation.kind == "git_status":
        return not observation.ok
    if observation.kind == "git_conflicts":
        return not observation.ok
    if observation.kind == "git_diff_contexts":
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
    if observation.kind == "check_suggested_checks":
        return not observation.ok
    if observation.kind == "run_suggested_checks":
        return not observation.ok
    if observation.kind == "project_commands":
        return not observation.ok
    if observation.kind == "related_tests":
        return not observation.ok
    if observation.kind == "focused_test_commands":
        return not observation.ok
    if observation.kind == "check_focused_test_commands":
        return not observation.ok
    if observation.kind == "run_focused_test_commands":
        return not observation.ok
    if observation.kind == "project_manifests":
        return not observation.ok
    if observation.kind == "project_instructions":
        return not observation.ok
    if observation.kind == "project_todos":
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
    if observation.kind == "session_plan":
        return not observation.ok
    if observation.kind == "session_transcript":
        return not observation.ok
    if observation.kind == "session_search":
        return not observation.ok
    if observation.kind == "session_commands":
        return not observation.ok
    if observation.kind == "session_output_contexts":
        return not observation.ok
    if observation.kind == "session_output_diagnostics":
        return not observation.ok
    if observation.kind == "process_output_contexts":
        return not observation.ok
    if observation.kind == "process_output_diagnostics":
        return not observation.ok
    if observation.kind == "session_files":
        return not observation.ok
    if observation.kind == "session_failures":
        return not observation.ok
    if observation.kind == "session_verification":
        return not observation.ok
    if observation.kind == "session_audit":
        return not observation.ok
    if observation.kind == "session_handoff":
        return not observation.ok
    if observation.kind in {
        "checkpoint_create",
        "checkpoint_list",
        "checkpoint_show",
        "checkpoint_diff",
        "checkpoint_status",
        "check_checkpoint_restore",
        "checkpoint_restore",
        "check_checkpoint_delete",
        "checkpoint_delete",
        "check_checkpoint_prune",
        "checkpoint_prune",
    }:
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
    elif action_type == "read_file_context":
        logger("reading file context", build_action_target(action))
    elif action_type == "read_file_contexts":
        logger("reading file contexts", build_action_target(action))
    elif action_type == "output_contexts":
        logger("reading output contexts", build_action_target(action))
    elif action_type == "tail_file":
        logger("tailing file", getattr(action, "path"))
    elif action_type == "read_files":
        logger("reading files", build_action_target(action))
    elif action_type == "read_file_ranges":
        logger("reading file ranges", build_action_target(action))
    elif action_type == "file_info":
        logger("reading file info", build_action_target(action))
    elif action_type == "image_info":
        logger("reading image info", build_action_target(action))
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
    elif action_type == "code_reference_contexts":
        logger("reading code reference contexts", build_action_target(action))
    elif action_type == "code_definitions":
        logger("reading code definitions", build_action_target(action))
    elif action_type == "code_rename_preview":
        logger("previewing code rename", build_action_target(action))
    elif action_type == "code_rename":
        logger("renaming code symbol", build_action_target(action))
    elif action_type == "python_definitions":
        logger("reading python definitions", build_action_target(action))
    elif action_type == "python_calls":
        logger("reading python calls", build_action_target(action))
    elif action_type == "python_call_graph":
        logger("reading python call graph", build_action_target(action))
    elif action_type == "python_references":
        logger("reading python references", build_action_target(action))
    elif action_type == "python_reference_contexts":
        logger("reading python reference contexts", build_action_target(action))
    elif action_type == "python_rename_preview":
        logger("previewing python rename", build_action_target(action))
    elif action_type == "python_rename":
        logger("renaming python symbol", build_action_target(action))
    elif action_type == "search":
        logger("searching", getattr(action, "query"))
    elif action_type == "search_contexts":
        logger("searching contexts", build_action_target(action))
    elif action_type == "glob":
        logger("globbing", getattr(action, "pattern"))
    elif action_type == "git_status":
        logger("checking git status", None)
    elif action_type == "git_conflicts":
        logger("scanning git conflicts", getattr(action, "path", None) or ".")
    elif action_type == "git_diff_contexts":
        logger("reading git diff contexts", getattr(action, "path", None) or ".")
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
    elif action_type == "check_suggested_checks":
        logger("checking suggested checks", build_action_target(action))
    elif action_type == "run_suggested_checks":
        logger("running suggested checks", build_action_target(action))
    elif action_type == "project_commands":
        logger("reading project commands", None)
    elif action_type == "related_tests":
        logger("finding related tests", build_action_target(action))
    elif action_type == "focused_test_commands":
        logger("suggesting focused test commands", build_action_target(action))
    elif action_type == "check_focused_test_commands":
        logger("checking focused test commands", build_action_target(action))
    elif action_type == "run_focused_test_commands":
        logger("running focused test commands", build_action_target(action))
    elif action_type == "project_manifests":
        logger("reading project manifests", None)
    elif action_type == "project_instructions":
        logger("reading project instructions", None)
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
    elif action_type == "session_plan":
        logger("reading session plan", build_action_target(action))
    elif action_type == "session_transcript":
        logger("reading session transcript", build_action_target(action))
    elif action_type == "session_search":
        logger("searching session", build_action_target(action))
    elif action_type == "session_commands":
        logger("reading session commands", build_action_target(action))
    elif action_type == "session_output_contexts":
        logger("reading session output contexts", build_action_target(action))
    elif action_type == "session_output_diagnostics":
        logger("reading session output diagnostics", build_action_target(action))
    elif action_type == "session_files":
        logger("reading session files", build_action_target(action))
    elif action_type == "session_failures":
        logger("reading session failures", build_action_target(action))
    elif action_type == "session_verification":
        logger("reading session verification", build_action_target(action))
    elif action_type == "session_audit":
        logger("reading session audit", build_action_target(action))
    elif action_type == "session_handoff":
        logger("reading session handoff", build_action_target(action))
    elif action_type == "checkpoint_create":
        logger("creating checkpoint", build_action_target(action))
    elif action_type == "checkpoint_list":
        logger("listing checkpoints", build_action_target(action))
    elif action_type == "checkpoint_show":
        logger("reading checkpoint", build_action_target(action))
    elif action_type == "checkpoint_diff":
        logger("reading checkpoint diff", build_action_target(action))
    elif action_type == "checkpoint_status":
        logger("checking checkpoint status", build_action_target(action))
    elif action_type == "check_checkpoint_restore":
        logger("checking checkpoint restore", build_action_target(action))
    elif action_type == "checkpoint_restore":
        logger("restoring checkpoint", build_action_target(action))
    elif action_type == "check_checkpoint_delete":
        logger("checking checkpoint delete", build_action_target(action))
    elif action_type == "checkpoint_delete":
        logger("deleting checkpoint", build_action_target(action))
    elif action_type == "check_checkpoint_prune":
        logger("checking checkpoint prune", build_action_target(action))
    elif action_type == "checkpoint_prune":
        logger("pruning checkpoints", build_action_target(action))
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
    elif action_type == "http_fetch":
        logger("fetching http", build_action_target(action))
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
