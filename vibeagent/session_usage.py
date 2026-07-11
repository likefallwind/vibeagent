from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from .config import CostRates


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

def usage_has_tokens(usage: SessionUsageSummary) -> bool:
    return bool(
        usage.input_tokens
        or usage.output_tokens
        or usage.total_tokens
        or usage.cache_creation_tokens
        or usage.cache_read_tokens
    )

def format_cost(
    project_root: str | Path,
    rates: CostRates,
    rate_errors: list[str] | None = None,
    limit: int = 20,
) -> str:
    usage = summarize_usage(project_root, limit=limit)
    if usage.sessions == 0:
        return "No sessions found."
    lines = [
        "Cost:",
        f"  sessions: {usage.sessions}",
        f"  inputTokens: {usage.input_tokens}",
        f"  outputTokens: {usage.output_tokens}",
        f"  totalTokens: {usage.total_tokens}",
    ]
    if usage.cache_creation_tokens or usage.cache_read_tokens:
        lines.append(
            f"  cacheTokens: {usage.cache_creation_tokens} created, {usage.cache_read_tokens} read"
        )
    if rate_errors:
        lines.extend(f"  error: {error}" for error in rate_errors)
        return "\n".join(lines)
    if not (usage.input_tokens or usage.output_tokens or usage.total_tokens):
        lines.append("  estimate: unavailable; provider token usage is not recorded.")
        return "\n".join(lines)
    missing = missing_cost_rate_names(usage, rates)
    if missing:
        lines.append(f"  estimate: unavailable; set {', '.join(missing)}.")
        return "\n".join(lines)

    input_cost = token_cost(usage.input_tokens, rates.input_usd_per_million)
    output_cost = token_cost(usage.output_tokens, rates.output_usd_per_million)
    cache_creation_cost = token_cost(usage.cache_creation_tokens, rates.cache_creation_usd_per_million)
    cache_read_cost = token_cost(usage.cache_read_tokens, rates.cache_read_usd_per_million)
    total_cost = input_cost + output_cost + cache_creation_cost + cache_read_cost
    lines.extend(
        [
            f"  inputCostUsd: {format_usd(input_cost)}",
            f"  outputCostUsd: {format_usd(output_cost)}",
        ]
    )
    if usage.cache_creation_tokens or usage.cache_read_tokens:
        lines.append(
            f"  cacheCostUsd: {format_usd(cache_creation_cost + cache_read_cost)}"
        )
    lines.append(f"  estimatedCostUsd: {format_usd(total_cost)}")
    return "\n".join(lines)

def build_cost_report(
    project_root: str | Path,
    rates: CostRates,
    rate_errors: list[str] | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    usage = summarize_usage(project_root, limit=limit)
    if usage.sessions == 0:
        return {
            "exists": False,
            "ok": False,
            "status": "missing",
            "message": "No sessions found.",
        }

    errors = list(rate_errors or [])
    report: dict[str, Any] = {
        "exists": True,
        "ok": not errors,
        "status": "invalid" if errors else "ready",
        "usage": serialize_usage_summary(usage),
        "rates": serialize_cost_rates(rates),
        "errors": errors,
    }
    if errors:
        report["estimate"] = {
            "available": False,
            "reason": "invalid rate configuration",
            "missingRates": [],
        }
        report["message"] = "Cost estimate unavailable because rate configuration is invalid."
        return report

    if not usage_has_tokens(usage):
        report["estimate"] = {
            "available": False,
            "reason": "provider token usage is not recorded",
            "missingRates": [],
        }
        report["message"] = "Cost estimate unavailable because provider token usage is not recorded."
        return report

    missing = missing_cost_rate_names(usage, rates)
    if missing:
        report["estimate"] = {
            "available": False,
            "reason": "required cost rates are not configured",
            "missingRates": missing,
        }
        report["message"] = "Cost estimate unavailable because required cost rates are not configured."
        return report

    input_cost = token_cost(usage.input_tokens, rates.input_usd_per_million)
    output_cost = token_cost(usage.output_tokens, rates.output_usd_per_million)
    cache_creation_cost = token_cost(usage.cache_creation_tokens, rates.cache_creation_usd_per_million)
    cache_read_cost = token_cost(usage.cache_read_tokens, rates.cache_read_usd_per_million)
    cache_cost = cache_creation_cost + cache_read_cost
    total_cost = input_cost + output_cost + cache_cost
    report["estimate"] = {
        "available": True,
        "reason": None,
        "missingRates": [],
        "inputCostUsd": decimal_usd_string(input_cost),
        "outputCostUsd": decimal_usd_string(output_cost),
        "cacheCostUsd": decimal_usd_string(cache_cost),
        "estimatedCostUsd": decimal_usd_string(total_cost),
        "formatted": {
            "inputCostUsd": format_usd(input_cost),
            "outputCostUsd": format_usd(output_cost),
            "cacheCostUsd": format_usd(cache_cost),
            "estimatedCostUsd": format_usd(total_cost),
        },
    }
    report["message"] = "Estimated provider cost from configured rates."
    return report

def serialize_cost_rates(rates: CostRates) -> dict[str, str | None]:
    return {
        "inputUsdPerMillion": decimal_rate_string(rates.input_usd_per_million),
        "outputUsdPerMillion": decimal_rate_string(rates.output_usd_per_million),
        "cacheCreationUsdPerMillion": decimal_rate_string(rates.cache_creation_usd_per_million),
        "cacheReadUsdPerMillion": decimal_rate_string(rates.cache_read_usd_per_million),
    }

def decimal_rate_string(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None

def decimal_usd_string(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.000001")))

def missing_cost_rate_names(usage: SessionUsageSummary, rates: CostRates) -> list[str]:
    missing: list[str] = []
    if usage.input_tokens and rates.input_usd_per_million is None:
        missing.append("VIBEAGENT_INPUT_USD_PER_MILLION")
    if usage.output_tokens and rates.output_usd_per_million is None:
        missing.append("VIBEAGENT_OUTPUT_USD_PER_MILLION")
    if usage.cache_creation_tokens and rates.cache_creation_usd_per_million is None:
        missing.append("VIBEAGENT_CACHE_CREATION_USD_PER_MILLION")
    if usage.cache_read_tokens and rates.cache_read_usd_per_million is None:
        missing.append("VIBEAGENT_CACHE_READ_USD_PER_MILLION")
    return missing

def token_cost(tokens: int, usd_per_million: Decimal | None) -> Decimal:
    if not tokens or usd_per_million is None:
        return Decimal("0")
    return (Decimal(tokens) * usd_per_million) / Decimal(1_000_000)

def format_usd(value: Decimal) -> str:
    return f"${value.quantize(Decimal('0.000001'))}"
