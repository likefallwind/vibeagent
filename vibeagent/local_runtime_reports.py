from __future__ import annotations

from .prompt_next_action_runtime_formatting import inline_output_issue_labels
from .local_runtime_report_formatting import (
    format_check_run_sequence_report_text,
    format_check_start_report_text,
    format_command_check_report_text,
    format_command_output_context_lines,
    format_command_output_diagnostic_lines,
    format_run_report_text,
    format_run_sequence_report_text,
    format_start_report_text,
    indent_block,
)
from .process_report_helpers import format_structured_command_output_analysis_lines, serialize_command_output_analysis


def empty_command_output_analysis() -> dict[str, object]:
    return {
        "diagnostics": {"shown": 0, "total": 0, "items": []},
        "diagnosticsTruncated": False,
        "contexts": {"shown": 0, "totalRefs": 0, "items": []},
        "contextsTruncated": False,
    }


def sum_command_result_duration_ms(results: list[object]) -> int:
    total = 0
    for result in results:
        duration = getattr(result, "duration_ms", 0)
        try:
            total += max(0, int(duration or 0))
        except (TypeError, ValueError):
            continue
    return total


def command_results_clean(results: list[object]) -> bool:
    return bool(results) and all(
        getattr(result, "exit_code", None) == 0
        and not bool(getattr(result, "timed_out", False))
        and not inline_output_issue_labels(result)
        for result in results
    )


def serialize_command_result(result: object, index: int | None = None) -> dict[str, object]:
    exit_code = getattr(result, "exit_code", None)
    timed_out = bool(getattr(result, "timed_out", False))
    ok = exit_code == 0 and not timed_out
    clean = ok and not inline_output_issue_labels(result)
    item: dict[str, object] = {
        "command": str(getattr(result, "command", "") or ""),
        "cwd": str(getattr(result, "cwd", ".") or "."),
        "ok": ok,
        "clean": clean,
        "exitCode": exit_code,
        "timedOut": timed_out,
        "signal": getattr(result, "signal", None),
        "timeoutMs": int(getattr(result, "timeout_ms", 0) or 0),
        "durationMs": int(getattr(result, "duration_ms", 0) or 0),
        "sandboxed": bool(getattr(result, "sandboxed", False)),
        "sandboxWarning": getattr(result, "sandbox_warning", None),
        "maxOutputChars": int(getattr(result, "max_output_chars", 0) or 0),
        "stdout": str(getattr(result, "stdout", "") or ""),
        "stderr": str(getattr(result, "stderr", "") or ""),
        "stdoutTruncated": bool(getattr(result, "stdout_truncated", False)),
        "stderrTruncated": bool(getattr(result, "stderr_truncated", False)),
        "stdoutPath": getattr(result, "stdout_path", None),
        "stderrPath": getattr(result, "stderr_path", None),
        "stdoutTotalBytes": int(getattr(result, "stdout_total_bytes", 0) or 0),
        "stderrTotalBytes": int(getattr(result, "stderr_total_bytes", 0) or 0),
        "outputArtifactError": getattr(result, "output_artifact_error", None),
        "analysis": serialize_command_output_analysis(result),
    }
    if index is not None:
        item["index"] = index
    return item


def serialize_command_check(check: object, index: int | None = None) -> dict[str, object]:
    item: dict[str, object] = {
        "command": str(getattr(check, "command", "") or ""),
        "cwd": str(getattr(check, "cwd", ".") or "."),
        "ok": bool(getattr(check, "ok", False)),
        "cwdOk": bool(getattr(check, "cwd_ok", False)),
        "blocked": bool(getattr(check, "blocked", False)),
        "executableAvailable": bool(getattr(check, "executable_available", False)),
        "blockReason": getattr(check, "block_reason", None),
        "missingTool": getattr(check, "missing_tool", None),
        "message": str(getattr(check, "message", "") or ""),
    }
    if index is not None:
        item["index"] = index
    return item


def validate_run_output_context_options(
    *,
    context_lines: int,
    max_diagnostics: int,
    max_contexts: int,
    max_bytes_per_context: int,
    usage: str,
) -> str | None:
    if context_lines < 0:
        return f"{usage}\nError: context_lines must be at least 0."
    if context_lines > 500:
        return f"{usage}\nError: context_lines must be at most 500."
    if max_diagnostics < 1:
        return f"{usage}\nError: max_diagnostics must be at least 1."
    if max_diagnostics > 200:
        return f"{usage}\nError: max_diagnostics must be at most 200."
    if max_contexts < 1:
        return f"{usage}\nError: max_contexts must be at least 1."
    if max_contexts > 100:
        return f"{usage}\nError: max_contexts must be at most 100."
    if max_bytes_per_context < 1_000:
        return f"{usage}\nError: max_bytes_per_context must be at least 1000."
    if max_bytes_per_context > 200_000:
        return f"{usage}\nError: max_bytes_per_context must be at most 200000."
    return None
