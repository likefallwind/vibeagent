from __future__ import annotations

import shlex

from .local_runtime_commands import validate_run_output_context_options
from .project_focused_test_reports import usage_error


def parse_related_tests_argument(argument: str | None) -> list[str] | None:
    if not argument or not argument.strip():
        return None
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if any(part.startswith("-") for part in parts):
        raise ValueError("options are not supported.")
    return parts or None


def validate_run_focused_test_options(
    *,
    usage: str,
    timeout_ms: int,
    max_output_chars: int,
    context_lines: int,
    max_diagnostics: int,
    max_contexts: int,
    max_bytes_per_context: int,
) -> str | None:
    if timeout_ms < 100:
        return usage_error(usage, "timeout_ms must be at least 100.")
    if timeout_ms > 600_000:
        return usage_error(usage, "timeout_ms must be at most 600000.")
    if max_output_chars < 1_000:
        return usage_error(usage, "max_output_chars must be at least 1000.")
    if max_output_chars > 50_000:
        return usage_error(usage, "max_output_chars must be at most 50000.")
    return validate_run_output_context_options(
        context_lines=context_lines,
        max_diagnostics=max_diagnostics,
        max_contexts=max_contexts,
        max_bytes_per_context=max_bytes_per_context,
        usage=usage,
    )


__all__ = ["parse_related_tests_argument", "validate_run_focused_test_options"]
