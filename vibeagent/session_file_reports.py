from __future__ import annotations

from typing import Any

from .session_types import SessionEvent


def validate_session_files_limit(max_files: int) -> None:
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 500:
        raise ValueError("max_files must be at most 500.")


def session_file_entries(events: list[SessionEvent]) -> list[dict[str, Any]]:
    by_path: dict[str, dict[str, Any]] = {}
    for event in events:
        if event.malformed:
            continue
        tool_name, payload = session_file_payload(event)
        if not tool_name or not isinstance(payload, dict):
            continue
        paths = sorted(extract_session_paths(payload))
        if not paths:
            continue
        use = classify_session_file_use(tool_name)
        for path in paths:
            entry = by_path.setdefault(path, {"path": path, "tools": set(), "uses": set(), "lines": [], "count": 0})
            entry["tools"].add(tool_name)
            entry["uses"].add(use)
            entry["lines"].append(event.line_number)
            entry["count"] += 1

    entries: list[dict[str, Any]] = []
    for entry in by_path.values():
        entries.append(
            {
                "path": entry["path"],
                "tools": sorted(entry["tools"]),
                "uses": sorted(entry["uses"]),
                "lines": sorted(entry["lines"]),
                "count": entry["count"],
            }
        )
    entries.sort(key=lambda item: (item["path"], item["tools"]))
    return entries


def session_file_payload(event: SessionEvent) -> tuple[str | None, dict[str, Any] | None]:
    payload = event.payload
    if event.type == "tool_call":
        name = payload.get("name")
        tool_input = payload.get("input")
        return (name if isinstance(name, str) else None), (tool_input if isinstance(tool_input, dict) else None)
    if event.type == "tool_result":
        result = payload.get("result")
        if not isinstance(result, dict):
            return None, None
        name = payload.get("name")
        kind = result.get("kind")
        tool_name = name if isinstance(name, str) else kind
        return (tool_name if isinstance(tool_name, str) else None), result
    if event.type == "action":
        action = payload.get("action")
        if not isinstance(action, dict):
            return None, None
        action_type = action.get("type")
        return (action_type if isinstance(action_type, str) else None), action
    if event.type == "observation":
        observation = payload.get("observation")
        if not isinstance(observation, dict):
            return None, None
        kind = observation.get("kind")
        return (kind if isinstance(kind, str) else None), observation
    return None, None


def extract_session_paths(value: Any) -> set[str]:
    paths: set[str] = set()
    if not isinstance(value, dict):
        return paths
    for key in ("path", "source", "destination"):
        item = value.get(key)
        if isinstance(item, str):
            add_session_path(paths, item)
    for key in ("paths", "files"):
        item = value.get(key)
        if isinstance(item, list):
            for child in item:
                if isinstance(child, str):
                    add_session_path(paths, child)
                elif isinstance(child, dict):
                    paths.update(extract_session_paths(child))
        elif isinstance(item, dict):
            paths.update(extract_session_paths(item))
    for key in ("ranges", "transfers", "edits"):
        item = value.get(key)
        if isinstance(item, list):
            for child in item:
                paths.update(extract_session_paths(child))
    return paths


def add_session_path(paths: set[str], value: str) -> None:
    path = value.strip()
    if not path or "\n" in path:
        return
    if "://" in path:
        return
    paths.add(path)


def classify_session_file_use(tool_name: str) -> str:
    if tool_name.startswith("check_") or tool_name.endswith("_preview"):
        return "preview"
    if any(token in tool_name for token in ("delete", "remove", "restore")):
        return "delete"
    if any(token in tool_name for token in ("move", "copy", "rename")):
        return "move"
    if any(token in tool_name for token in ("write", "edit", "replace", "insert", "append", "patch", "set", "create")):
        return "write"
    if tool_name.startswith(("read", "list", "search", "glob", "file_info", "image_info", "python_", "code_", "git_", "config_check")):
        return "read"
    return "reference"
