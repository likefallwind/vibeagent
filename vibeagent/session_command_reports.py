from __future__ import annotations

from typing import Any

from .redaction import redact_sensitive_text
from .session_types import SessionEvent
from .session_utils import compact


def session_command_entries(events: list[SessionEvent]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for event in events:
        if event.malformed or event.type != "tool_result":
            continue
        result = event.payload.get("result")
        if not isinstance(result, dict):
            continue
        kind = result.get("kind")
        if kind == "run_command":
            command_result = result.get("result")
            if isinstance(command_result, dict):
                entries.append({"line_number": event.line_number, "kind": kind, "index": 1, "result": command_result})
        elif kind in {"run_commands", "run_suggested_checks", "run_focused_test_commands"}:
            command_results = result.get("results")
            if isinstance(command_results, list):
                for index, command_result in enumerate(command_results, start=1):
                    if isinstance(command_result, dict):
                        entries.append({"line_number": event.line_number, "kind": kind, "index": index, "result": command_result})
    return entries


def format_session_command_entry(entry: dict[str, Any], max_output_chars: int) -> list[str]:
    result = entry["result"]
    command = result.get("command")
    exit_code = result.get("exit_code")
    timed_out = result.get("timed_out")
    cwd = result.get("cwd")
    signal = result.get("signal")
    duration_ms = result.get("duration_ms")
    parts = [
        f"exit={exit_code if isinstance(exit_code, int) else 'unknown'}",
        f"timedOut={'yes' if timed_out is True else 'no'}",
    ]
    if isinstance(duration_ms, int):
        parts.append(f"durationMs={duration_ms}")
    if isinstance(signal, str) and signal:
        parts.append(f"signal={signal}")
    if isinstance(cwd, str) and cwd:
        parts.append(f"cwd={cwd}")
    header = f"    - #{entry['line_number']} {entry['kind']}[{entry['index']}]: " + ", ".join(parts)
    lines = [header, f"      command: {compact(command, 500) if isinstance(command, str) else 'unknown'}"]
    lines.extend(format_session_command_stream("stdout", result.get("stdout"), result.get("stdout_truncated"), max_output_chars))
    lines.extend(format_session_command_stream("stderr", result.get("stderr"), result.get("stderr_truncated"), max_output_chars))
    for label, key in (("stdoutPath", "stdout_path"), ("stderrPath", "stderr_path")):
        value = result.get(key)
        if isinstance(value, str) and value:
            lines.append(f"      {label}: {value}")
    artifact_error = result.get("output_artifact_error")
    if isinstance(artifact_error, str) and artifact_error:
        lines.append(f"      outputArtifactError: {artifact_error}")
    return lines


def format_session_command_stream(label: str, value: Any, already_truncated: Any, max_output_chars: int) -> list[str]:
    text = value if isinstance(value, str) else ""
    clipped = command_output_tail(text, max_output_chars)
    suffix = " (stored truncated)" if already_truncated is True else ""
    lines = [f"      {label}{suffix}:"]
    if not clipped:
        lines.append("        (empty)")
    else:
        lines.extend(f"        {line}" for line in clipped.splitlines())
    return lines


def command_output_tail(value: str, max_chars: int) -> str:
    redacted = redact_sensitive_text(value)
    if max_chars == 0:
        return ""
    if len(redacted) <= max_chars:
        return redacted
    return "[... omitted earlier output ...]\n" + redacted[-max_chars:]


def serialize_session_command_with_output(entry: dict[str, Any], max_output_chars: int) -> dict[str, Any]:
    result = entry["result"]
    command = result.get("command")
    cwd = result.get("cwd")
    exit_code = result.get("exit_code")
    signal = result.get("signal")
    duration_ms = result.get("duration_ms")
    stdout = result.get("stdout")
    stderr = result.get("stderr")
    return {
        "lineNumber": entry.get("line_number"),
        "kind": entry.get("kind"),
        "index": entry.get("index"),
        "command": compact(command, 500) if isinstance(command, str) else None,
        "cwd": cwd if isinstance(cwd, str) and cwd else ".",
        "exitCode": exit_code if isinstance(exit_code, int) else None,
        "timedOut": result.get("timed_out") is True,
        "durationMs": duration_ms if isinstance(duration_ms, int) else None,
        "signal": signal if isinstance(signal, str) and signal else None,
        "stdout": command_output_tail(stdout if isinstance(stdout, str) else "", max_output_chars),
        "stdoutStoredTruncated": result.get("stdout_truncated") is True,
        "stdoutPath": result.get("stdout_path") if isinstance(result.get("stdout_path"), str) else None,
        "stdoutTotalBytes": result.get("stdout_total_bytes") if isinstance(result.get("stdout_total_bytes"), int) else 0,
        "stderr": command_output_tail(stderr if isinstance(stderr, str) else "", max_output_chars),
        "stderrStoredTruncated": result.get("stderr_truncated") is True,
        "stderrPath": result.get("stderr_path") if isinstance(result.get("stderr_path"), str) else None,
        "stderrTotalBytes": result.get("stderr_total_bytes") if isinstance(result.get("stderr_total_bytes"), int) else 0,
        "outputArtifactError": result.get("output_artifact_error") if isinstance(result.get("output_artifact_error"), str) else None,
    }
