from __future__ import annotations

from .session_types import SessionSummary
from .session_utils import compact


def final_review_resolved_by_completion(summary: SessionSummary) -> bool:
    return (
        summary.completed
        and not summary.failed
        and not summary.blocked
        and summary.final_review_seen
        and summary.final_review_ready is not True
        and summary.completion_ready is True
    )


def final_review_ready_label(ready: bool | None) -> str:
    return "yes" if ready is True else "no" if ready is False else "unknown"


def final_review_resolution_suffix(summary: SessionSummary) -> str:
    if final_review_resolved_by_completion(summary):
        return ", resolvedByCompletion=yes"
    return ""


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


def format_latest_completion_detail_lines(
    summary: SessionSummary,
    indent: str = "  ",
    max_text: int = 160,
) -> list[str]:
    lines: list[str] = []
    sections = [
        ("latestCompletionPendingChecks", summary.latest_completion_pending_verification_checks),
        ("latestCompletionFailedChecks", summary.latest_completion_failed_verification_checks),
        ("latestCompletionFinalReviewIssues", summary.latest_completion_final_review_issues),
        ("latestCompletionFinalReviewChangedFiles", summary.latest_completion_final_review_changed_files),
        ("latestCompletionToolErrors", summary.latest_completion_tool_errors),
        ("latestCompletionCheckpointFailures", summary.latest_completion_checkpoint_failures),
        ("latestCompletionActiveProcesses", summary.latest_completion_active_background_processes),
        ("latestCompletionDeniedApprovals", summary.latest_completion_denied_approvals),
        ("latestCompletionNextActions", summary.latest_completion_next_actions),
    ]
    for title, items in sections:
        append_bulleted_section(lines, title, items, indent=indent, max_text=max_text)
    return lines


def append_bulleted_section(
    lines: list[str],
    title: str,
    items: list[str],
    *,
    indent: str,
    max_text: int,
) -> None:
    if not items:
        return
    lines.append(f"{indent}{title}:")
    lines.extend(f"{indent}  - {compact(item, max_text)}" for item in items)
