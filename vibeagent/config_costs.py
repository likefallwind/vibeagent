from __future__ import annotations

import os
from decimal import Decimal, InvalidOperation
from typing import Callable, Mapping, TypeVar

CostRatesT = TypeVar("CostRatesT")


def resolve_cost_rates(
    env: Mapping[str, str | None] | None = None,
    *,
    cost_rates_factory: Callable[..., CostRatesT],
) -> tuple[CostRatesT, list[str]]:
    source = env if env is not None else os.environ
    input_rate, input_error = parse_cost_rate(source.get("VIBEAGENT_INPUT_USD_PER_MILLION"), "VIBEAGENT_INPUT_USD_PER_MILLION")
    output_rate, output_error = parse_cost_rate(source.get("VIBEAGENT_OUTPUT_USD_PER_MILLION"), "VIBEAGENT_OUTPUT_USD_PER_MILLION")
    cache_creation_rate, cache_creation_error = parse_cost_rate(
        source.get("VIBEAGENT_CACHE_CREATION_USD_PER_MILLION"),
        "VIBEAGENT_CACHE_CREATION_USD_PER_MILLION",
    )
    cache_read_rate, cache_read_error = parse_cost_rate(
        source.get("VIBEAGENT_CACHE_READ_USD_PER_MILLION"),
        "VIBEAGENT_CACHE_READ_USD_PER_MILLION",
    )
    errors = [
        error
        for error in (input_error, output_error, cache_creation_error, cache_read_error)
        if error is not None
    ]
    return (
        cost_rates_factory(
            input_usd_per_million=input_rate,
            output_usd_per_million=output_rate,
            cache_creation_usd_per_million=cache_creation_rate,
            cache_read_usd_per_million=cache_read_rate,
        ),
        errors,
    )


def parse_cost_rate(value: str | None, name: str) -> tuple[Decimal | None, str | None]:
    if value is None or not value.strip():
        return None, None
    try:
        parsed = Decimal(value.strip())
    except InvalidOperation:
        return None, f"{name} must be a non-negative decimal."
    if parsed < 0:
        return None, f"{name} must be a non-negative decimal."
    return parsed, None
