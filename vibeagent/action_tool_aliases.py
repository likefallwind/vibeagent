from __future__ import annotations

from collections.abc import Callable
from typing import Any


ToolInputNormalizer = Callable[[dict[str, Any]], dict[str, Any]]


CLAUDE_TOOL_ACTION_ALIASES: dict[str, str] = {
    "AskUserQuestion": "ask_user",
    "Agent": "delegate_task",
    "Bash": "run_command",
    "BashOutput": "read_process",
    "Edit": "edit_file",
    "ExitPlanMode": "update_plan",
    "Glob": "glob",
    "Grep": "search",
    "KillBash": "stop_process",
    "LS": "list_tree",
    "MultiEdit": "multi_edit_file",
    "NotebookEdit": "edit_file",
    "NotebookRead": "read_file",
    "Read": "read_file",
    "Task": "delegate_task",
    "TodoRead": "todo_read",
    "TodoWrite": "todo_write",
    "WebFetch": "web_fetch",
    "Write": "write_file",
}


def normalize_tool_action(name: str, tool_input: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    mcp_action = _normalize_claude_mcp_tool_action(name, tool_input)
    if mcp_action is not None:
        return mcp_action

    action_type = CLAUDE_TOOL_ACTION_ALIASES.get(name, name)
    if name == "Bash" and tool_input.get("run_in_background") is True:
        return "start_command", _drop_fields(
            dict(tool_input),
            {"run_in_background", "timeout_ms", "max_output_chars"},
        )

    normalizer = _NAME_INPUT_NORMALIZERS.get(name) or _ACTION_INPUT_NORMALIZERS.get(action_type)
    if normalizer is not None:
        return action_type, normalizer(tool_input)
    return action_type, dict(tool_input)


def _rename_fields(value: dict[str, Any], aliases: dict[str, str]) -> dict[str, Any]:
    normalized = dict(value)
    for source, target in aliases.items():
        if source in normalized and target not in normalized:
            normalized[target] = normalized[source]
        normalized.pop(source, None)
    return normalized


def _drop_fields(value: dict[str, Any], fields: set[str]) -> dict[str, Any]:
    for field in fields:
        value.pop(field, None)
    return value


def _normalize_exit_plan_mode_input(value: dict[str, Any]) -> dict[str, Any]:
    plan = value.get("plan")
    if isinstance(plan, list):
        return {"plan": plan}
    if isinstance(plan, str) and plan.strip():
        return {"plan": [{"step": plan.strip(), "status": "completed"}]}
    return dict(value)


def _normalize_multi_edit_input(value: dict[str, Any]) -> dict[str, Any]:
    normalized = _rename_fields(value, {"file_path": "path"})
    edits = normalized.get("edits")
    if isinstance(edits, list):
        normalized["edits"] = [
            _rename_fields(edit, {"old_string": "old", "new_string": "new"}) if isinstance(edit, dict) else edit
            for edit in edits
        ]
    return normalized


def _normalize_search_input(value: dict[str, Any]) -> dict[str, Any]:
    normalized = _rename_fields(value, {"pattern": "query", "head_limit": "max_matches"})
    if normalized.get("output_mode") == "content" and "context_lines" not in normalized:
        normalized["context_lines"] = 2
    return normalized


def _normalize_glob_input(value: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(value)
    pattern = normalized.get("pattern")
    path = normalized.pop("path", None)
    if isinstance(pattern, str) and isinstance(path, str) and path.strip():
        normalized["pattern"] = f"{path.strip().rstrip('/')}/{pattern.strip()}"
    return normalized


def _normalize_task_input(value: dict[str, Any]) -> dict[str, Any]:
    normalized = _rename_fields(value, {"prompt": "task", "description": "context", "subagent_type": "agent"})
    normalized.setdefault("mode", "explore")
    return normalized


def _normalize_process_alias_input(value: dict[str, Any]) -> dict[str, Any]:
    return _rename_fields(value, {"bash_id": "process_id"})


def _normalize_ask_user_input(value: dict[str, Any]) -> dict[str, Any]:
    return _rename_fields(value, {"prompt": "question"})


def _normalize_read_file_input(value: dict[str, Any]) -> dict[str, Any]:
    return _rename_fields(
        value,
        {"file_path": "path", "notebook_path": "path", "offset": "start_line", "limit": "line_count"},
    )


def _normalize_path_alias_input(value: dict[str, Any]) -> dict[str, Any]:
    return _rename_fields(value, {"file_path": "path"})


def _normalize_edit_file_input(value: dict[str, Any]) -> dict[str, Any]:
    return _rename_fields(
        value,
        {"file_path": "path", "notebook_path": "path", "old_string": "old", "new_string": "new"},
    )


def _normalize_claude_mcp_tool_action(name: str, tool_input: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    parts = name.split("__", 2)
    if len(parts) != 3 or parts[0] != "mcp":
        return None
    _, server, tool_name = parts
    return "mcp_call", {"server": server, "name": tool_name, "arguments": dict(tool_input)}


_NAME_INPUT_NORMALIZERS: dict[str, ToolInputNormalizer] = {
    "ExitPlanMode": _normalize_exit_plan_mode_input,
}


_ACTION_INPUT_NORMALIZERS: dict[str, ToolInputNormalizer] = {
    "ask_user": _normalize_ask_user_input,
    "delegate_task": _normalize_task_input,
    "edit_file": _normalize_edit_file_input,
    "glob": _normalize_glob_input,
    "list_tree": _normalize_path_alias_input,
    "multi_edit_file": _normalize_multi_edit_input,
    "read_file": _normalize_read_file_input,
    "read_process": _normalize_process_alias_input,
    "search": _normalize_search_input,
    "stop_process": _normalize_process_alias_input,
    "write_file": _normalize_path_alias_input,
}


__all__ = [
    "CLAUDE_TOOL_ACTION_ALIASES",
    "normalize_tool_action",
]
