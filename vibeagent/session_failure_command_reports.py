from __future__ import annotations

from typing import Any

from .session_utils import compact


def command_failure_entry(line_number: int, name: str, command_result: dict[str, Any], max_text: int) -> dict[str, str | int]:
    command = command_result.get("command")
    exit_code = command_result.get("exit_code")
    timed_out = command_result.get("timed_out")
    stderr = command_result.get("stderr")
    detail_parts = [
        f"exit={exit_code if isinstance(exit_code, int) else 'unknown'}",
        f"timedOut={'yes' if timed_out is True else 'no'}",
    ]
    output_issue_detail = command_output_issue_detail(command_result, max_text=max_text)
    if output_issue_detail:
        detail_parts.append(f"outputIssues={output_issue_detail}")
    return {
        "line_number": line_number,
        "type": "command",
        "name": name,
        "message": compact(command, max_text) if isinstance(command, str) and command.strip() else "Command failed.",
        "detail": "; ".join(detail_parts + ([f"stderr={compact(stderr, max_text)}"] if isinstance(stderr, str) and stderr.strip() else [])),
    }


def command_result_failed(command_result: dict[str, Any]) -> bool:
    return (
        command_result.get("exit_code") != 0
        or command_result.get("timed_out") is True
        or bool(command_output_issue_detail(command_result, max_text=500))
    )


def command_output_issue_detail(command_result: dict[str, Any], max_text: int) -> str:
    diagnostics = command_result.get("output_diagnostics")
    labels = command_output_diagnostic_labels(diagnostics, max_text=max_text)
    if labels:
        return compact("; ".join(labels), max_text)
    contexts = command_result.get("output_contexts")
    labels = command_output_context_labels(contexts, max_text=max_text)
    return compact("; ".join(labels), max_text) if labels else ""


def command_output_diagnostic_labels(values: object, max_text: int) -> list[str]:
    if not isinstance(values, list):
        return []
    labels: list[str] = []
    for value in values:
        if not isinstance(value, dict):
            continue
        labels.append(command_output_location_label(value, max_text=max_text))
    return [label for label in labels if label]


def command_output_context_labels(values: object, max_text: int) -> list[str]:
    if not isinstance(values, list):
        return []
    labels: list[str] = []
    for value in values:
        if not isinstance(value, dict):
            continue
        label = command_output_location_label(value, max_text=max_text)
        if not label:
            raw = value.get("raw")
            label = compact(raw, max_text) if isinstance(raw, str) and raw.strip() else ""
        if label:
            labels.append(label)
    return labels


def command_output_location_label(value: dict[str, Any], max_text: int) -> str:
    path = value.get("path")
    if not isinstance(path, str) or not path.strip():
        return ""
    label = path.strip()
    line = value.get("line")
    column = value.get("column")
    if isinstance(line, int):
        label = f"{label}:{line}"
        if isinstance(column, int):
            label = f"{label}:{column}"
    severity = value.get("severity")
    text = value.get("text")
    if isinstance(text, str) and text.strip():
        prefix = f"{severity}: " if isinstance(severity, str) and severity.strip() else ""
        label = f"{label} {prefix}{text.strip()}"
    return compact(label, max_text)
