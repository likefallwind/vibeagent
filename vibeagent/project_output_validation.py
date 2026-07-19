from __future__ import annotations


def usage_error(usage: str, error: object) -> str:
    return f"{usage}\nError: {error}"


def validate_output_context_options(
    usage: str,
    *,
    text: str | None,
    context_lines: int,
    max_contexts: int,
    max_bytes_per_context: int,
) -> str | None:
    if text is not None and len(text) > 200_000:
        return usage_error(usage, "text must be at most 200000 characters.")
    if context_lines < 0:
        return usage_error(usage, "context_lines must be at least 0.")
    if context_lines > 500:
        return usage_error(usage, "context_lines must be at most 500.")
    if max_contexts < 1:
        return usage_error(usage, "max_contexts must be at least 1.")
    if max_contexts > 100:
        return usage_error(usage, "max_contexts must be at most 100.")
    if max_bytes_per_context < 1_000:
        return usage_error(usage, "max_bytes_per_context must be at least 1000.")
    if max_bytes_per_context > 200_000:
        return usage_error(usage, "max_bytes_per_context must be at most 200000.")
    return None


def validate_output_diagnostic_options(
    usage: str,
    *,
    text: str | None,
    context_lines: int,
    max_diagnostics: int,
    max_contexts: int,
    max_bytes_per_context: int,
) -> str | None:
    if text is not None and len(text) > 200_000:
        return usage_error(usage, "text must be at most 200000 characters.")
    if context_lines < 0:
        return usage_error(usage, "context_lines must be at least 0.")
    if context_lines > 500:
        return usage_error(usage, "context_lines must be at most 500.")
    if max_diagnostics < 1:
        return usage_error(usage, "max_diagnostics must be at least 1.")
    if max_diagnostics > 200:
        return usage_error(usage, "max_diagnostics must be at most 200.")
    if max_contexts < 1:
        return usage_error(usage, "max_contexts must be at least 1.")
    if max_contexts > 100:
        return usage_error(usage, "max_contexts must be at most 100.")
    if max_bytes_per_context < 1_000:
        return usage_error(usage, "max_bytes_per_context must be at least 1000.")
    if max_bytes_per_context > 200_000:
        return usage_error(usage, "max_bytes_per_context must be at most 200000.")
    return None
