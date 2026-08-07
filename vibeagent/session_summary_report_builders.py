from __future__ import annotations

from typing import Any

from .session_summary_completion_reports import final_review_resolved_by_completion
from .session_types import SessionProcessInfo, SessionSummary
from .session_utils import compact


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
            "resolvedByCompletion": final_review_resolved_by_completion(summary),
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
            "latestNextActions": summary.latest_completion_next_actions,
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
            "restoreHint": CHECKPOINT_RESTORE_HINT if summary.latest_checkpoint_id else None,
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
        "subagents": {
            "started": summary.subagents_started,
            "completed": summary.subagents_completed,
            "failed": summary.subagents_failed,
            "toolCalls": {
                "total": len(summary.subagent_tool_calls),
                "names": summary.subagent_tool_calls,
            },
            "latestFailures": summary.latest_subagent_failures,
            "contextCompacted": summary.subagent_context_compacted_count,
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


def session_summary_status(summary: SessionSummary) -> str:
    if summary.completed:
        return "completed"
    if summary.failed:
        return "failed"
    if summary.blocked:
        return "blocked"
    return "incomplete"


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
                **({"activeForm": item.active_form} if item.active_form else {}),
            }
            for item in summary.latest_plan
        ],
        "message": f"Found {len(summary.latest_plan)} plan item(s).",
    }
