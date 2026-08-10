from __future__ import annotations

from collections.abc import Callable
import re
from typing import Any

from .action_parsing_helpers import ActionParseError, coerce_int
from .action_tool_alias_sets import (
    BASH_TOOL_NAMES,
    CLAUDE_MCP_TOOL_NAME_PATTERN,
    CLAUDE_TOOL_ACTION_ALIASES,
    CLAUDE_TOOL_ALIASES,
    FILE_EDIT_TOOL_NAMES,
    FILE_READ_TOOL_NAMES,
    PROFILE_TOOL_ALIAS_EXPANSIONS,
)
from .action_tool_alias_search import normalize_search_input
from .action_tool_alias_utils import rename_fields, truthy_alias_bool


ToolInputNormalizer = Callable[[dict[str, Any]], dict[str, Any]]


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


def tool_name_matches_restriction(restriction: str, name: str) -> bool:
    if restriction == name:
        return True
    if not restriction.startswith("mcp__") or not name.startswith("mcp__"):
        return False
    if restriction.endswith("__*"):
        return name.startswith(restriction[:-1])
    return restriction.count("__") == 1 and name.startswith(f"{restriction}__")


def tool_name_is_restricted(restrictions: frozenset[str], name: str) -> bool:
    return any(
        tool_name_matches_restriction(restriction, name)
        for restriction in restrictions
    )


def normalize_tool_action(name: str, tool_input: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    mcp_action = _normalize_claude_mcp_tool_action(name, tool_input)
    if mcp_action is not None:
        return mcp_action

    action_type = CLAUDE_TOOL_ACTION_ALIASES.get(name, name)
    if name == "Bash" and truthy_alias_bool(tool_input.get("run_in_background")):
        return "start_command", _drop_fields(
            dict(tool_input),
            {"run_in_background", "timeout", "timeout_ms"},
        )
    if name == "BashOutput":
        output_action = _normalize_bash_output_action(tool_input)
        if output_action is not None:
            return output_action
    if name == "NotebookEdit" and "new_source" not in tool_input and "old_string" in tool_input and "new_string" in tool_input:
        if truthy_alias_bool(tool_input.get("replace_all")):
            return "regex_replace", _normalize_edit_replace_all_input(tool_input)
        return "edit_file", _normalize_edit_file_input(tool_input)
    if name == "Edit" and truthy_alias_bool(tool_input.get("replace_all")):
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


CLAUDE_BUILTIN_SUBAGENT_TYPES = frozenset({"general-purpose"})


def _normalize_task_input(value: dict[str, Any]) -> dict[str, Any]:
    normalized = _rename_fields(
        value,
        {
            "prompt": "task",
            "description": "context",
            "subagent_type": "agent",
            "name": "teammate_name",
        },
    )
    normalized.pop("team_name", None)
    if normalized.get("agent") in CLAUDE_BUILTIN_SUBAGENT_TYPES:
        normalized.pop("agent")
    normalized.setdefault("mode", "explore")
    if normalized.get("teammate_name") is not None:
        normalized["run_in_background"] = True
    return normalized


def _normalize_task_create_input(value: dict[str, Any]) -> dict[str, Any]:
    return _rename_fields(value, {"activeForm": "active_form"})


def _normalize_task_id_input(value: dict[str, Any]) -> dict[str, Any]:
    return _rename_fields(value, {"taskId": "task_id"})


def _normalize_task_update_input(value: dict[str, Any]) -> dict[str, Any]:
    return _rename_fields(
        value,
        {
            "taskId": "task_id",
            "activeForm": "active_form",
            "addBlocks": "add_blocks",
            "addBlockedBy": "add_blocked_by",
        },
    )


def _normalize_process_alias_input(value: dict[str, Any]) -> dict[str, Any]:
    return _rename_fields(value, {"bash_id": "process_id", "filter": "output_filter"})


def _normalize_ask_user_input(value: dict[str, Any]) -> dict[str, Any]:
    return _rename_fields(value, {"prompt": "question"})


def _normalize_skill_input(value: dict[str, Any]) -> dict[str, Any]:
    return _rename_fields(value, {"skill": "name", "args": "arguments"})


def _normalize_tool_search_input(value: dict[str, Any]) -> dict[str, Any]:
    return _rename_fields(value, {"max_results": "max_matches"})


def _normalize_lsp_input(value: dict[str, Any]) -> dict[str, Any]:
    return _rename_fields(value, {"filePath": "path", "query": "symbol", "maxResults": "max_results"})


def _normalize_bash_input(value: dict[str, Any]) -> dict[str, Any]:
    return _rename_fields(value, {"timeout": "timeout_ms"})


def _normalize_bash_output_action(value: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    normalized = _normalize_process_alias_input(value)
    normalized.pop("extract_output_contexts", None)
    normalized.pop("extract_output_diagnostics", None)
    normalized.pop("filter", None)
    if truthy_alias_bool(value.get("extract_output_diagnostics")):
        return "process_output_diagnostics", normalized
    if truthy_alias_bool(value.get("extract_output_contexts")):
        normalized.pop("max_diagnostics", None)
        return "process_output_contexts", normalized
    return None


def _normalize_read_file_input(value: dict[str, Any]) -> dict[str, Any]:
    return _rename_fields(
        value,
        {"file_path": "path", "notebook_path": "path", "offset": "start_line", "limit": "line_count"},
    )


def _normalize_read_range_alias(value: Any) -> dict[str, int]:
    if isinstance(value, dict):
        start = value.get("start", value.get("start_line"))
        end = value.get("end", value.get("end_line"))
    elif isinstance(value, (list, tuple)) and len(value) == 2:
        start, end = value
    elif isinstance(value, str):
        match = re.fullmatch(r"\s*(\d+)\s*[-:]\s*(\d+)\s*", value)
        if match is None:
            return {}
        start, end = match.groups()
    else:
        return {}

    start_int = coerce_int(start)
    end_int = coerce_int(end)
    if start_int is None or end_int is None or start_int < 1 or end_int < start_int:
        return {}
    return {"start_line": start_int, "line_count": end_int - start_int + 1}


def _is_zero_offset_alias(value: Any) -> bool:
    return coerce_int(value) == 0


def _normalize_claude_read_file_input(value: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_read_file_input(value)
    if "read_range" in normalized and "start_line" not in normalized and "line_count" not in normalized:
        range_fields = _normalize_read_range_alias(normalized["read_range"])
        if not range_fields:
            raise ActionParseError(
                "Read tool read_range must be an inclusive range object, [start, end], or 'start-end'.",
                repr(value),
            )
        normalized.update(range_fields)
    normalized.pop("read_range", None)
    if _is_zero_offset_alias(normalized.get("start_line")):
        normalized["start_line"] = 1
    if "line_count" in normalized and "start_line" not in normalized:
        normalized["start_line"] = 1
    return normalized


def _normalize_claude_notebook_read_input(value: dict[str, Any]) -> dict[str, Any]:
    normalized = _rename_fields(
        value,
        {"notebook_path": "path", "offset": "start_cell", "limit": "cell_count"},
    )
    if _is_zero_offset_alias(normalized.get("start_cell")):
        normalized["start_cell"] = 1
    return normalized


def _normalize_path_alias_input(value: dict[str, Any]) -> dict[str, Any]:
    return _rename_fields(value, {"file_path": "path"})


def _normalize_edit_file_input(value: dict[str, Any]) -> dict[str, Any]:
    return _rename_fields(
        value,
        {"file_path": "path", "notebook_path": "path", "old_string": "old", "new_string": "new"},
    )


def _normalize_notebook_edit_input(value: dict[str, Any]) -> dict[str, Any]:
    return _rename_fields(
        value,
        {"notebook_path": "path"},
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
    "CronDelete": _normalize_task_id_input,
    "ExitPlanMode": _normalize_exit_plan_mode_input,
    "NotebookRead": _normalize_claude_notebook_read_input,
    "LSP": _normalize_lsp_input,
    "Read": _normalize_claude_read_file_input,
    "Skill": _normalize_skill_input,
    "TaskCreate": _normalize_task_create_input,
    "TaskGet": _normalize_task_id_input,
    "TaskUpdate": _normalize_task_update_input,
    "ToolSearch": _normalize_tool_search_input,
    "NotebookEdit": _normalize_notebook_edit_input,
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
