from __future__ import annotations

from typing import Any

from .session_summary_reports import (
    CHECKPOINT_RESTORE_HINT,
    final_review_resolved_by_completion,
    session_summary_status,
)
from .session_audit_formatting import (
    format_session_audit_report_text,
    format_session_handoff_report_text,
    format_session_verification_report_text,
)
from .session_audit_serialization import (
    failed_checkpoint_create_count,
    serialize_session_command_entry,
    serialize_session_failure,
    validate_session_audit_limits,
    validate_session_handoff_limits,
)
from .session_audit_readiness import (
    session_audit_blockers,
    session_audit_denied_approval_blocker_count,
    session_pending_plan_items,
)
from .session_audit_text import (
    format_session_audit_from_parts,
    format_session_handoff_readiness,
    format_session_handoff_sections,
)
from .session_types import SessionSummary
from .session_utils import compact
from .session_verification_reports import limited_string_group


def build_session_audit_report_from_parts(
    run_id: str,
    summary: SessionSummary,
    failures: list[dict[str, str | int]],
    command_entries: list[dict[str, Any]],
    files: list[dict[str, Any]],
    max_failures: int = 10,
    max_files: int = 20,
    max_commands: int = 10,
    max_checks: int = 50,
    max_text: int = 300,
) -> dict[str, Any]:
    pending_plan_items = session_pending_plan_items(summary)
    blockers = session_audit_blockers(summary, failures, files)
    plan_statuses = {item.status for item in summary.latest_plan}
    shown_failures = failures[-max_failures:]
    shown_commands = command_entries[-max_commands:]
    shown_files = files[:max_files]
    shown_processes = summary.active_background_processes[:max_failures]

    return {
        "session": run_id,
        "exists": True,
        "ok": not blockers,
        "ready": not blockers,
        "status": "ready" if not blockers else "blocked",
        "summary": {
            "sessionStatus": session_summary_status(summary),
            "events": summary.event_count,
            "malformedRows": summary.malformed_count,
            "iterations": summary.iterations,
            "toolCalls": len(summary.tool_calls),
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
            "task": summary.task,
            "completed": summary.completed,
            "failed": summary.failed,
            "blocked": summary.blocked,
            "modelErrors": summary.model_errors,
            "latestModelError": summary.latest_model_error,
            "subagentContextCompacted": summary.subagent_context_compacted_count,
        },
        "finalReview": {
            "seen": summary.final_review_seen,
            "ready": summary.final_review_ready,
            "resolvedByCompletion": final_review_resolved_by_completion(summary),
            "blockingIssues": summary.final_review_blocking_issues,
            "warnings": summary.final_review_warnings,
            "files": summary.final_review_files,
            "changedFiles": summary.final_review_changed_files,
            "suggestedChecks": summary.final_review_suggested_checks,
            "message": summary.final_review_message,
            "failures": {
                "python": summary.final_review_python_failures,
                "config": summary.final_review_config_failures,
            },
        },
        "checkpoints": {
            "created": summary.checkpoints_created,
            "autoCreated": summary.auto_checkpoints_created,
            "latestId": summary.latest_checkpoint_id,
            "latestMessage": summary.latest_checkpoint_message,
            "restoreHint": CHECKPOINT_RESTORE_HINT if summary.latest_checkpoint_id else None,
        },
        "backgroundProcesses": {
            "started": summary.background_processes_started,
            "active": len(summary.active_background_processes),
            "shown": len(shown_processes),
            "truncated": len(summary.active_background_processes) > len(shown_processes),
            "processes": [
                {
                    "processId": process.process_id,
                    "pid": process.pid,
                    "cwd": compact(process.cwd, max_text),
                    "command": compact(process.command, max_text),
                    "lineNumber": process.line_number,
                }
                for process in shown_processes
            ],
        },
        "blockers": {
            "count": len(blockers),
            "items": [compact(blocker, max_text) for blocker in blockers],
        },
        "completion": {
            "ready": summary.completion_ready,
            "blockers": [compact(blocker, max_text) for blocker in summary.completion_blockers],
            "blockedCount": summary.completion_blocked_count,
            "latestBlockers": [compact(blocker, max_text) for blocker in summary.latest_completion_blockers],
            "latestPendingVerificationChecks": [
                compact(check, max_text)
                for check in summary.latest_completion_pending_verification_checks
            ],
            "latestFailedVerificationChecks": [
                compact(check, max_text)
                for check in summary.latest_completion_failed_verification_checks
            ],
            "latestFinalReviewBlockingIssues": [
                compact(issue, max_text)
                for issue in summary.latest_completion_final_review_issues
            ],
            "latestFinalReviewChangedFiles": [
                compact(path, max_text)
                for path in summary.latest_completion_final_review_changed_files
            ],
            "latestToolErrors": [
                compact(error, max_text)
                for error in summary.latest_completion_tool_errors
            ],
            "latestCheckpointFailures": [
                compact(failure, max_text)
                for failure in summary.latest_completion_checkpoint_failures
            ],
            "latestActiveBackgroundProcesses": [
                compact(process, max_text)
                for process in summary.latest_completion_active_background_processes
            ],
            "latestDeniedApprovals": [
                compact(approval, max_text)
                for approval in summary.latest_completion_denied_approvals
            ],
            "latestNextActions": [
                compact(action, max_text)
                for action in summary.latest_completion_next_actions
            ],
            "warnings": [compact(warning, max_text) for warning in summary.completion_warnings],
        },
        "verification": {
            "verified": limited_string_group(summary.verification_checks, max_checks, max_text, status="verified"),
            "pending": limited_string_group(summary.pending_verification_checks, max_checks, max_text, status="pending"),
            "failed": limited_string_group(summary.failed_verification_checks, max_checks, max_text, status="failed"),
        },
        "plan": {
            "items": len(summary.latest_plan),
            "inProgress": "in_progress" in plan_statuses,
            "pending": {
                "total": len(pending_plan_items),
                "shown": min(len(pending_plan_items), max_failures),
                "truncated": len(pending_plan_items) > max_failures,
                "items": [
                    {"status": item.status, "step": compact(item.step, max_text)}
                    for item in pending_plan_items[:max_failures]
                ],
            },
        },
        "failures": {
            "total": len(failures),
            "shown": len(shown_failures),
            "truncated": len(failures) > len(shown_failures),
            "items": [serialize_session_failure(failure, max_text) for failure in shown_failures],
        },
        "commands": {
            "total": len(command_entries),
            "shown": len(shown_commands),
            "truncated": len(command_entries) > len(shown_commands),
            "items": [serialize_session_command_entry(entry, max_text) for entry in shown_commands],
        },
        "files": {
            "total": len(files),
            "shown": len(shown_files),
            "truncated": len(files) > len(shown_files),
            "items": [
                {
                    "path": compact(str(file_entry.get("path", "unknown")), max_text),
                    "uses": file_entry.get("uses") if isinstance(file_entry.get("uses"), list) else [],
                }
                for file_entry in shown_files
            ],
        },
        "message": "Session is ready." if not blockers else f"Session has {len(blockers)} blocker(s).",
    }


def build_session_handoff_report_from_sections(
    run_id: str,
    audit: dict[str, Any],
    sections: dict[str, str],
    max_failures: int,
    max_files: int,
    max_commands: int,
    max_checks: int,
    max_output_chars: int,
    max_text: int,
) -> dict[str, Any]:
    ready = audit.get("ready") is True
    return {
        "session": run_id,
        "exists": True,
        "ok": ready,
        "ready": ready,
        "status": audit.get("status", "ready" if ready else "blocked"),
        "audit": audit,
        "sections": sections,
        "limits": {
            "maxFailures": max_failures,
            "maxFiles": max_files,
            "maxCommands": max_commands,
            "maxChecks": max_checks,
            "maxOutputChars": max_output_chars,
            "maxText": max_text,
        },
        "message": "Session handoff is ready." if ready else "Session handoff has blocker(s).",
    }
