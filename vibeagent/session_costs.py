from __future__ import annotations

from decimal import Decimal
from typing import Any, Callable, Protocol

from .config import CostRates


class CostUsage(Protocol):
    sessions: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int


def format_cost_from_summary(
    usage: CostUsage,
    rates: CostRates,
    rate_errors: list[str] | None = None,
) -> str:
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

    estimate = estimate_token_costs(usage, rates)
    lines.extend(
        [
            f"  inputCostUsd: {format_usd(estimate['input_cost'])}",
            f"  outputCostUsd: {format_usd(estimate['output_cost'])}",
        ]
    )
    if usage.cache_creation_tokens or usage.cache_read_tokens:
        lines.append(f"  cacheCostUsd: {format_usd(estimate['cache_cost'])}")
    lines.append(f"  estimatedCostUsd: {format_usd(estimate['total_cost'])}")
    return "\n".join(lines)


def build_cost_report_from_summary(
    usage: CostUsage,
    rates: CostRates,
    rate_errors: list[str] | None,
    missing_message: str,
    usage_serializer: Callable[[CostUsage], dict[str, Any]],
) -> dict[str, Any]:
    if usage.sessions == 0:
        return {
            "exists": False,
            "ok": False,
            "status": "missing",
            "message": missing_message,
        }

    errors = list(rate_errors or [])
    report: dict[str, Any] = {
        "exists": True,
        "ok": not errors,
        "status": "invalid" if errors else "ready",
        "usage": usage_serializer(usage),
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

    estimate = estimate_token_costs(usage, rates)
    report["estimate"] = {
        "available": True,
        "reason": None,
        "missingRates": [],
        "inputCostUsd": decimal_usd_string(estimate["input_cost"]),
        "outputCostUsd": decimal_usd_string(estimate["output_cost"]),
        "cacheCostUsd": decimal_usd_string(estimate["cache_cost"]),
        "estimatedCostUsd": decimal_usd_string(estimate["total_cost"]),
        "formatted": {
            "inputCostUsd": format_usd(estimate["input_cost"]),
            "outputCostUsd": format_usd(estimate["output_cost"]),
            "cacheCostUsd": format_usd(estimate["cache_cost"]),
            "estimatedCostUsd": format_usd(estimate["total_cost"]),
        },
    }
    report["message"] = "Estimated provider cost from configured rates."
    return report


def estimate_token_costs(usage: CostUsage, rates: CostRates) -> dict[str, Decimal]:
    input_cost = token_cost(usage.input_tokens, rates.input_usd_per_million)
    output_cost = token_cost(usage.output_tokens, rates.output_usd_per_million)
    cache_creation_cost = token_cost(usage.cache_creation_tokens, rates.cache_creation_usd_per_million)
    cache_read_cost = token_cost(usage.cache_read_tokens, rates.cache_read_usd_per_million)
    cache_cost = cache_creation_cost + cache_read_cost
    return {
        "input_cost": input_cost,
        "output_cost": output_cost,
        "cache_creation_cost": cache_creation_cost,
        "cache_read_cost": cache_read_cost,
        "cache_cost": cache_cost,
        "total_cost": input_cost + output_cost + cache_cost,
    }


def usage_has_tokens(usage: CostUsage) -> bool:
    return bool(
        usage.input_tokens
        or usage.output_tokens
        or usage.total_tokens
        or usage.cache_creation_tokens
        or usage.cache_read_tokens
    )


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


def missing_cost_rate_names(usage: CostUsage, rates: CostRates) -> list[str]:
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
