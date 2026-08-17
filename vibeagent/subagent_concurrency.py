from __future__ import annotations

from collections.abc import Mapping
import os


DEFAULT_MAX_CONCURRENT_SUBAGENTS = 20
MAX_CONFIGURED_CONCURRENT_SUBAGENTS = 100
_ENVIRONMENT_NAMES = (
    "VIBEAGENT_MAX_CONCURRENT_SUBAGENTS",
    "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS",
)


def resolve_max_concurrent_subagents(
    environment: Mapping[str, str] | None = None,
) -> int:
    values = os.environ if environment is None else environment
    for name in _ENVIRONMENT_NAMES:
        raw = values.get(name, "").strip()
        if not raw:
            continue
        try:
            limit = int(raw)
        except ValueError as error:
            raise ValueError(f"{name} must be an integer.") from error
        if not 1 <= limit <= MAX_CONFIGURED_CONCURRENT_SUBAGENTS:
            raise ValueError(
                f"{name} must be between 1 and "
                f"{MAX_CONFIGURED_CONCURRENT_SUBAGENTS}."
            )
        return limit
    return DEFAULT_MAX_CONCURRENT_SUBAGENTS


__all__ = [
    "DEFAULT_MAX_CONCURRENT_SUBAGENTS",
    "MAX_CONFIGURED_CONCURRENT_SUBAGENTS",
    "resolve_max_concurrent_subagents",
]
