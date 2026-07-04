from __future__ import annotations


def format_next_action_items(items: list[str], max_items: int = 3) -> str:
    shown = items[:max_items]
    suffix = "" if len(items) <= max_items else f"; +{len(items) - max_items} more"
    return "; ".join(shown) + suffix


def diagnostic_labels(values: object) -> list[str]:
    labels: list[str] = []
    if not isinstance(values, list):
        return labels
    for value in values:
        path = str(getattr(value, "path", "") or "").strip()
        line = getattr(value, "line", None)
        column = getattr(value, "column", None)
        text = str(getattr(value, "text", "") or "").strip()
        severity = str(getattr(value, "severity", "") or "").strip()
        location = path
        if path and isinstance(line, int):
            location = f"{path}:{line}"
            if isinstance(column, int):
                location = f"{location}:{column}"
        if location and text:
            labels.append(f"{location} {severity}: {text}" if severity else f"{location}: {text}")
        elif location:
            labels.append(location)
        elif text:
            labels.append(f"{severity}: {text}" if severity else text)
    return labels


def context_labels(values: object) -> list[str]:
    labels: list[str] = []
    if not isinstance(values, list):
        return labels
    for value in values:
        path = str(getattr(value, "path", "") or "").strip()
        line = getattr(value, "line", None)
        column = getattr(value, "column", None)
        raw = str(getattr(value, "raw", "") or "").strip()
        ok = getattr(value, "ok", True)
        label = path
        if path and isinstance(line, int):
            label = f"{path}:{line}"
            if isinstance(column, int):
                label = f"{label}:{column}"
        if not label:
            label = raw
        if label:
            labels.append(label if ok else f"{label} (context unavailable)")
    return labels


def check_failure_labels(values: object) -> list[str]:
    labels: list[str] = []
    if not isinstance(values, list):
        return labels
    for value in values:
        if getattr(value, "ok", True):
            continue
        path = str(getattr(value, "path", "") or "").strip()
        line = getattr(value, "line", None)
        column = getattr(value, "column", None)
        message = str(getattr(value, "message", "") or "").strip()
        label = path
        if path and isinstance(line, int):
            label = f"{path}:{line}"
            if isinstance(column, int):
                label = f"{label}:{column}"
        if label and message:
            labels.append(f"{label}: {message}")
        elif label:
            labels.append(label)
        elif message:
            labels.append(message)
    return labels


def command_result_failed(result: object) -> bool:
    return bool(getattr(result, "timed_out", False)) or getattr(result, "exit_code", 0) != 0


def failed_command_labels(results: object) -> list[str]:
    labels: list[str] = []
    if not isinstance(results, list):
        return labels
    for result in results:
        if not command_result_failed(result):
            continue
        command = str(getattr(result, "command", "") or "").strip()
        cwd = str(getattr(result, "cwd", ".") or ".").strip()
        exit_code = getattr(result, "exit_code", None)
        timed_out = bool(getattr(result, "timed_out", False))
        status = "timed out" if timed_out else f"exit {exit_code}"
        if command:
            labels.append(f"{command} (cwd={cwd}, {status})")
        else:
            labels.append(status)
    return labels


def not_run_selected_command_labels(values: object, ran_count: int) -> list[str]:
    labels: list[str] = []
    if not isinstance(values, list):
        return labels
    for index, value in enumerate(values):
        if index < ran_count or not isinstance(value, dict):
            continue
        command = str(value.get("command") or "").strip()
        cwd = str(value.get("cwd") or ".").strip() or "."
        status = str(value.get("status") or "").strip()
        if not command:
            continue
        label = f"{command} (cwd={cwd})"
        if status:
            label = f"{label}: {status}"
        labels.append(label)
    return labels
