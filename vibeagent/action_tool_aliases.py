from __future__ import annotations

from typing import Any


CLAUDE_TOOL_ACTION_ALIASES: dict[str, str] = {
    "Bash": "run_command",
    "Edit": "edit_file",
    "Glob": "glob",
    "Grep": "search",
    "LS": "list_tree",
    "MultiEdit": "multi_edit_file",
    "Read": "read_file",
    "TodoRead": "todo_read",
    "TodoWrite": "todo_write",
    "Write": "write_file",
}


def normalize_tool_action(name: str, tool_input: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    action_type = CLAUDE_TOOL_ACTION_ALIASES.get(name, name)
    if action_type == "read_file":
        return action_type, _rename_fields(tool_input, {"file_path": "path", "offset": "start_line", "limit": "line_count"})
    if action_type in {"write_file", "list_tree"}:
        return action_type, _rename_fields(tool_input, {"file_path": "path"})
    if action_type == "edit_file":
        return action_type, _rename_fields(tool_input, {"file_path": "path", "old_string": "old", "new_string": "new"})
    if action_type == "multi_edit_file":
        return action_type, _normalize_multi_edit_input(tool_input)
    if action_type == "search":
        return action_type, _rename_fields(tool_input, {"pattern": "query"})
    return action_type, dict(tool_input)


def _rename_fields(value: dict[str, Any], aliases: dict[str, str]) -> dict[str, Any]:
    normalized = dict(value)
    for source, target in aliases.items():
        if source in normalized and target not in normalized:
            normalized[target] = normalized[source]
        normalized.pop(source, None)
    return normalized


def _normalize_multi_edit_input(value: dict[str, Any]) -> dict[str, Any]:
    normalized = _rename_fields(value, {"file_path": "path"})
    edits = normalized.get("edits")
    if isinstance(edits, list):
        normalized["edits"] = [
            _rename_fields(edit, {"old_string": "old", "new_string": "new"}) if isinstance(edit, dict) else edit
            for edit in edits
        ]
    return normalized


__all__ = [
    "CLAUDE_TOOL_ACTION_ALIASES",
    "normalize_tool_action",
]
