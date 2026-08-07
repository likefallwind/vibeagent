from __future__ import annotations

from typing import Any

from .action_parsing_helpers import ActionParseError, parse_nonnegative_int, parse_optional_positive_int
from .types import OutputContextsAction, OutputDiagnosticsAction


READ_OUTPUT_ACTION_TYPES = {"output_contexts", "output_diagnostics", "python_traceback"}


def parse_read_output_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type == "output_contexts":
        text = value.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ActionParseError("output_contexts action requires non-empty text.", raw)
        if len(text) > 200_000:
            raise ActionParseError("output_contexts text must be at most 200000 characters.", raw)
        context_lines = parse_nonnegative_int(value.get("context_lines", 5), "context_lines", raw, maximum=500)
        parse_optional_positive_int(value.get("max_diagnostics", 50), "max_diagnostics", raw, maximum=200)
        max_contexts = parse_optional_positive_int(value.get("max_contexts", 20), "max_contexts", raw, maximum=100) or 20
        max_bytes_per_context = parse_optional_positive_int(
            value.get("max_bytes_per_context", 20_000),
            "max_bytes_per_context",
            raw,
            maximum=200_000,
        ) or 20_000
        if max_bytes_per_context < 1000:
            raise ActionParseError("max_bytes_per_context must be at least 1000.", raw)
        return OutputContextsAction(
            type="output_contexts",
            text=text,
            context_lines=context_lines,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        )

    if action_type in {"output_diagnostics", "python_traceback"}:
        label = "python_traceback" if action_type == "python_traceback" else "output_diagnostics"
        text = value.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ActionParseError(f"{label} action requires non-empty text.", raw)
        if len(text) > 200_000:
            raise ActionParseError(f"{label} text must be at most 200000 characters.", raw)
        context_lines = parse_nonnegative_int(value.get("context_lines", 2), "context_lines", raw, maximum=500)
        max_diagnostics = parse_optional_positive_int(value.get("max_diagnostics", 50), "max_diagnostics", raw, maximum=200) or 50
        max_contexts = parse_optional_positive_int(value.get("max_contexts", 20), "max_contexts", raw, maximum=100) or 20
        max_bytes_per_context = parse_optional_positive_int(
            value.get("max_bytes_per_context", 20_000),
            "max_bytes_per_context",
            raw,
            maximum=200_000,
        ) or 20_000
        if max_bytes_per_context < 1000:
            raise ActionParseError("max_bytes_per_context must be at least 1000.", raw)
        return OutputDiagnosticsAction(
            type="output_diagnostics",
            text=text,
            context_lines=context_lines,
            max_diagnostics=max_diagnostics,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        )

    return None
