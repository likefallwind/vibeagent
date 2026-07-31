from __future__ import annotations

from pathlib import Path

PROCESS_OUTPUT_CONTEXTS_USAGE = "Usage: /process-output-contexts <id> [chars]"
PROCESS_OUTPUT_DIAGNOSTICS_USAGE = "Usage: /process-output-diagnostics <id> [chars]"


def usage_error(usage: str, error: object) -> str:
    return f"{usage}\nError: {error}"


def validate_process_output_context_limits(
    *,
    context_lines: int,
    max_contexts: int,
    max_bytes_per_context: int,
) -> str:
    if context_lines < 0:
        return usage_error(PROCESS_OUTPUT_CONTEXTS_USAGE, "context_lines must be at least 0.")
    if context_lines > 500:
        return usage_error(PROCESS_OUTPUT_CONTEXTS_USAGE, "context_lines must be at most 500.")
    if max_contexts < 1:
        return usage_error(PROCESS_OUTPUT_CONTEXTS_USAGE, "max_contexts must be at least 1.")
    if max_contexts > 100:
        return usage_error(PROCESS_OUTPUT_CONTEXTS_USAGE, "max_contexts must be at most 100.")
    if max_bytes_per_context < 1_000:
        return usage_error(PROCESS_OUTPUT_CONTEXTS_USAGE, "max_bytes_per_context must be at least 1000.")
    if max_bytes_per_context > 200_000:
        return usage_error(PROCESS_OUTPUT_CONTEXTS_USAGE, "max_bytes_per_context must be at most 200000.")
    return ""


def validate_process_output_diagnostic_limits(
    *,
    context_lines: int,
    max_diagnostics: int,
    max_contexts: int,
    max_bytes_per_context: int,
) -> str:
    if context_lines < 0:
        return usage_error(PROCESS_OUTPUT_DIAGNOSTICS_USAGE, "context_lines must be at least 0.")
    if context_lines > 500:
        return usage_error(PROCESS_OUTPUT_DIAGNOSTICS_USAGE, "context_lines must be at most 500.")
    if max_diagnostics < 1:
        return usage_error(PROCESS_OUTPUT_DIAGNOSTICS_USAGE, "max_diagnostics must be at least 1.")
    if max_diagnostics > 200:
        return usage_error(PROCESS_OUTPUT_DIAGNOSTICS_USAGE, "max_diagnostics must be at most 200.")
    if max_contexts < 1:
        return usage_error(PROCESS_OUTPUT_DIAGNOSTICS_USAGE, "max_contexts must be at least 1.")
    if max_contexts > 100:
        return usage_error(PROCESS_OUTPUT_DIAGNOSTICS_USAGE, "max_contexts must be at most 100.")
    if max_bytes_per_context < 1_000:
        return usage_error(PROCESS_OUTPUT_DIAGNOSTICS_USAGE, "max_bytes_per_context must be at least 1000.")
    if max_bytes_per_context > 200_000:
        return usage_error(PROCESS_OUTPUT_DIAGNOSTICS_USAGE, "max_bytes_per_context must be at most 200000.")
    return ""


def process_output_contexts_usage_report(
    root: Path,
    process_id: str,
    max_output_chars: int | None,
    message: str,
) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "processId": process_id,
        "pid": None,
        "status": "unknown",
        "contexts": {"ok": 0, "total": 0, "items": []},
        "totalRefs": 0,
        "maxOutputChars": max_output_chars,
        "stdoutChars": 0,
        "stderrChars": 0,
        "truncated": False,
        "message": message,
    }


def process_output_diagnostics_usage_report(
    root: Path,
    process_id: str,
    max_output_chars: int | None,
    context_lines: int,
    max_diagnostics: int,
    max_contexts: int,
    max_bytes_per_context: int,
    message: str,
) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "processId": process_id,
        "pid": None,
        "status": "unknown",
        "diagnostics": {"shown": 0, "total": 0, "items": []},
        "contexts": {"ok": 0, "total": 0, "items": []},
        "totalRefs": 0,
        "maxOutputChars": max_output_chars,
        "stdoutChars": 0,
        "stderrChars": 0,
        "contextLines": context_lines,
        "maxDiagnostics": max_diagnostics,
        "maxContexts": max_contexts,
        "maxBytesPerContext": max_bytes_per_context,
        "diagnosticsTruncated": False,
        "contextsTruncated": False,
        "message": message,
    }
