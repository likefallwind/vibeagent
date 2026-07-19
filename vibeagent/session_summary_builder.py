from __future__ import annotations

from pathlib import Path

from .session_store import read_session_events
from .session_summary_helpers import (
    checkpoint_result_id,
    parse_session_plan,
    parse_string_list,
    session_changed_file_labels,
    session_check_failure_labels,
    update_session_background_processes,
)
from .session_types import SessionPlanItem, SessionProcessInfo, SessionSummary
from .session_utils import (
    as_int,
    has_tool_call_content,
    is_failed_tool_result,
    model_text,
    parse_usage_payload,
    session_dir,
)
from .session_verification_state import session_verification_from_events


def summarize_session(project_root: str | Path, run_id: str) -> SessionSummary:
    session_path = session_dir(project_root, run_id)
    events = read_session_events(project_root, run_id)
    valid_events = [event for event in events if not event.malformed]
    malformed_count = len(events) - len(valid_events)
    iterations = max((as_int(event.payload.get("iteration")) or 0 for event in valid_events), default=0)

    tool_calls: list[str] = []
    approvals_requested = 0
    approvals_approved = 0
    approvals_denied = 0
    input_tokens = 0
    output_tokens = 0
    total_tokens = 0
    cache_creation_tokens = 0
    cache_read_tokens = 0
    task: str | None = None
    final_message: str | None = None
    latest_plan: list[SessionPlanItem] = []
    completed = False
    failed = False
    blocked = False
    final_review_seen = False
    final_review_ready: bool | None = None
    final_review_blocking_issues = 0
    final_review_warnings = 0
    final_review_files = 0
    final_review_changed_files: list[str] = []
    final_review_suggested_checks = 0
    final_review_message: str | None = None
    final_review_python_failures: list[str] = []
    final_review_config_failures: list[str] = []
    completion_ready: bool | None = None
    completion_blockers: list[str] = []
    completion_blocked_count = 0
    latest_completion_blockers: list[str] = []
    latest_completion_pending_verification_checks: list[str] = []
    latest_completion_failed_verification_checks: list[str] = []
    latest_completion_final_review_issues: list[str] = []
    latest_completion_final_review_changed_files: list[str] = []
    latest_completion_tool_errors: list[str] = []
    latest_completion_checkpoint_failures: list[str] = []
    latest_completion_active_background_processes: list[str] = []
    latest_completion_denied_approvals: list[str] = []
    latest_completion_next_actions: list[str] = []
    completion_warnings: list[str] = []
    verification_checks: list[str] = []
    pending_verification_checks: list[str] = []
    failed_verification_checks: list[str] = []
    verification_payload_seen = False
    checkpoints_created = 0
    auto_checkpoints_created = 0
    latest_checkpoint_id: str | None = None
    latest_checkpoint_message: str | None = None
    model_errors = 0
    latest_model_error: str | None = None
    background_processes_started = 0
    active_background_processes: dict[str, SessionProcessInfo] = {}
    subagents_started = 0
    subagents_completed = 0
    subagents_failed = 0
    subagent_tool_calls: list[str] = []
    subagent_context_compacted_count = 0

    for event in valid_events:
        if event.type == "task":
            event_task = event.payload.get("task")
            if isinstance(event_task, str):
                task = event_task
        elif event.type == "tool_call":
            name = event.payload.get("name")
            if isinstance(name, str):
                tool_calls.append(name)
        elif event.type == "approval_requested":
            approvals_requested += 1
        elif event.type == "approval_decision":
            decision = event.payload.get("decision")
            approved = decision.get("approved") if isinstance(decision, dict) else None
            if approved is True:
                approvals_approved += 1
            elif approved is False:
                approvals_denied += 1
        elif event.type in {"model", "subagent_model"}:
            usage = parse_usage_payload(event.payload.get("usage"))
            input_tokens += usage["input_tokens"]
            output_tokens += usage["output_tokens"]
            total_tokens += usage["total_tokens"]
            cache_creation_tokens += usage["cache_creation_tokens"]
            cache_read_tokens += usage["cache_read_tokens"]
            if event.type == "model":
                text = model_text(event.payload.get("content"))
                has_tool_call = has_tool_call_content(event.payload.get("content"))
                if text and not has_tool_call:
                    final_message = text
                    completed = True
        elif event.type in {"model_error", "subagent_model_error"}:
            model_errors += 1
            message = event.payload.get("message")
            if isinstance(message, str) and message.strip():
                latest_model_error = message.strip()
            failed = True
        elif event.type == "subagent_started":
            subagents_started += 1
        elif event.type == "subagent_tool_call":
            name = event.payload.get("name")
            if isinstance(name, str):
                subagent_tool_calls.append(name)
        elif event.type == "subagent_context_compacted":
            subagent_context_compacted_count += 1
        elif event.type == "subagent_completed":
            subagents_completed += 1
            result = event.payload.get("result")
            ok = result.get("ok") if isinstance(result, dict) else None
            if ok is False:
                subagents_failed += 1
        elif event.type == "completion_blocked":
            completion_blocked_count += 1
            blockers = event.payload.get("blockers")
            if isinstance(blockers, list):
                latest_completion_blockers = [item for item in blockers if isinstance(item, str) and item.strip()]
            details = event.payload.get("details")
            if isinstance(details, dict):
                (
                    latest_completion_pending_verification_checks,
                    latest_completion_failed_verification_checks,
                    latest_completion_final_review_issues,
                    latest_completion_final_review_changed_files,
                    latest_completion_tool_errors,
                    latest_completion_checkpoint_failures,
                    latest_completion_active_background_processes,
                    latest_completion_denied_approvals,
                    latest_completion_next_actions,
                ) = parse_completion_detail_lists(details)
            else:
                latest_completion_pending_verification_checks = []
                latest_completion_failed_verification_checks = []
                latest_completion_final_review_issues = []
                latest_completion_final_review_changed_files = []
                latest_completion_tool_errors = []
                latest_completion_checkpoint_failures = []
                latest_completion_active_background_processes = []
                latest_completion_denied_approvals = []
                latest_completion_next_actions = []
        elif event.type == "tool_result":
            result = event.payload.get("result")
            if isinstance(result, dict):
                kind = result.get("kind")
                if kind == "finish" and isinstance(result.get("message"), str):
                    final_message = result["message"]
                    completed = True
                if kind == "update_plan":
                    latest_plan = parse_session_plan(result.get("plan"))
                if kind == "final_review":
                    final_review_seen = True
                    ready = result.get("ready")
                    final_review_ready = ready if isinstance(ready, bool) else None
                    final_review_blocking_issues = len(result["blocking_issues"]) if isinstance(result.get("blocking_issues"), list) else 0
                    final_review_warnings = len(result["warnings"]) if isinstance(result.get("warnings"), list) else 0
                    total_files = as_int(result.get("total_files"))
                    final_review_files = total_files if total_files is not None else len(result["files"]) if isinstance(result.get("files"), list) else 0
                    final_review_changed_files = session_changed_file_labels(result.get("files"))
                    total_checks = as_int(result.get("suggested_checks_total"))
                    final_review_suggested_checks = total_checks if total_checks is not None else len(result["suggested_checks"]) if isinstance(result.get("suggested_checks"), list) else 0
                    review_message = result.get("message")
                    final_review_message = review_message if isinstance(review_message, str) and review_message.strip() else None
                    final_review_python_failures = session_check_failure_labels(result.get("python"))
                    final_review_config_failures = session_check_failure_labels(result.get("config"))
                update_session_background_processes(
                    active_background_processes,
                    result,
                    line_number=event.line_number,
                )
                if kind == "start_command" and result.get("ok") is True and isinstance(result.get("process_id"), str):
                    background_processes_started += 1
                if kind == "checkpoint_create" and result.get("ok") is True:
                    checkpoints_created += 1
                    if event.payload.get("auto") is True:
                        auto_checkpoints_created += 1
                    checkpoint_id = checkpoint_result_id(result)
                    if checkpoint_id:
                        latest_checkpoint_id = checkpoint_id
                    message = result.get("message")
                    if isinstance(message, str) and message.strip():
                        latest_checkpoint_message = message.strip()
                if is_failed_tool_result(result):
                    failed = True
        elif event.type == "result":
            success = event.payload.get("success")
            status = event.payload.get("status")
            message = event.payload.get("message")
            if isinstance(message, str) and message.strip():
                final_message = message
            result_iterations = as_int(event.payload.get("iterations"))
            if result_iterations is not None:
                iterations = max(iterations, result_iterations)
            result_plan = parse_session_plan(event.payload.get("plan"))
            if result_plan:
                latest_plan = result_plan
            ready = event.payload.get("completion_ready")
            if isinstance(ready, bool):
                completion_ready = ready
            result_blockers = event.payload.get("completion_blockers")
            if isinstance(result_blockers, list):
                completion_blockers = [item for item in result_blockers if isinstance(item, str) and item.strip()]
            result_warnings = event.payload.get("completion_warnings")
            if isinstance(result_warnings, list):
                completion_warnings = [item for item in result_warnings if isinstance(item, str) and item.strip()]
            result_details = event.payload.get("completion_details")
            if isinstance(result_details, dict):
                (
                    result_pending_checks,
                    result_failed_checks,
                    result_final_review_issues,
                    result_final_review_changed_files,
                    result_tool_errors,
                    result_checkpoint_failures,
                    result_active_background_processes,
                    result_denied_approvals,
                    result_next_actions,
                ) = parse_completion_detail_lists(result_details)
                if result_pending_checks:
                    latest_completion_pending_verification_checks = result_pending_checks
                if result_failed_checks:
                    latest_completion_failed_verification_checks = result_failed_checks
                if result_final_review_issues:
                    latest_completion_final_review_issues = result_final_review_issues
                if result_final_review_changed_files:
                    latest_completion_final_review_changed_files = result_final_review_changed_files
                if result_tool_errors:
                    latest_completion_tool_errors = result_tool_errors
                if result_checkpoint_failures:
                    latest_completion_checkpoint_failures = result_checkpoint_failures
                if result_active_background_processes:
                    latest_completion_active_background_processes = result_active_background_processes
                if result_denied_approvals:
                    latest_completion_denied_approvals = result_denied_approvals
                if result_next_actions:
                    latest_completion_next_actions = result_next_actions
            result_checks = event.payload.get("verification_checks")
            if isinstance(result_checks, list):
                verification_payload_seen = True
                verification_checks = [item for item in result_checks if isinstance(item, str) and item.strip()]
            pending_checks = event.payload.get("pending_verification_checks")
            if isinstance(pending_checks, list):
                verification_payload_seen = True
                pending_verification_checks = [item for item in pending_checks if isinstance(item, str) and item.strip()]
            failed_checks = event.payload.get("failed_verification_checks")
            if isinstance(failed_checks, list):
                verification_payload_seen = True
                failed_verification_checks = [item for item in failed_checks if isinstance(item, str) and item.strip()]
            if success is True:
                if completion_ready is False or status == "blocked":
                    completed = False
                    blocked = True
                else:
                    completed = True
                    blocked = False
                failed = False
            elif success is False:
                completed = False
                blocked = False
                failed = True
        elif event.type == "step_completed":
            step = event.payload.get("step")
            status = step.get("status") if isinstance(step, dict) else None
            if status in {"failed", "denied"}:
                failed = True

    if not verification_payload_seen:
        (
            verification_checks,
            pending_verification_checks,
            failed_verification_checks,
        ) = session_verification_from_events(valid_events)

    return SessionSummary(
        run_id=run_id,
        exists=session_path.is_dir(),
        event_count=len(valid_events),
        malformed_count=malformed_count,
        iterations=iterations,
        task=task,
        tool_calls=tool_calls,
        approvals_requested=approvals_requested,
        approvals_approved=approvals_approved,
        approvals_denied=approvals_denied,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        cache_creation_tokens=cache_creation_tokens,
        cache_read_tokens=cache_read_tokens,
        final_message=final_message,
        latest_plan=latest_plan,
        completed=completed,
        failed=failed,
        blocked=blocked,
        final_review_seen=final_review_seen,
        final_review_ready=final_review_ready,
        final_review_blocking_issues=final_review_blocking_issues,
        final_review_warnings=final_review_warnings,
        final_review_files=final_review_files,
        final_review_changed_files=final_review_changed_files,
        final_review_suggested_checks=final_review_suggested_checks,
        final_review_message=final_review_message,
        final_review_python_failures=final_review_python_failures,
        final_review_config_failures=final_review_config_failures,
        completion_ready=completion_ready,
        completion_blockers=completion_blockers,
        completion_blocked_count=completion_blocked_count,
        latest_completion_blockers=latest_completion_blockers,
        latest_completion_pending_verification_checks=latest_completion_pending_verification_checks,
        latest_completion_failed_verification_checks=latest_completion_failed_verification_checks,
        latest_completion_final_review_issues=latest_completion_final_review_issues,
        latest_completion_final_review_changed_files=latest_completion_final_review_changed_files,
        latest_completion_tool_errors=latest_completion_tool_errors,
        latest_completion_checkpoint_failures=latest_completion_checkpoint_failures,
        latest_completion_active_background_processes=latest_completion_active_background_processes,
        latest_completion_denied_approvals=latest_completion_denied_approvals,
        latest_completion_next_actions=latest_completion_next_actions,
        completion_warnings=completion_warnings,
        verification_checks=verification_checks,
        pending_verification_checks=pending_verification_checks,
        failed_verification_checks=failed_verification_checks,
        checkpoints_created=checkpoints_created,
        auto_checkpoints_created=auto_checkpoints_created,
        latest_checkpoint_id=latest_checkpoint_id,
        latest_checkpoint_message=latest_checkpoint_message,
        model_errors=model_errors,
        latest_model_error=latest_model_error,
        background_processes_started=background_processes_started,
        active_background_processes=sorted(active_background_processes.values(), key=lambda process: process.process_id),
        subagents_started=subagents_started,
        subagents_completed=subagents_completed,
        subagents_failed=subagents_failed,
        subagent_tool_calls=subagent_tool_calls,
        subagent_context_compacted_count=subagent_context_compacted_count,
    )


def parse_completion_detail_lists(details: dict[object, object]) -> tuple[
    list[str],
    list[str],
    list[str],
    list[str],
    list[str],
    list[str],
    list[str],
    list[str],
    list[str],
]:
    return (
        parse_string_list(details.get("pendingVerificationChecks")),
        parse_string_list(details.get("failedVerificationChecks")),
        parse_string_list(details.get("finalReviewBlockingIssues")),
        parse_string_list(details.get("finalReviewChangedFiles")),
        parse_string_list(details.get("toolErrors")),
        parse_string_list(details.get("checkpointFailures")),
        parse_string_list(details.get("activeBackgroundProcesses")),
        parse_string_list(details.get("deniedApprovals")),
        parse_string_list(details.get("nextActions")),
    )


__all__ = [
    "summarize_session",
]
