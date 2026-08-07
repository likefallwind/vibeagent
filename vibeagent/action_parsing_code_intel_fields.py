from __future__ import annotations

from typing import Any

from .action_parsing_helpers import ActionParseError, parse_nonnegative_int, parse_optional_positive_int


def parse_optional_path(value: Any, raw: str, action_type: str) -> str | None:
    if value is not None and not isinstance(value, str):
        raise ActionParseError(f"{action_type} action path must be a string when provided.", raw)
    return value


def parse_required_symbol(value: Any, raw: str, action_type: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ActionParseError(f"{action_type} action requires a non-empty symbol.", raw)
    return value.strip()


def parse_dependency_limits(value: dict[str, Any], raw: str) -> tuple[int, int]:
    max_files = parse_optional_positive_int(value.get("max_files", 100), "max_files", raw, maximum=500) or 100
    max_imports = parse_optional_positive_int(value.get("max_imports", 500), "max_imports", raw, maximum=2000) or 500
    return max_files, max_imports


def parse_reference_context_limits(value: dict[str, Any], raw: str) -> tuple[int, int, int]:
    max_matches = parse_optional_positive_int(value.get("max_matches", 50), "max_matches", raw, maximum=100) or 50
    context_lines = parse_nonnegative_int(value.get("context_lines", 3), "context_lines", raw, maximum=50)
    max_bytes_per_context = parse_optional_positive_int(
        value.get("max_bytes_per_context", 20_000),
        "max_bytes_per_context",
        raw,
        maximum=200_000,
    ) or 20_000
    if max_bytes_per_context < 1000:
        raise ActionParseError("max_bytes_per_context must be at least 1000.", raw)
    return max_matches, context_lines, max_bytes_per_context
