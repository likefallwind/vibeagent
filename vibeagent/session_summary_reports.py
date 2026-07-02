from __future__ import annotations

from datetime import datetime
from typing import Any

from .session_types import SessionProcessInfo, SessionSummary
from .session_utils import compact, count_names


CHECKPOINT_RESTORE_HINT = "/check-checkpoint-restore latest"


def build_session_summary_report(summary: SessionSummary, max_text: int = 500) -> dict[str, Any]:
    if not summary.exists:
        return {
            "session": summary.run_id,
            "exists": False,
            "ok": False,
            "status": "missing",
            "message": f"Session not found: {summary.run_id}",
        }
    return {
        "session": summary.run_id,
        "exists": True,
        "ok": True,
        "status": session_summary_status(summary),
        "events": {
            "total": summary.event_count,
            "malformed": summary.malformed_count,
            "iterations": summary.iterations,
        },
        "task": compact(summary.task, max_text) if summary.task else None,
        "toolCalls": {
            "total": len(summary.tool_calls),
            "names": summary.tool_calls,
        },
        "approvals": {
            "requested": summary.approvals_requested,
            "approved": summary.approvals_approved,
            "denied": summary.approvals_denied,
        },
        "tokens": {
            "input": summary.input_tokens,
            "output": summary.output_tokens,
            "total": summary.total_tokens,
            "cacheCreation": summary.cache_creation_tokens,
            "cacheRead": summary.cache_read_tokens,
        },
        "plan": {
            "status": session_plan_status(summary),
            "items": [
                {
                    "status": item.status,
                    "step": item.step,
                }
                for item in summary.latest_plan
            ],
        },
        "finalReview": {
            "seen": summary.final_review_seen,
            "ready": summary.final_review_ready,
            "blockingIssues": summary.final_review_blocking_issues,
            "warnings": summary.final_review_warnings,
            "files": summary.final_review_files,
            "changedFiles": summary.final_review_changed_files,
            "suggestedChecks": summary.final_review_suggested_checks,
            "message": compact(summary.final_review_message, max_text) if summary.final_review_message else None,
            "pythonFailures": summary.final_review_python_failures,
            "configFailures": summary.final_review_config_failures,
        },
        "completion": {
            "ready": summary.completion_ready,
            "blockers": summary.completion_blockers,
            "blockedCount": summary.completion_blocked_count,
            "latestBlockers": summary.latest_completion_blockers,
            "latestPendingVerificationChecks": summary.latest_completion_pending_verification_checks,
            "latestFailedVerificationChecks": summary.latest_completion_failed_verification_checks,
            "latestFinalReviewBlockingIssues": summary.latest_completion_final_review_issues,
            "latestFinalReviewChangedFiles": summary.latest_completion_final_review_changed_files,
            "latestToolErrors": summary.latest_completion_tool_errors,
            "latestCheckpointFailures": summary.latest_completion_checkpoint_failures,
            "latestActiveBackgroundProcesses": summary.latest_completion_active_background_processes,
            "latestDeniedApprovals": summary.latest_completion_denied_approvals,
            "warnings": summary.completion_warnings,
        },
        "verification": {
            "verified": summary.verification_checks,
            "pending": summary.pending_verification_checks,
            "failed": summary.failed_verification_checks,
        },
        "checkpoints": {
            "created": summary.checkpoints_created,
            "autoCreated": summary.auto_checkpoints_created,
            "latestId": summary.latest_checkpoint_id,
            "latestMessage": compact(summary.latest_checkpoint_message, max_text) if summary.latest_checkpoint_message else None,
        },
        "modelErrors": {
            "total": summary.model_errors,
            "latest": compact(summary.latest_model_error, max_text) if summary.latest_model_error else None,
        },
        "backgroundProcesses": {
            "started": summary.background_processes_started,
            "active": [
                serialize_session_process(process)
                for process in summary.active_background_processes
            ],
        },
        "finalMessage": compact(summary.final_message, max_text) if summary.final_message else None,
        "message": f"Read session summary for {summary.run_id}.",
    }


def serialize_session_process(process: SessionProcessInfo) -> dict[str, Any]:
    return {
        "processId": process.process_id,
        "pid": process.pid,
        "command": process.command,
        "cwd": process.cwd,
        "lineNumber": process.line_number,
    }


def format_session_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def session_summary_status(summary: SessionSummary) -> str:
    if summary.completed:
        return "completed"
    if summary.failed:
        return "failed"
    if summary.blocked:
        return "blocked"
    return "incomplete"


def format_final_review_failure_lines(summary: SessionSummary, indent: str = "  ", max_text: int = 160) -> list[str]:
    failures = [
        ("python", item)
        for item in summary.final_review_python_failures
    ] + [
        ("config", item)
        for item in summary.final_review_config_failures
    ]
    if not failures:
        return []
    lines = [f"{indent}finalReviewFailures:"]
    lines.extend(f"{indent}  - {kind}: {compact(item, max_text)}" for kind, item in failures[:20])
    if len(failures) > 20:
        lines.append(f"{indent}  - ... {len(failures) - 20} more")
    return lines


def format_session_summary(summary: SessionSummary) -> str:
    if not summary.exists:
        return f"Session not found: {summary.run_id}"

    tool_counts = count_names(summary.tool_calls)
    tools = ", ".join(f"{name} x{count}" if count > 1 else name for name, count in tool_counts.items())
    status = session_summary_status(summary)
    lines = [
        f"Session: {summary.run_id}",
        f"  status: {status}",
        f"  events: {summary.event_count}",
        f"  iterations: {summary.iterations}",
        f"  tools: {tools or 'none'}",
        (
            "  approvals: "
            f"{summary.approvals_requested} requested, "
            f"{summary.approvals_approved} approved, "
            f"{summary.approvals_denied} denied"
        ),
    ]
    if summary.total_tokens or summary.input_tokens or summary.output_tokens:
        lines.append(
            "  tokens: "
            f"{summary.input_tokens} input, "
            f"{summary.output_tokens} output, "
            f"{summary.total_tokens} total"
        )
    if summary.cache_creation_tokens or summary.cache_read_tokens:
        lines.append(
            "  cacheTokens: "
            f"{summary.cache_creation_tokens} created, "
            f"{summary.cache_read_tokens} read"
        )
    if summary.malformed_count:
        lines.append(f"  malformedRows: {summary.malformed_count}")
    if summary.model_errors:
        error_line = f"  modelErrors: {summary.model_errors}"
        if summary.latest_model_error:
            error_line += f", latest={compact(summary.latest_model_error, 180)}"
        lines.append(error_line)
    if summary.background_processes_started or summary.active_background_processes:
        lines.append(
            "  backgroundProcesses: "
            f"started={summary.background_processes_started}, "
            f"active={len(summary.active_background_processes)}"
        )
    if summary.task:
        lines.append(f"  task: {compact(summary.task, 240)}")
    if summary.checkpoints_created:
        checkpoint_line = (
            "  checkpoints: "
            f"created={summary.checkpoints_created}, "
            f"auto={summary.auto_checkpoints_created}"
        )
        if summary.latest_checkpoint_id:
            checkpoint_line += f", latest={compact(summary.latest_checkpoint_id, 80)}"
        if summary.latest_checkpoint_message:
            checkpoint_line += f", message={compact(summary.latest_checkpoint_message, 160)}"
        lines.append(checkpoint_line)
        if summary.latest_checkpoint_id:
            lines.append(f"  restoreHint: {CHECKPOINT_RESTORE_HINT}")
    if summary.latest_plan:
        lines.append("  plan:")
        lines.extend(f"    - {item.status}: {compact(item.step, 160)}" for item in summary.latest_plan)
    if summary.final_review_seen:
        ready = "yes" if summary.final_review_ready is True else "no" if summary.final_review_ready is False else "unknown"
        final_review = (
            f"  finalReview: ready={ready}, "
            f"blocking={summary.final_review_blocking_issues}, "
            f"warnings={summary.final_review_warnings}, "
            f"files={summary.final_review_files}, "
            f"suggestedChecks={summary.final_review_suggested_checks}"
        )
        if summary.final_review_message:
            final_review += f", message={compact(summary.final_review_message, 160)}"
        lines.append(final_review)
        if summary.final_review_changed_files:
            lines.append("  finalReviewChangedFiles:")
            lines.extend(f"    - {compact(path, 160)}" for path in summary.final_review_changed_files)
        lines.extend(format_final_review_failure_lines(summary, indent="  ", max_text=160))
    if summary.completion_ready is not None:
        lines.append(f"  completionReady: {'yes' if summary.completion_ready else 'no'}")
    if summary.completion_blockers:
        lines.append("  completionBlockers:")
        lines.extend(f"    - {compact(blocker, 160)}" for blocker in summary.completion_blockers)
    if summary.completion_blocked_count:
        lines.append(f"  completionBlocked: {summary.completion_blocked_count}")
        if summary.latest_completion_blockers:
            lines.append("  latestCompletionBlockers:")
            lines.extend(f"    - {compact(blocker, 160)}" for blocker in summary.latest_completion_blockers)
        lines.extend(format_latest_completion_detail_lines(summary, indent="  ", max_text=160))
    if summary.completion_warnings:
        lines.append("  completionWarnings:")
        lines.extend(f"    - {compact(warning, 160)}" for warning in summary.completion_warnings)
    if summary.verification_checks:
        lines.append("  verified:")
        lines.extend(f"    - {compact(check, 160)}" for check in summary.verification_checks)
    if summary.pending_verification_checks:
        lines.append("  pendingChecks:")
        lines.extend(f"    - {compact(check, 160)}" for check in summary.pending_verification_checks)
    if summary.failed_verification_checks:
        lines.append("  failedChecks:")
        lines.extend(f"    - {compact(check, 160)}" for check in summary.failed_verification_checks)
    if summary.final_message:
        lines.append(f"  final: {compact(summary.final_message, 240)}")
    return "\n".join(lines)


def format_session_plan(summary: SessionSummary) -> str:
    if not summary.exists:
        return f"Session not found: {summary.run_id}"

    status = session_plan_status(summary)
    lines = [
        "Plan:",
        f"  session: {summary.run_id}",
        f"  status: {status}",
    ]
    if summary.task:
        lines.append(f"  task: {compact(summary.task, 240)}")
    if summary.latest_plan:
        lines.append("  items:")
        lines.extend(f"    - {item.status}: {compact(item.step, 200)}" for item in summary.latest_plan)
    else:
        lines.append("  items: none")
    return "\n".join(lines)


def session_plan_status(summary: SessionSummary) -> str:
    plan_statuses = {item.status for item in summary.latest_plan}
    if "in_progress" in plan_statuses:
        return "in_progress"
    return session_summary_status(summary)


def build_session_plan_report(summary: SessionSummary) -> dict[str, Any]:
    if not summary.exists:
        return {
            "session": summary.run_id,
            "exists": False,
            "ok": False,
            "status": "missing",
            "message": f"Session not found: {summary.run_id}",
        }
    status = session_plan_status(summary)
    return {
        "session": summary.run_id,
        "exists": True,
        "ok": True,
        "status": status,
        "task": summary.task,
        "items": [
            {
                "status": item.status,
                "step": item.step,
            }
            for item in summary.latest_plan
        ],
        "message": f"Found {len(summary.latest_plan)} plan item(s).",
    }


def format_latest_completion_detail_lines(
    summary: SessionSummary,
    indent: str = "  ",
    max_text: int = 160,
) -> list[str]:
    lines: list[str] = []
    if summary.latest_completion_pending_verification_checks:
        lines.append(f"{indent}latestCompletionPendingChecks:")
        lines.extend(
            f"{indent}  - {compact(check, max_text)}"
            for check in summary.latest_completion_pending_verification_checks
        )
    if summary.latest_completion_failed_verification_checks:
        lines.append(f"{indent}latestCompletionFailedChecks:")
        lines.extend(
            f"{indent}  - {compact(check, max_text)}"
            for check in summary.latest_completion_failed_verification_checks
        )
    if summary.latest_completion_final_review_issues:
        lines.append(f"{indent}latestCompletionFinalReviewIssues:")
        lines.extend(
            f"{indent}  - {compact(issue, max_text)}"
            for issue in summary.latest_completion_final_review_issues
        )
    if summary.latest_completion_final_review_changed_files:
        lines.append(f"{indent}latestCompletionFinalReviewChangedFiles:")
        lines.extend(
            f"{indent}  - {compact(path, max_text)}"
            for path in summary.latest_completion_final_review_changed_files
        )
    if summary.latest_completion_tool_errors:
        lines.append(f"{indent}latestCompletionToolErrors:")
        lines.extend(
            f"{indent}  - {compact(error, max_text)}"
            for error in summary.latest_completion_tool_errors
        )
    if summary.latest_completion_checkpoint_failures:
        lines.append(f"{indent}latestCompletionCheckpointFailures:")
        lines.extend(
            f"{indent}  - {compact(failure, max_text)}"
            for failure in summary.latest_completion_checkpoint_failures
        )
    if summary.latest_completion_active_background_processes:
        lines.append(f"{indent}latestCompletionActiveProcesses:")
        lines.extend(
            f"{indent}  - {compact(process, max_text)}"
            for process in summary.latest_completion_active_background_processes
        )
    if summary.latest_completion_denied_approvals:
        lines.append(f"{indent}latestCompletionDeniedApprovals:")
        lines.extend(
            f"{indent}  - {compact(approval, max_text)}"
            for approval in summary.latest_completion_denied_approvals
        )
    return lines
