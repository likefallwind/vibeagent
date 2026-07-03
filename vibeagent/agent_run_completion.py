from __future__ import annotations

from collections.abc import Callable

from .agent_completion import (
    auto_final_review_reason,
    build_completion_blocker_details,
    build_completion_blockers,
    build_completion_warnings,
    build_failed_verification_checks,
    build_final_review_changed_file_details,
    build_pending_verification_checks,
    build_verification_checks,
    format_completion_blocked_feedback,
)
from .agent_observation_utils import summarize
from .agent_result import AgentResult
from .agent_runtime_utils import append_session_event, to_jsonable
from .agent_steps import observation_summary
from .redaction import redact_jsonable_payload
from .session import summarize_session
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
) -> AgentResult:
    auto_run_final_review_if_needed(
        workspace,
        success,
        observations,
        iterations,
        command_timeout_ms,
        logger,
        execute_action_safely_func,
    )
    completion_blockers = build_completion_blockers(success, observations, plan)
    completion_ready = success and not completion_blockers
    result_status = session_result_status(success, completion_ready)
    completion_warnings = build_completion_warnings(success, observations, plan)
    verification_checks = build_verification_checks(success, observations)
    pending_verification_checks = build_pending_verification_checks(success, observations)
    failed_verification_checks = build_failed_verification_checks(success, observations)
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
            "verification_checks": verification_checks,
            "pending_verification_checks": pending_verification_checks,
            "failed_verification_checks": failed_verification_checks,
            "final_review_changed_files": final_review_changed_files,
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
        final_review_changed_files=session_summary.final_review_changed_files,
    )


def session_result_status(success: bool, completion_ready: bool) -> str:
    if not success:
        return "failed"
    if completion_ready:
        return "completed"
    return "blocked"


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
    result_payload = redact_jsonable_payload(to_jsonable(observation))
    append_session_event(
        workspace.session_dir,
        "tool_result",
        {
            "iteration": iteration,
            "id": "auto-final-review",
            "name": "final_review",
            "auto": True,
            "result": result_payload,
        },
    )
    if logger:
        logger("auto final_review result", observation_summary(observation))
