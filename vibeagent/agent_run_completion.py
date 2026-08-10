from __future__ import annotations

from collections.abc import Callable

from .agent_completion import (
    VerificationStatus,
    auto_final_review_reason,
    build_completion_blocker_details,
    build_completion_blockers,
    build_completion_warnings,
    build_final_review_changed_file_details,
    resolve_completion_verification_status,
    format_completion_blocked_feedback,
)
from .agent_observation_utils import summarize
from .agent_result import AgentResult
from .agent_runtime_utils import append_session_event, to_jsonable
from .agent_steps import observation_summary
from .agent_tool_results import record_tool_result_event
from .background_delegate_runtime import close_background_delegate_tasks
from .agent_team_runtime import clear_team_runtime
from .session import read_session_events, summarize_session
from .session_verification_state import session_verification_from_events
from .types import AgentLogger, FinalReviewAction, Observation, PlanItem, TaskStep
from .workspace_core import RunWorkspace


ExecuteActionSafely = Callable[[RunWorkspace, object, int, str], Observation]


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
    execute_action_safely_func: ExecuteActionSafely,
) -> str | None:
    if not success or iteration >= max_iterations:
        return None
    auto_run_final_review_if_needed(
        workspace,
        success,
        observations,
        iteration,
        command_timeout_ms,
        logger,
        execute_action_safely_func,
    )
    verification_status = session_completion_verification_status(workspace)
    blockers = build_completion_blockers(success, observations, plan, verification_status)
    if not blockers:
        return None
    details = build_completion_blocker_details(success, observations, verification_status, blockers)
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
    execute_action_safely_func: ExecuteActionSafely,
    *,
    stop_reason: str | None = None,
    deferred_tool_use: dict[str, object] | None = None,
    is_error: bool = False,
) -> AgentResult:
    background_close = close_background_delegate_tasks(workspace)
    clear_team_runtime(workspace)
    if background_close.task_ids:
        append_session_event(
            workspace.session_dir,
            "background_delegate_tasks_closed",
            {
                "task_ids": list(background_close.task_ids),
                "cancel_requested_task_ids": list(background_close.cancel_requested_task_ids),
                "discarded_task_ids": list(background_close.discarded_task_ids),
                "still_running_task_ids": list(background_close.still_running_task_ids),
            },
        )
    suspended = stop_reason in {"tool_deferred", "tool_deferred_unavailable"}
    if not suspended:
        auto_run_final_review_if_needed(
            workspace,
            success,
            observations,
            iterations,
            command_timeout_ms,
            logger,
            execute_action_safely_func,
        )
    verification_status = session_completion_verification_status(workspace)
    completion_blockers = (
        []
        if suspended
        else build_completion_blockers(success, observations, plan, verification_status)
    )
    completion_ready = success and not completion_blockers and not suspended
    result_status = (
        "deferred"
        if stop_reason == "tool_deferred"
        else session_result_status(success, completion_ready)
    )
    completion_warnings = (
        []
        if suspended
        else build_completion_warnings(success, observations, plan, verification_status)
    )
    completion_details = build_completion_blocker_details(success, observations, verification_status, completion_blockers)
    verification_checks, pending_verification_checks, failed_verification_checks = resolve_completion_verification_status(
        success,
        observations,
        verification_status,
    )
    final_review_changed_files = build_final_review_changed_file_details(observations)
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
            "completion_details": completion_details,
            "verification_checks": verification_checks,
            "pending_verification_checks": pending_verification_checks,
            "failed_verification_checks": failed_verification_checks,
            "final_review_changed_files": final_review_changed_files,
            "stop_reason": stop_reason,
            "deferred_tool_use": deferred_tool_use,
            "is_error": is_error,
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
        latest_completion_final_review_issues=session_summary.latest_completion_final_review_issues,
        latest_completion_final_review_changed_files=session_summary.latest_completion_final_review_changed_files,
        latest_completion_tool_errors=session_summary.latest_completion_tool_errors,
        latest_completion_checkpoint_failures=session_summary.latest_completion_checkpoint_failures,
        latest_completion_active_background_processes=session_summary.latest_completion_active_background_processes,
        latest_completion_denied_approvals=session_summary.latest_completion_denied_approvals,
        latest_completion_next_actions=session_summary.latest_completion_next_actions,
        final_review_changed_files=session_summary.final_review_changed_files,
        stop_reason=stop_reason,
        deferred_tool_use=deferred_tool_use,
        is_error=is_error,
    )


def session_result_status(success: bool, completion_ready: bool) -> str:
    if not success:
        return "failed"
    if completion_ready:
        return "completed"
    return "blocked"


def session_completion_verification_status(workspace: RunWorkspace) -> VerificationStatus | None:
    status = session_verification_from_events(read_session_events(workspace.root, workspace.run_id))
    return status if any(status) else None


def auto_run_final_review_if_needed(
    workspace: RunWorkspace,
    success: bool,
    observations: list[Observation],
    iteration: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
    execute_action_safely_func: ExecuteActionSafely,
) -> None:
    reason = auto_final_review_reason(success, observations)
    if reason is None:
        return

    if logger:
        logger("auto final_review", f"{reason}; running read-only final review.")
    action = FinalReviewAction(type="final_review")
    observation = execute_action_safely_func(workspace, action, command_timeout_ms, "final_review")
    observations.append(observation)
    record_tool_result_event(
        workspace,
        tool_id="auto-final-review",
        tool_name="final_review",
        observation=observation,
        iteration=iteration,
        auto=True,
    )
    if logger:
        logger("auto final_review result", observation_summary(observation))
