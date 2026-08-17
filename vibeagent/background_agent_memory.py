from __future__ import annotations

from typing import Mapping

from .tool_memory_limit import (
    MAX_TOOL_MEMORY_LIMIT_BYTES,
    TOOL_MEMORY_LIMIT_ENV,
    ToolMemoryLimitError,
    parse_tool_memory_limit,
)


BACKGROUND_AGENT_MEMORY_LIMIT_ENV = "VIBEAGENT_BACKGROUND_AGENT_MEMORY_LIMIT"


def resolve_background_agent_memory_limit(
    cli_value: str | None,
    environment: Mapping[str, str],
) -> int | None:
    raw = cli_value
    if raw is None:
        raw = environment.get(BACKGROUND_AGENT_MEMORY_LIMIT_ENV)
    if raw is None:
        return None
    value = raw.strip()
    if value.lower() in {"0", "off", "none", "unlimited"}:
        return None
    try:
        return parse_tool_memory_limit({TOOL_MEMORY_LIMIT_ENV: value})
    except ToolMemoryLimitError as error:
        message = str(error).replace(TOOL_MEMORY_LIMIT_ENV, BACKGROUND_AGENT_MEMORY_LIMIT_ENV)
        raise ToolMemoryLimitError(message) from error


def validate_background_agent_memory_limit_bytes(value: int | None) -> int | None:
    if value is None:
        return None
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value <= 0
        or value > MAX_TOOL_MEMORY_LIMIT_BYTES
    ):
        raise ValueError("Background agent memory limit is invalid.")
    return value


__all__ = [
    "BACKGROUND_AGENT_MEMORY_LIMIT_ENV",
    "resolve_background_agent_memory_limit",
    "validate_background_agent_memory_limit_bytes",
]
