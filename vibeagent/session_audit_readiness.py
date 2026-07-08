from __future__ import annotations

from typing import Any

from .session_audit_serialization import failed_checkpoint_create_count
from .session_types import SessionPlanItem, SessionSummary


def session_pending_plan_items(summary: SessionSummary) -> list[SessionPlanItem]:
    return [
        item
        for item in summary.latest_plan
        if item.status not in {"completed", "done", "skipped"}
    ]


def session_audit_blockers(
    summary: SessionSummary,
    failures: list[dict[str, str | int]],
    files: list[dict[str, Any]],
) -> list[str]:
    blockers: list[str] = []
    pending_plan_items = session_pending_plan_items(summary)
    checkpoint_failures = failed_checkpoint_create_count(failures)
    if summary.failed:
        blockers.append("session status is failed")
    elif summary.blocked:
        blockers.append("session status is blocked")
    elif not summary.completed:
        blockers.append("session status is incomplete")
    if summary.completion_ready is False:
        if summary.completion_blockers:
            blockers.append(f"{len(summary.completion_blockers)} completion blocker(s)")
        else:
            blockers.append("completion is not ready")
    if summary.malformed_count:
        blockers.append(f"{summary.malformed_count} malformed session row(s)")
    denied_approval_blocker_count = session_audit_denied_approval_blocker_count(summary)
    if denied_approval_blocker_count:
        blockers.append(f"{denied_approval_blocker_count} denied approval(s)")
    if failures and (summary.failed or not summary.completed):
        blockers.append(f"{len(failures)} failure event(s)")
    if checkpoint_failures:
        blockers.append(f"{checkpoint_failures} checkpoint creation failure(s); restore point may be unavailable")
    if summary.final_review_seen and summary.final_review_ready is False and summary.completion_ready is not True:
        blockers.append("final review is not ready")
    if not summary.final_review_seen and files:
        blockers.append("changed files exist but final_review has not run")
    if not summary.final_review_seen and summary.background_processes_started:
        blockers.append("background process(es) were started but final_review has not run")
    if summary.pending_verification_checks:
        blockers.append(f"{len(summary.pending_verification_checks)} pending verification check(s)")
    if summary.failed_verification_checks:
        blockers.append(f"{len(summary.failed_verification_checks)} failed verification check(s)")
    if pending_plan_items:
        blockers.append(f"{len(pending_plan_items)} non-completed plan item(s)")
    if summary.active_background_processes:
        blockers.append(f"{len(summary.active_background_processes)} active background process(es)")
    return blockers


def session_audit_denied_approval_blocker_count(summary: SessionSummary) -> int:
    if summary.completion_ready is True:
        return 0
    if summary.latest_completion_denied_approvals:
        return len(summary.latest_completion_denied_approvals)
    if summary.completion_ready is False or not summary.completed:
        return summary.approvals_denied
    return 0
