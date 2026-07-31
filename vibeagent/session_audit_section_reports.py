from __future__ import annotations

from typing import Any

from .session_summary_reports import (
    CHECKPOINT_RESTORE_HINT,
    final_review_resolved_by_completion,
    session_summary_status,
)
from .session_types import SessionSummary
from .session_utils import compact


def build_audit_summary_section(summary: SessionSummary, max_text: int) -> dict[str, Any]:
    return {
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
        "subagentsStarted": summary.subagents_started,
        "subagentsCompleted": summary.subagents_completed,
        "subagentsFailed": summary.subagents_failed,
        "subagentToolCalls": len(summary.subagent_tool_calls),
        "subagentToolCallNames": summary.subagent_tool_calls,
        "latestSubagentFailures": [compact(failure, max_text) for failure in summary.latest_subagent_failures],
        "subagentContextCompacted": summary.subagent_context_compacted_count,
    }


def build_audit_final_review_section(summary: SessionSummary) -> dict[str, Any]:
    return {
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
    }


def build_audit_checkpoints_section(summary: SessionSummary) -> dict[str, Any]:
    return {
        "created": summary.checkpoints_created,
        "autoCreated": summary.auto_checkpoints_created,
        "latestId": summary.latest_checkpoint_id,
        "latestMessage": summary.latest_checkpoint_message,
        "restoreHint": CHECKPOINT_RESTORE_HINT if summary.latest_checkpoint_id else None,
    }


def build_audit_background_processes_section(
    summary: SessionSummary,
    *,
    max_processes: int,
    max_text: int,
) -> dict[str, Any]:
    shown_processes = summary.active_background_processes[:max_processes]
    return {
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
    }


def build_audit_completion_section(summary: SessionSummary, max_text: int) -> dict[str, Any]:
    return {
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
    }
