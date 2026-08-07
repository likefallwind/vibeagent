from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import CostRates
from .session_costs import (
    build_cost_report_from_summary as _build_cost_report_from_summary,
    decimal_rate_string,
    decimal_usd_string,
    format_cost_from_summary,
    format_usd,
    missing_cost_rate_names,
    serialize_cost_rates,
    token_cost,
    usage_has_tokens,
)


@dataclass(frozen=True)
class SessionUsageSummary:
    sessions: int
    events: int
    malformed_rows: int
    iterations: int
    tool_calls: int
    approvals_requested: int
    approvals_approved: int
    approvals_denied: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    completed: int
    blocked: int
    incomplete: int
    failed: int

def _session_summaries(project_root: str | Path, limit: int) -> list[object]:
    from .session import list_sessions, summarize_session

    return [summarize_session(project_root, info.run_id) for info in list_sessions(project_root, limit=limit)]


def summarize_usage(project_root: str | Path, limit: int = 20) -> SessionUsageSummary:
    summaries = _session_summaries(project_root, limit)
    return summarize_usage_from_session_summaries(summaries)

def summarize_run_usage(project_root: str | Path, run_id: str) -> SessionUsageSummary:
    from .session import summarize_session

    summary = summarize_session(project_root, run_id)
    if not summary.exists:
        return summarize_usage_from_session_summaries([])
    return summarize_usage_from_session_summaries([summary])

def summarize_usage_from_session_summaries(summaries: list[object]) -> SessionUsageSummary:
    return SessionUsageSummary(
        sessions=len(summaries),
        events=sum(summary.event_count for summary in summaries),
        malformed_rows=sum(summary.malformed_count for summary in summaries),
        iterations=sum(summary.iterations for summary in summaries),
        tool_calls=sum(len(summary.tool_calls) for summary in summaries),
        approvals_requested=sum(summary.approvals_requested for summary in summaries),
        approvals_approved=sum(summary.approvals_approved for summary in summaries),
        approvals_denied=sum(summary.approvals_denied for summary in summaries),
        input_tokens=sum(summary.input_tokens for summary in summaries),
        output_tokens=sum(summary.output_tokens for summary in summaries),
        total_tokens=sum(summary.total_tokens for summary in summaries),
        cache_creation_tokens=sum(summary.cache_creation_tokens for summary in summaries),
        cache_read_tokens=sum(summary.cache_read_tokens for summary in summaries),
        completed=sum(1 for summary in summaries if summary.completed),
        blocked=sum(1 for summary in summaries if summary.blocked),
        incomplete=sum(1 for summary in summaries if not summary.completed and not summary.failed and not summary.blocked),
        failed=sum(1 for summary in summaries if summary.failed),
    )

def format_usage(project_root: str | Path, limit: int = 20) -> str:
    usage = summarize_usage(project_root, limit=limit)
    if usage.sessions == 0:
        return "No sessions found."
    lines = [
        "Usage:",
        f"  sessions: {usage.sessions}",
        f"  events: {usage.events}",
        f"  iterations: {usage.iterations}",
        f"  toolCalls: {usage.tool_calls}",
        (
            "  approvals: "
            f"{usage.approvals_requested} requested, "
            f"{usage.approvals_approved} approved, "
            f"{usage.approvals_denied} denied"
        ),
        f"  completed: {usage.completed}",
        f"  blocked: {usage.blocked}",
        f"  incomplete: {usage.incomplete}",
        f"  failed: {usage.failed}",
    ]
    if usage.total_tokens or usage.input_tokens or usage.output_tokens:
        lines.extend(
            [
                f"  inputTokens: {usage.input_tokens}",
                f"  outputTokens: {usage.output_tokens}",
                f"  totalTokens: {usage.total_tokens}",
            ]
        )
    if usage.cache_creation_tokens or usage.cache_read_tokens:
        lines.append(
            f"  cacheTokens: {usage.cache_creation_tokens} created, {usage.cache_read_tokens} read"
        )
    if usage.malformed_rows:
        lines.append(f"  malformedRows: {usage.malformed_rows}")
    if usage.total_tokens or usage.input_tokens or usage.output_tokens:
        lines.append("  cost: unavailable; provider pricing is not configured.")
    else:
        lines.append("  cost: unavailable; provider token usage is not recorded.")
    return "\n".join(lines)

def build_usage_report(project_root: str | Path, limit: int = 20) -> dict[str, Any]:
    usage = summarize_usage(project_root, limit=limit)
    return build_usage_report_from_summary(usage, missing_message="No sessions found.")

def build_run_usage_report(project_root: str | Path, run_id: str) -> dict[str, Any]:
    usage = summarize_run_usage(project_root, run_id)
    return build_usage_report_from_summary(usage, missing_message=f"No session found for {run_id}.")

def build_usage_report_from_summary(usage: SessionUsageSummary, missing_message: str) -> dict[str, Any]:
    if usage.sessions == 0:
        return {
            "exists": False,
            "ok": False,
            "status": "missing",
            "message": missing_message,
        }
    return {
        "exists": True,
        "ok": True,
        "status": "ready",
        "usage": serialize_usage_summary(usage),
        "cost": {
            "available": False,
            "reason": "provider pricing is not configured" if usage_has_tokens(usage) else "provider token usage is not recorded",
        },
        "message": f"Summarized usage across {usage.sessions} session(s).",
    }

def serialize_usage_summary(usage: SessionUsageSummary) -> dict[str, Any]:
    return {
        "sessions": usage.sessions,
        "events": usage.events,
        "malformedRows": usage.malformed_rows,
        "iterations": usage.iterations,
        "toolCalls": usage.tool_calls,
        "approvals": {
            "requested": usage.approvals_requested,
            "approved": usage.approvals_approved,
            "denied": usage.approvals_denied,
        },
        "statuses": {
            "completed": usage.completed,
            "blocked": usage.blocked,
            "incomplete": usage.incomplete,
            "failed": usage.failed,
        },
        "tokens": {
            "input": usage.input_tokens,
            "output": usage.output_tokens,
            "total": usage.total_tokens,
            "cacheCreation": usage.cache_creation_tokens,
            "cacheRead": usage.cache_read_tokens,
        },
    }

def format_cost(
    project_root: str | Path,
    rates: CostRates,
    rate_errors: list[str] | None = None,
    limit: int = 20,
) -> str:
    usage = summarize_usage(project_root, limit=limit)
    return format_cost_from_summary(usage, rates, rate_errors)

def build_cost_report(
    project_root: str | Path,
    rates: CostRates,
    rate_errors: list[str] | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    usage = summarize_usage(project_root, limit=limit)
    return build_cost_report_from_summary(usage, rates, rate_errors, missing_message="No sessions found.")

def build_run_cost_report(
    project_root: str | Path,
    run_id: str,
    rates: CostRates,
    rate_errors: list[str] | None = None,
) -> dict[str, Any]:
    usage = summarize_run_usage(project_root, run_id)
    return build_cost_report_from_summary(usage, rates, rate_errors, missing_message=f"No session found for {run_id}.")

def build_cost_report_from_summary(
    usage: SessionUsageSummary,
    rates: CostRates,
    rate_errors: list[str] | None,
    missing_message: str,
) -> dict[str, Any]:
    return _build_cost_report_from_summary(
        usage,
        rates,
        rate_errors,
        missing_message,
        serialize_usage_summary,
    )
