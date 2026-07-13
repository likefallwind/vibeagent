from __future__ import annotations

from collections.abc import Callable
import re
from typing import Any

from .action_tool_alias_search import normalize_search_input
from .action_tool_alias_utils import rename_fields


ToolInputNormalizer = Callable[[dict[str, Any]], dict[str, Any]]


CLAUDE_MCP_TOOL_NAME_PATTERN = re.compile(r"^mcp__[A-Za-z0-9][A-Za-z0-9._-]{0,63}__[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

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

BASH_TOOL_NAMES = frozenset(
    {
        "run_command",
        "run_commands",
        "run_focused_test_commands",
        "run_session_verification",
        "run_suggested_checks",
        "start_command",
    }
)
FILE_EDIT_TOOL_NAMES = frozenset(
    {
        "append_file",
        "code_rename",
        "copy_dir",
        "copy_dirs",
        "copy_file",
        "copy_files",
        "create_dir",
        "create_dirs",
        "delete_empty_dir",
        "delete_empty_dirs",
        "delete_file",
        "delete_files",
        "edit_file",
        "insert_lines",
        "json_patch",
        "json_remove",
        "json_set",
        "move_dir",
        "move_dirs",
        "move_file",
        "move_files",
        "multi_edit_file",
        "patch_file",
        "patch_files",
        "python_rename",
        "regex_replace",
        "replace_lines",
        "replace_python_definition",
        "set_executable",
        "write_file",
        "write_files",
    }
)
FILE_READ_TOOL_NAMES = frozenset(
    {
        "code_definitions",
        "code_dependencies",
        "code_outline",
        "code_reference_contexts",
        "code_references",
        "config_check",
        "file_info",
        "find_files",
        "glob",
        "image_info",
        "list_files",
        "list_tree",
        "python_call_graph",
        "python_calls",
        "python_check",
        "python_definitions",
        "python_dependencies",
        "python_reference_contexts",
        "python_references",
        "python_symbols",
        "read_file",
        "read_file_context",
        "read_file_contexts",
        "read_file_ranges",
        "read_files",
        "repo_map",
        "search",
        "search_contexts",
        "tail_file",
        "view_image",
    }
)
CLAUDE_TOOL_ALIASES = {
    "Agent": frozenset({"delegate_task"}),
    "AskUserQuestion": frozenset({"ask_user"}),
    "Bash": BASH_TOOL_NAMES,
    "BashOutput": frozenset({"read_process"}),
    "Edit": FILE_EDIT_TOOL_NAMES,
    "ExitPlanMode": frozenset({"update_plan"}),
    "Glob": frozenset({"glob"}),
    "Grep": frozenset({"search"}),
    "KillBash": frozenset({"stop_process"}),
    "LS": frozenset({"list_tree"}),
    "MultiEdit": frozenset({"multi_edit_file"}),
    "NotebookEdit": FILE_EDIT_TOOL_NAMES,
    "NotebookRead": FILE_READ_TOOL_NAMES,
    "Read": FILE_READ_TOOL_NAMES,
    "Task": frozenset({"delegate_task"}),
    "TodoRead": frozenset({"session_plan"}),
    "TodoWrite": frozenset({"update_plan"}),
    "WebFetch": frozenset({"web_fetch"}),
    "Write": FILE_EDIT_TOOL_NAMES,
}
PROFILE_TOOL_ALIAS_EXPANSIONS = {
    "Bash": frozenset({"run_command", "start_command"}),
    "TodoRead": frozenset({"session_plan"}),
}


def tool_name_candidates(tool_name: str, action: object | None = None) -> tuple[str, ...]:
    names = [tool_name]
    action_type = getattr(action, "type", None)
    if isinstance(action_type, str) and action_type not in names:
        names.append(action_type)
    mcp_alias = _mcp_alias_candidate(action)
    if mcp_alias is not None and mcp_alias not in names:
        names.append(mcp_alias)
    for alias, internal_names in CLAUDE_TOOL_ALIASES.items():
        if alias in names:
            continue
        if tool_name == alias or tool_name in internal_names or action_type in internal_names:
            names.append(alias)
    return tuple(names)


def _mcp_alias_candidate(action: object | None) -> str | None:
    if getattr(action, "type", None) != "mcp_call":
        return None
    server = getattr(action, "server", None)
    name = getattr(action, "name", None)
    if not isinstance(server, str) or not isinstance(name, str):
        return None
    candidate = f"mcp__{server}__{name}"
    return candidate if CLAUDE_MCP_TOOL_NAME_PATTERN.fullmatch(candidate) else None


def profile_tool_names(name: str) -> frozenset[str]:
    if CLAUDE_MCP_TOOL_NAME_PATTERN.fullmatch(name):
        return frozenset({"mcp_tools", name})
    expanded = PROFILE_TOOL_ALIAS_EXPANSIONS.get(name)
    if expanded is not None:
        return expanded
    return frozenset({CLAUDE_TOOL_ACTION_ALIASES.get(name, name)})


def normalize_tool_action(name: str, tool_input: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    mcp_action = _normalize_claude_mcp_tool_action(name, tool_input)
    if mcp_action is not None:
        return mcp_action

    action_type = CLAUDE_TOOL_ACTION_ALIASES.get(name, name)
    if name == "Bash" and tool_input.get("run_in_background") is True:
        return "start_command", _drop_fields(
            dict(tool_input),
            {"run_in_background", "timeout", "timeout_ms", "max_output_chars"},
        )
    if name in {"Edit", "NotebookEdit"} and tool_input.get("replace_all") is True:
        return "regex_replace", _normalize_edit_replace_all_input(tool_input)

    normalizer = _NAME_INPUT_NORMALIZERS.get(name) or _ACTION_INPUT_NORMALIZERS.get(action_type)
    if normalizer is not None:
        return action_type, normalizer(tool_input)
    return action_type, dict(tool_input)


def _rename_fields(value: dict[str, Any], aliases: dict[str, str]) -> dict[str, Any]:
    return rename_fields(value, aliases)


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
    return _rename_fields(value, {"bash_id": "process_id", "filter": "output_filter"})


def _normalize_ask_user_input(value: dict[str, Any]) -> dict[str, Any]:
    return _rename_fields(value, {"prompt": "question"})


def _normalize_bash_input(value: dict[str, Any]) -> dict[str, Any]:
    return _rename_fields(value, {"timeout": "timeout_ms"})


def _normalize_read_file_input(value: dict[str, Any]) -> dict[str, Any]:
    return _rename_fields(
        value,
        {"file_path": "path", "notebook_path": "path", "offset": "start_line", "limit": "line_count"},
    )


def _normalize_claude_read_file_input(value: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_read_file_input(value)
    if normalized.get("start_line") == 0:
        normalized["start_line"] = 1
    if "line_count" in normalized and "start_line" not in normalized:
        normalized["start_line"] = 1
    return normalized


def _normalize_path_alias_input(value: dict[str, Any]) -> dict[str, Any]:
    return _rename_fields(value, {"file_path": "path"})


def _normalize_edit_file_input(value: dict[str, Any]) -> dict[str, Any]:
    return _rename_fields(
        value,
        {"file_path": "path", "notebook_path": "path", "old_string": "old", "new_string": "new"},
    )


def _normalize_edit_replace_all_input(value: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_edit_file_input(value)
    old = normalized.get("old")
    new = normalized.get("new")
    if isinstance(old, str):
        normalized["pattern"] = re.escape(old)
    if isinstance(new, str):
        normalized["replacement"] = new.replace("\\", "\\\\")
    normalized.pop("old", None)
    normalized.pop("new", None)
    normalized.pop("replace_all", None)
    normalized.setdefault("count", 0)
    return normalized


def _normalize_claude_mcp_tool_action(name: str, tool_input: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    parts = name.split("__", 2)
    if len(parts) != 3 or parts[0] != "mcp":
        return None
    _, server, tool_name = parts
    return "mcp_call", {"server": server, "name": tool_name, "arguments": dict(tool_input)}


_NAME_INPUT_NORMALIZERS: dict[str, ToolInputNormalizer] = {
    "Bash": _normalize_bash_input,
    "ExitPlanMode": _normalize_exit_plan_mode_input,
    "NotebookRead": _normalize_claude_read_file_input,
    "Read": _normalize_claude_read_file_input,
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
    "search": normalize_search_input,
    "stop_process": _normalize_process_alias_input,
    "write_file": _normalize_path_alias_input,
}


__all__ = [
    "BASH_TOOL_NAMES",
    "CLAUDE_MCP_TOOL_NAME_PATTERN",
    "CLAUDE_TOOL_ACTION_ALIASES",
    "CLAUDE_TOOL_ALIASES",
    "FILE_EDIT_TOOL_NAMES",
    "FILE_READ_TOOL_NAMES",
    "normalize_tool_action",
    "profile_tool_names",
    "tool_name_candidates",
]
