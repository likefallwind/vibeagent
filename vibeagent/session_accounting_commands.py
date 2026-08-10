from __future__ import annotations

from pathlib import Path

from .config import resolve_cost_rates
from .session import build_cost_report, build_sessions_report, build_usage_report


def get_sessions_text(project_root: str | Path = ".") -> str:
    return format_sessions_report_text(get_sessions_report(project_root))


def get_sessions_report(project_root: str | Path = ".") -> dict[str, object]:
    return build_sessions_report(project_root)


def format_sessions_report_text(report: dict[str, object]) -> str:
    if not bool(report.get("exists")):
        return str(report.get("message") or "No sessions found.")
    sessions = report.get("sessions") if isinstance(report.get("sessions"), dict) else {}
    items = [item for item in sessions.get("items", []) if isinstance(item, dict)] if isinstance(sessions.get("items"), list) else []
    if not items:
        return str(report.get("message") or "No sessions found.")
    lines = ["Recent sessions:"]
    for item in items:
        malformed = f", {item.get('malformed')} malformed" if int(item.get("malformed", 0) or 0) else ""
        last = item.get("lastEventTime") or "unknown"
        task = f"  task={item.get('task')}" if item.get("task") else ""
        name = f"  name={item.get('name')}" if item.get("name") else ""
        lines.append(
            f"  {item.get('session')}  status={item.get('status')}  "
            f"events={int(item.get('events', 0) or 0)}{malformed}  last={last}{name}{task}"
        )
    return "\n".join(lines)


def get_usage_text(project_root: str | Path = ".") -> str:
    return format_usage_report_text(get_usage_report(project_root))


def get_usage_report(project_root: str | Path = ".") -> dict[str, object]:
    return build_usage_report(project_root)


def format_usage_report_text(report: dict[str, object]) -> str:
    if not bool(report.get("exists")):
        return str(report.get("message") or "No sessions found.")
    usage = report.get("usage") if isinstance(report.get("usage"), dict) else {}
    approvals = usage.get("approvals") if isinstance(usage.get("approvals"), dict) else {}
    statuses = usage.get("statuses") if isinstance(usage.get("statuses"), dict) else {}
    tokens = usage.get("tokens") if isinstance(usage.get("tokens"), dict) else {}
    input_tokens = int(tokens.get("input", 0) or 0)
    output_tokens = int(tokens.get("output", 0) or 0)
    total_tokens = int(tokens.get("total", 0) or 0)
    cache_creation = int(tokens.get("cacheCreation", 0) or 0)
    cache_read = int(tokens.get("cacheRead", 0) or 0)
    lines = [
        "Usage:",
        f"  sessions: {int(usage.get('sessions', 0) or 0)}",
        f"  events: {int(usage.get('events', 0) or 0)}",
        f"  iterations: {int(usage.get('iterations', 0) or 0)}",
        f"  toolCalls: {int(usage.get('toolCalls', 0) or 0)}",
        (
            "  approvals: "
            f"{int(approvals.get('requested', 0) or 0)} requested, "
            f"{int(approvals.get('approved', 0) or 0)} approved, "
            f"{int(approvals.get('denied', 0) or 0)} denied"
        ),
        f"  completed: {int(statuses.get('completed', 0) or 0)}",
        f"  blocked: {int(statuses.get('blocked', 0) or 0)}",
        f"  incomplete: {int(statuses.get('incomplete', 0) or 0)}",
        f"  failed: {int(statuses.get('failed', 0) or 0)}",
    ]
    if input_tokens or output_tokens or total_tokens:
        lines.extend(
            [
                f"  inputTokens: {input_tokens}",
                f"  outputTokens: {output_tokens}",
                f"  totalTokens: {total_tokens}",
            ]
        )
    if cache_creation or cache_read:
        lines.append(f"  cacheTokens: {cache_creation} created, {cache_read} read")
    malformed_rows = int(usage.get("malformedRows", 0) or 0)
    if malformed_rows:
        lines.append(f"  malformedRows: {malformed_rows}")
    cost = report.get("cost") if isinstance(report.get("cost"), dict) else {}
    reason = str(cost.get("reason") or "provider token usage is not recorded")
    lines.append(f"  cost: unavailable; {reason}.")
    return "\n".join(lines)


def get_cost_text(project_root: str | Path = ".", env: dict[str, str | None] | None = None) -> str:
    return format_cost_report_text(get_cost_report(project_root, env))


def get_cost_report(project_root: str | Path = ".", env: dict[str, str | None] | None = None) -> dict[str, object]:
    rates, errors = resolve_cost_rates(env)
    return build_cost_report(project_root, rates, errors)


def format_cost_report_text(report: dict[str, object]) -> str:
    if not bool(report.get("exists")):
        return str(report.get("message") or "No sessions found.")
    usage = report.get("usage") if isinstance(report.get("usage"), dict) else {}
    tokens = usage.get("tokens") if isinstance(usage.get("tokens"), dict) else {}
    input_tokens = int(tokens.get("input", 0) or 0)
    output_tokens = int(tokens.get("output", 0) or 0)
    total_tokens = int(tokens.get("total", 0) or 0)
    cache_creation = int(tokens.get("cacheCreation", 0) or 0)
    cache_read = int(tokens.get("cacheRead", 0) or 0)
    lines = [
        "Cost:",
        f"  sessions: {int(usage.get('sessions', 0) or 0)}",
        f"  inputTokens: {input_tokens}",
        f"  outputTokens: {output_tokens}",
        f"  totalTokens: {total_tokens}",
    ]
    if cache_creation or cache_read:
        lines.append(f"  cacheTokens: {cache_creation} created, {cache_read} read")
    errors = [str(error) for error in report.get("errors", [])] if isinstance(report.get("errors"), list) else []
    if errors:
        lines.extend(f"  error: {error}" for error in errors)
        return "\n".join(lines)
    estimate = report.get("estimate") if isinstance(report.get("estimate"), dict) else {}
    if not bool(estimate.get("available")):
        reason = str(estimate.get("reason") or "provider token usage is not recorded")
        missing = estimate.get("missingRates") if isinstance(estimate.get("missingRates"), list) else []
        if missing:
            lines.append(f"  estimate: unavailable; set {', '.join(str(item) for item in missing)}.")
        else:
            lines.append(f"  estimate: unavailable; {reason}.")
        return "\n".join(lines)
    formatted = estimate.get("formatted") if isinstance(estimate.get("formatted"), dict) else {}
    lines.extend(
        [
            f"  inputCostUsd: {formatted.get('inputCostUsd') or estimate.get('inputCostUsd')}",
            f"  outputCostUsd: {formatted.get('outputCostUsd') or estimate.get('outputCostUsd')}",
        ]
    )
    if cache_creation or cache_read:
        lines.append(f"  cacheCostUsd: {formatted.get('cacheCostUsd') or estimate.get('cacheCostUsd')}")
    lines.append(f"  estimatedCostUsd: {formatted.get('estimatedCostUsd') or estimate.get('estimatedCostUsd')}")
    return "\n".join(lines)
