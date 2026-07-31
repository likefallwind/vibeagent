from __future__ import annotations

from .session_summary_reports import (
    CHECKPOINT_RESTORE_HINT,
    final_review_ready_label,
    final_review_resolution_suffix,
    format_final_review_failure_lines,
    format_latest_completion_detail_lines,
)
from .session_types import SessionSummary
from .session_utils import compact


def append_final_review_lines(
    lines: list[str],
    summary: SessionSummary,
    *,
    max_text: int,
    include_counts: bool,
    changed_file_limit: int | None = None,
) -> None:
    if summary.final_review_seen:
        ready = final_review_ready_label(summary.final_review_ready)
        counts = (
            f", files={summary.final_review_files}, "
            f"suggestedChecks={summary.final_review_suggested_checks}"
            if include_counts
            else ""
        )
        lines.append(
            "  finalReview: "
            f"ready={ready}, "
            f"blocking={summary.final_review_blocking_issues}, "
            f"warnings={summary.final_review_warnings}"
            f"{counts}"
            f"{final_review_resolution_suffix(summary)}"
        )
        if summary.final_review_changed_files:
            lines.append("  finalReviewChangedFiles:")
            shown_files = (
                summary.final_review_changed_files
                if changed_file_limit is None
                else summary.final_review_changed_files[:changed_file_limit]
            )
            lines.extend(f"    - {compact(path, max_text)}" for path in shown_files)
            if changed_file_limit is not None and len(summary.final_review_changed_files) > changed_file_limit:
                lines.append(f"    - ... {len(summary.final_review_changed_files) - changed_file_limit} more")
        lines.extend(format_final_review_failure_lines(summary, indent="  ", max_text=max_text))
    else:
        lines.append("  finalReview: not run")


def append_checkpoint_lines(lines: list[str], summary: SessionSummary, *, max_text: int) -> None:
    if not summary.checkpoints_created:
        return
    checkpoint_line = (
        "  checkpoints: "
        f"created={summary.checkpoints_created}, "
        f"auto={summary.auto_checkpoints_created}"
    )
    if summary.latest_checkpoint_id:
        checkpoint_line += f", latest={compact(summary.latest_checkpoint_id, max_text)}"
    lines.append(checkpoint_line)
    if summary.latest_checkpoint_id:
        lines.append(f"  restoreHint: {CHECKPOINT_RESTORE_HINT}")


def append_completion_lines(lines: list[str], summary: SessionSummary, *, max_text: int) -> None:
    if summary.completion_ready is not None:
        lines.append(f"  completionReady: {'yes' if summary.completion_ready else 'no'}")
    if summary.completion_blockers:
        lines.append("  completionBlockers:")
        lines.extend(f"    - {compact(blocker, max_text)}" for blocker in summary.completion_blockers)
    latest_detail_lines = format_latest_completion_detail_lines(summary, indent="  ", max_text=max_text)
    if summary.completion_blocked_count:
        lines.append(f"  completionBlocked: {summary.completion_blocked_count}")
        if summary.latest_completion_blockers:
            lines.append("  latestCompletionBlockers:")
            lines.extend(f"    - {compact(blocker, max_text)}" for blocker in summary.latest_completion_blockers)
    if latest_detail_lines:
        lines.extend(latest_detail_lines)
    if summary.completion_warnings:
        lines.append("  completionWarnings:")
        lines.extend(f"    - {compact(warning, max_text)}" for warning in summary.completion_warnings)
