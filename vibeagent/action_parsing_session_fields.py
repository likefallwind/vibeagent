from __future__ import annotations

from typing import Any

from .action_parsing_helpers import ActionParseError, parse_nonnegative_int, parse_optional_positive_int
from .session_input import normalize_optional_run_id


def parse_run_id(value: Any, raw: str, action_type: str) -> str | None:
    if value is not None and not isinstance(value, str):
        raise ActionParseError(f"{action_type} action run_id must be a string when provided.", raw)
    return normalize_optional_run_id(value)


def parse_min_text(value: Any, raw: str, default: int) -> int:
    max_text = parse_optional_positive_int(value, "max_text", raw, maximum=5000) or default
    if max_text < 80:
        raise ActionParseError("max_text must be at least 80.", raw)
    return max_text


def parse_session_command_limits(
    value: dict[str, Any],
    raw: str,
) -> tuple[int, int]:
    max_commands = parse_optional_positive_int(value.get("max_commands", 20), "max_commands", raw, maximum=100) or 20
    max_output_chars = value.get("max_output_chars", 20_000)
    if not isinstance(max_output_chars, int):
        raise ActionParseError("max_output_chars must be an integer.", raw)
    if max_output_chars < 0:
        raise ActionParseError("max_output_chars must be at least 0.", raw)
    if max_output_chars > 20_000:
        raise ActionParseError("max_output_chars must be at most 20000.", raw)
    return max_commands, max_output_chars


def parse_output_context_limits(
    value: dict[str, Any],
    raw: str,
    default_context_lines: int,
) -> tuple[int, int, int]:
    context_lines = parse_nonnegative_int(value.get("context_lines", default_context_lines), "context_lines", raw, maximum=500)
    max_contexts = parse_optional_positive_int(value.get("max_contexts", 20), "max_contexts", raw, maximum=100) or 20
    max_bytes_per_context = parse_optional_positive_int(
        value.get("max_bytes_per_context", 20_000),
        "max_bytes_per_context",
        raw,
        maximum=200_000,
    ) or 20_000
    if max_bytes_per_context < 1000:
        raise ActionParseError("max_bytes_per_context must be at least 1000.", raw)
    return context_lines, max_contexts, max_bytes_per_context
