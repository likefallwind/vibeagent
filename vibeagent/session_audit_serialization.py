from __future__ import annotations

from typing import Any

from .session_utils import compact


def validate_session_audit_limits(
    max_failures: int,
    max_files: int,
    max_commands: int,
    max_checks: int,
    max_text: int,
) -> None:
    if max_failures < 1:
        raise ValueError("max_failures must be at least 1.")
    if max_failures > 200:
        raise ValueError("max_failures must be at most 200.")
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 500:
        raise ValueError("max_files must be at most 500.")
    if max_commands < 1:
        raise ValueError("max_commands must be at least 1.")
    if max_commands > 100:
        raise ValueError("max_commands must be at most 100.")
    if max_checks < 1:
        raise ValueError("max_checks must be at least 1.")
    if max_checks > 500:
        raise ValueError("max_checks must be at most 500.")
    if max_text < 80:
        raise ValueError("max_text must be at least 80.")
    if max_text > 5000:
        raise ValueError("max_text must be at most 5000.")


def validate_session_handoff_limits(max_output_chars: int) -> None:
    if max_output_chars < 0:
        raise ValueError("max_output_chars must be at least 0.")
    if max_output_chars > 20_000:
        raise ValueError("max_output_chars must be at most 20000.")


def serialize_session_failure(failure: dict[str, str | int], max_text: int) -> dict[str, Any]:
    item: dict[str, Any] = {
        "lineNumber": failure.get("line_number"),
        "type": failure.get("type"),
        "name": failure.get("name"),
        "message": compact(str(failure.get("message", "")), max_text),
    }
    detail = failure.get("detail")
    if isinstance(detail, str) and detail.strip():
        item["detail"] = compact(detail, max_text)
    return item


def serialize_session_command_entry(entry: dict[str, Any], max_text: int) -> dict[str, Any]:
    result = entry["result"]
    command = result.get("command")
    cwd = result.get("cwd")
    exit_code = result.get("exit_code")
    duration_ms = result.get("duration_ms")
    return {
        "lineNumber": entry.get("line_number"),
        "kind": entry.get("kind"),
        "index": entry.get("index"),
        "command": compact(command, max_text) if isinstance(command, str) else None,
        "cwd": cwd if isinstance(cwd, str) and cwd else ".",
        "exitCode": exit_code if isinstance(exit_code, int) else None,
        "timedOut": result.get("timed_out") is True,
        "durationMs": duration_ms if isinstance(duration_ms, int) else None,
    }


def failed_checkpoint_create_count(failures: list[dict[str, str | int]]) -> int:
    return sum(
        1
        for failure in failures
        if failure.get("type") == "tool_result" and failure.get("name") == "checkpoint_create"
    )
