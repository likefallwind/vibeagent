from __future__ import annotations

import re
from typing import Any

from .action_parsing_helpers import ActionParseError, parse_nonnegative_int, parse_optional_positive_int


def parse_command(value: Any, raw: str, action_type: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ActionParseError(f"{action_type} action requires a non-empty command.", raw)
    return value


def parse_optional_description(value: Any, raw: str, action_type: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ActionParseError(f"{action_type} action description must be a non-empty string when provided.", raw)
    return value.strip()


def parse_process_id(value: Any, raw: str, action_type: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ActionParseError(f"{action_type} action requires a non-empty process_id.", raw)
    return value


def parse_write_process_content(value: dict[str, Any], raw: str, action_type: str) -> tuple[str | None, str | None]:
    content = value.get("content")
    stdin_file = value.get("stdin_file")
    if content is not None and stdin_file is not None:
        raise ActionParseError(f"{action_type} action requires either content or stdin_file, not both.", raw)
    if stdin_file is not None:
        if not isinstance(stdin_file, str) or not stdin_file.strip():
            raise ActionParseError(f"{action_type} action stdin_file must be a non-empty string when provided.", raw)
        return None, stdin_file
    if not isinstance(content, str) or content == "":
        raise ActionParseError(f"{action_type} action requires non-empty content.", raw)
    return content, None


def parse_timeout_ms(value: Any, raw: str) -> int | None:
    timeout_ms = parse_optional_positive_int(value, "timeout_ms", raw, maximum=600_000)
    if timeout_ms is not None and timeout_ms < 100:
        raise ActionParseError("timeout_ms must be at least 100.", raw)
    return timeout_ms


def parse_optional_command_output_chars(value: Any, raw: str) -> int | None:
    max_output_chars = parse_optional_positive_int(value, "max_output_chars", raw, maximum=50_000)
    if max_output_chars is not None and max_output_chars < 1_000:
        raise ActionParseError("max_output_chars must be at least 1000.", raw)
    return max_output_chars


def parse_optional_output_filter(value: Any, raw: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ActionParseError("output_filter must be a non-empty string when provided.", raw)
    pattern = value.strip()
    try:
        re.compile(pattern)
    except re.error as error:
        raise ActionParseError(f"output_filter must be a valid regex: {error}.", raw) from error
    return pattern


def parse_output_context_options(
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
