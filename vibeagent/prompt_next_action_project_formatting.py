from __future__ import annotations


def command_labels(values: object) -> list[str]:
    labels: list[str] = []
    if not isinstance(values, list):
        return labels
    for value in values:
        label = command_label(value)
        if label:
            labels.append(label)
    return labels


def available_command_labels(values: object) -> list[str]:
    labels: list[str] = []
    if not isinstance(values, list):
        return labels
    for value in values:
        if not getattr(value, "available", True):
            continue
        label = command_label(value)
        if label:
            labels.append(label)
    return labels


def available_skill_names(values: object) -> list[str]:
    names: list[str] = []
    if not isinstance(values, list):
        return names
    for value in values:
        if not getattr(value, "available", False):
            continue
        name = str(getattr(value, "name", "") or "").strip()
        if name:
            names.append(name)
    return names


def command_label(value: object) -> str | None:
    command = str(getattr(value, "command", "") or "").strip()
    if not command:
        return None
    cwd = str(getattr(value, "cwd", ".") or ".").strip() or "."
    return f"{command} (cwd={cwd})"


def blocked_check_labels(values: object) -> list[str]:
    labels: list[str] = []
    if not isinstance(values, list):
        return labels
    for value in values:
        if getattr(value, "ok", False):
            continue
        label = blocked_check_label(value)
        if label:
            labels.append(label)
    return labels


def blocked_check_label(value: object) -> str | None:
    command = str(getattr(value, "command", "") or "").strip()
    reason = blocked_check_reason(value)
    if command and reason:
        return f"{command}: {reason}"
    return command or reason or None


def blocked_check_reason(value: object) -> str:
    return str(
        getattr(value, "block_reason", "")
        or getattr(value, "missing_tool", "")
        or getattr(value, "message", "")
        or ""
    ).strip()


def format_next_action_items(items: list[str], max_items: int = 3) -> str:
    shown = items[:max_items]
    suffix = "" if len(items) <= max_items else f"; +{len(items) - max_items} more"
    return "; ".join(shown) + suffix


def tool_names(matches: object) -> list[str]:
    names: list[str] = []
    if not isinstance(matches, list):
        return names
    for match in matches:
        if not isinstance(match, dict):
            continue
        name = str(match.get("name") or "").strip()
        if name:
            names.append(name)
    return names


def manifest_paths(values: object) -> list[str]:
    paths: list[str] = []
    if not isinstance(values, list):
        return paths
    for value in values:
        path = str(getattr(value, "path", "") or "").strip()
        if path:
            paths.append(path)
    return paths


def instruction_paths(values: object) -> list[str]:
    paths: list[str] = []
    if not isinstance(values, list):
        return paths
    for value in values:
        if not getattr(value, "included", False):
            continue
        path = str(getattr(value, "path", "") or "").strip()
        if path:
            paths.append(path)
    return paths


def todo_labels(values: object) -> list[str]:
    labels: list[str] = []
    if not isinstance(values, list):
        return labels
    for value in values:
        path = str(getattr(value, "path", "") or "").strip()
        line = getattr(value, "line", None)
        marker = str(getattr(value, "marker", "") or "").strip()
        text = str(getattr(value, "text", "") or "").strip()
        location = f"{path}:{line}" if path and isinstance(line, int) else path
        label = location
        if marker:
            label = f"{label} [{marker}]" if label else f"[{marker}]"
        if text:
            label = f"{label} {text}" if label else text
        if label:
            labels.append(label)
    return labels


def unavailable_tool_names(values: object) -> list[str]:
    names: list[str] = []
    if not isinstance(values, list):
        return names
    for value in values:
        if getattr(value, "available", False):
            continue
        name = str(getattr(value, "name", "") or "").strip()
        if name:
            names.append(name)
    return names
