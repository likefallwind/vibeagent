from __future__ import annotations

from datetime import datetime
from typing import Any

from .session_summary_report_builders import (
    CHECKPOINT_RESTORE_HINT,
    build_session_plan_report,
    build_session_summary_report,
    serialize_session_process,
    session_plan_status,
    session_summary_status,
)
from .session_summary_completion_reports import (
    final_review_ready_label,
    final_review_resolution_suffix,
    final_review_resolved_by_completion,
    format_final_review_failure_lines,
    format_latest_completion_detail_lines,
)
from .session_types import SessionSummary
from .session_utils import compact, count_names


def format_session_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


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
    if summary.subagents_started or summary.subagent_context_compacted_count:
        lines.append(
            "  subagents: "
            f"started={summary.subagents_started}, "
            f"completed={summary.subagents_completed}, "
            f"failed={summary.subagents_failed}, "
            f"toolCalls={len(summary.subagent_tool_calls)}, "
            f"contextCompacted={summary.subagent_context_compacted_count}"
        )
    if summary.latest_subagent_failures:
        lines.append("  latestSubagentFailures:")
        lines.extend(f"    - {compact(failure, 160)}" for failure in summary.latest_subagent_failures[:20])
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
        ready = final_review_ready_label(summary.final_review_ready)
        final_review = (
            f"  finalReview: ready={ready}, "
            f"blocking={summary.final_review_blocking_issues}, "
            f"warnings={summary.final_review_warnings}, "
            f"files={summary.final_review_files}, "
            f"suggestedChecks={summary.final_review_suggested_checks}"
            f"{final_review_resolution_suffix(summary)}"
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
    latest_detail_lines = format_latest_completion_detail_lines(summary, indent="  ", max_text=160)
    if summary.completion_blocked_count:
        lines.append(f"  completionBlocked: {summary.completion_blocked_count}")
        if summary.latest_completion_blockers:
            lines.append("  latestCompletionBlockers:")
            lines.extend(f"    - {compact(blocker, 160)}" for blocker in summary.latest_completion_blockers)
    if latest_detail_lines:
        lines.extend(latest_detail_lines)
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
        lines.extend(f"    - {format_session_plan_item(item)}" for item in summary.latest_plan)
    else:
        lines.append("  items: none")
    return "\n".join(lines)


def format_session_plan_item(item: Any) -> str:
    text = f"{item.status}: {compact(item.step, 200)}"
    active_form = getattr(item, "active_form", None)
    if isinstance(active_form, str) and active_form.strip():
        text += f" (activeForm: {compact(active_form, 120)})"
    return text
