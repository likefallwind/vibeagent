from __future__ import annotations

from typing import Any


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
        return "start_command", _drop_fields(dict(tool_input), {"run_in_background", "timeout_ms", "max_output_chars"})
    if action_type in {"read_process", "stop_process"}:
        return action_type, _rename_fields(tool_input, {"bash_id": "process_id"})
    if name == "ExitPlanMode":
        return action_type, _normalize_exit_plan_mode_input(tool_input)
    if action_type == "ask_user":
        return action_type, _rename_fields(tool_input, {"prompt": "question"})
    if action_type == "delegate_task":
        return action_type, _normalize_task_input(tool_input)
    if action_type == "read_file":
        return action_type, _rename_fields(
            tool_input,
            {"file_path": "path", "notebook_path": "path", "offset": "start_line", "limit": "line_count"},
        )
    if action_type in {"write_file", "list_tree"}:
        return action_type, _rename_fields(tool_input, {"file_path": "path"})
    if action_type == "edit_file":
        return action_type, _rename_fields(
            tool_input,
            {"file_path": "path", "notebook_path": "path", "old_string": "old", "new_string": "new"},
        )
    if action_type == "multi_edit_file":
        return action_type, _normalize_multi_edit_input(tool_input)
    if action_type == "search":
        return action_type, _normalize_search_input(tool_input)
    if action_type == "glob":
        return action_type, _normalize_glob_input(tool_input)
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


def _normalize_claude_mcp_tool_action(name: str, tool_input: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    parts = name.split("__", 2)
    if len(parts) != 3 or parts[0] != "mcp":
        return None
    _, server, tool_name = parts
    return "mcp_call", {"server": server, "name": tool_name, "arguments": dict(tool_input)}


__all__ = [
    "CLAUDE_TOOL_ACTION_ALIASES",
    "normalize_tool_action",
]
