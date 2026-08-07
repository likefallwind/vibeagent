from __future__ import annotations

from typing import Any


def validate_positive_int(value: Any, key: str) -> int:
    parsed = parse_int_config(value, key)
    if parsed <= 0:
        raise ValueError(f".vibeagent/config.json {key} must be a positive integer.")
    return parsed


def validate_nonnegative_int(value: Any, key: str) -> int:
    parsed = parse_int_config(value, key)
    if parsed < 0:
        raise ValueError(f".vibeagent/config.json {key} must be a non-negative integer.")
    return parsed


def validate_timeout_ms(value: Any, key: str) -> int:
    parsed = validate_positive_int(value, key)
    if parsed < 100:
        raise ValueError(f".vibeagent/config.json {key} must be at least 100.")
    return parsed


def parse_int_config(value: Any, key: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f".vibeagent/config.json {key} must be an integer.")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return int(value.strip())
        except ValueError as error:
            raise ValueError(f".vibeagent/config.json {key} must be an integer.") from error
    raise ValueError(f".vibeagent/config.json {key} must be an integer.")
