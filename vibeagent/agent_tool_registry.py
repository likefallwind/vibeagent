from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .agent_runtime_utils import append_session_event
from .tool_definitions import AGENT_TOOL_DEFINITIONS
from .types import Observation
from .workspace_core import RunWorkspace


CORE_AGENT_TOOL_NAMES = frozenset(
    {
        "ask_user",
        "check_edit_file",
        "check_patch",
        "check_write_file",
        "command_check",
        "delegate_task",
        "edit_file",
        "file_info",
        "final_review",
        "find_files",
        "finish",
        "focused_test_commands",
        "git_changes",
        "git_diff",
        "git_status",
        "glob",
        "list_files",
        "list_tree",
        "patch_file",
        "project_instructions",
        "project_overview",
        "read_file",
        "read_file_context",
        "read_files",
        "related_tests",
        "repo_map",
        "run_command",
        "search",
        "search_contexts",
        "suggest_checks",
        "tool_search",
        "update_plan",
        "write_file",
    }
)

TOOL_DEFINITION_BY_NAME = {
    str(tool["name"]): tool
    for tool in AGENT_TOOL_DEFINITIONS
}


def initial_agent_tool_names() -> set[str]:
    return set(CORE_AGENT_TOOL_NAMES)


def initialize_agent_tools(workspace: RunWorkspace) -> set[str]:
    active_names = initial_agent_tool_names()
    append_session_event(
        workspace.session_dir,
        "tool_catalog_initialized",
        {
            "active": len(active_names),
            "total": len(AGENT_TOOL_DEFINITIONS),
            "tools": sorted(active_names),
        },
    )
    return active_names


def agent_tool_definitions(active_names: set[str]) -> list[dict[str, Any]]:
    return [
        tool
        for tool in AGENT_TOOL_DEFINITIONS
        if str(tool["name"]) in active_names
    ]


def activate_agent_tool_names(active_names: set[str], requested_names: Iterable[str]) -> list[str]:
    newly_active: list[str] = []
    for name in requested_names:
        if name in active_names or name not in TOOL_DEFINITION_BY_NAME:
            continue
        active_names.add(name)
        newly_active.append(name)
    return sorted(newly_active)


def tool_search_activation_names(observation: object) -> list[str]:
    if getattr(observation, "kind", None) != "tool_search" or not getattr(observation, "ok", False):
        return []
    matches = getattr(observation, "matches", None)
    if not isinstance(matches, list):
        return []
    names: list[str] = []
    for match in matches:
        if not isinstance(match, dict):
            continue
        name = match.get("name")
        if isinstance(name, str) and name in TOOL_DEFINITION_BY_NAME:
            names.append(name)
    return names


def activate_tools_for_run(
    workspace: RunWorkspace,
    active_names: set[str],
    requested_names: list[str],
    iteration: int,
    *,
    source: str,
) -> list[str]:
    activated = activate_agent_tool_names(active_names, requested_names)
    if activated:
        append_session_event(
            workspace.session_dir,
            "tools_activated",
            {
                "iteration": iteration,
                "source": source,
                "activated": activated,
                "active": len(active_names),
                "total": len(AGENT_TOOL_DEFINITIONS),
            },
        )
    return activated


def activate_tools_from_observations(
    workspace: RunWorkspace,
    active_names: set[str],
    observations: list[Observation],
    iteration: int,
) -> list[str]:
    requested_names: list[str] = []
    for observation in observations:
        requested_names.extend(tool_search_activation_names(observation))
    return activate_tools_for_run(
        workspace,
        active_names,
        requested_names,
        iteration,
        source="tool_search",
    )


def validate_core_agent_tools() -> list[str]:
    return sorted(CORE_AGENT_TOOL_NAMES - TOOL_DEFINITION_BY_NAME.keys())
