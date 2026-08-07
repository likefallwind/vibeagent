from __future__ import annotations

from typing import Any

from .action_parsing_helpers import ActionParseError, parse_nonnegative_int, parse_optional_positive_int


def parse_optional_paths(value: Any, raw: str, action_type: str) -> list[str] | None:
    if value is None:
        return None
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ActionParseError(f"{action_type} action paths must be a list of non-empty strings when provided.", raw)
    return [item.strip() for item in value]


def parse_output_extraction_options(
    value: dict[str, Any],
    raw: str,
    action_type: str,
) -> tuple[bool, bool, int, int, int]:
    extract_output_contexts = value.get("extract_output_contexts", False)
    if not isinstance(extract_output_contexts, bool):
        raise ActionParseError(f"{action_type} action extract_output_contexts must be a boolean.", raw)
    extract_output_diagnostics = value.get("extract_output_diagnostics", False)
    if not isinstance(extract_output_diagnostics, bool):
        raise ActionParseError(f"{action_type} action extract_output_diagnostics must be a boolean.", raw)
    context_lines = parse_nonnegative_int(value.get("context_lines", 5), "context_lines", raw, maximum=500)
    max_diagnostics = parse_optional_positive_int(value.get("max_diagnostics", 50), "max_diagnostics", raw, maximum=200) or 50
    max_contexts = parse_optional_positive_int(value.get("max_contexts", 20), "max_contexts", raw, maximum=100) or 20
    return extract_output_contexts, extract_output_diagnostics, context_lines, max_diagnostics, max_contexts


def parse_run_limits(value: dict[str, Any], raw: str, action_type: str) -> tuple[int | None, int | None, bool]:
    timeout_ms = parse_optional_positive_int(value.get("timeout_ms"), "timeout_ms", raw, maximum=600_000)
    if timeout_ms is not None and timeout_ms < 100:
        raise ActionParseError("timeout_ms must be at least 100.", raw)
    max_output_chars = parse_optional_positive_int(value.get("max_output_chars"), "max_output_chars", raw, maximum=50_000)
    if max_output_chars is not None and max_output_chars < 1_000:
        raise ActionParseError("max_output_chars must be at least 1000.", raw)
    stop_on_failure = value.get("stop_on_failure", True)
    if not isinstance(stop_on_failure, bool):
        raise ActionParseError(f"{action_type} action stop_on_failure must be a boolean when provided.", raw)
    return timeout_ms, max_output_chars, stop_on_failure


def parse_max_bytes_per_context(value: dict[str, Any], raw: str) -> int:
    max_bytes_per_context = parse_optional_positive_int(
        value.get("max_bytes_per_context", 20_000),
        "max_bytes_per_context",
        raw,
        maximum=200_000,
    ) or 20_000
    if max_bytes_per_context < 1_000:
        raise ActionParseError("max_bytes_per_context must be at least 1000.", raw)
    return max_bytes_per_context
