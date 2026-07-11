from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
from typing import Any

from .agent_runtime_utils import append_session_event
from .tool_catalog_core import APPROVAL_REQUIRED_TOOL_NAMES
from .tool_definitions import AGENT_TOOL_DEFINITIONS
from .types import ApprovalPolicy, Observation, ToolSearchAction
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
        "mcp_servers",
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
        "todo_read",
        "todo_write",
        "tool_search",
        "update_plan",
        "web_fetch",
        "write_file",
    }
)

TOOL_DEFINITION_BY_NAME = {
    str(tool["name"]): tool
    for tool in AGENT_TOOL_DEFINITIONS
}


def initial_agent_tool_names() -> set[str]:
    return set(CORE_AGENT_TOOL_NAMES)


def tool_available_for_policy(
    name: str,
    approval_policy: ApprovalPolicy,
    excluded_names: frozenset[str] = frozenset(),
) -> bool:
    return name not in excluded_names and (
        approval_policy != "plan" or name not in APPROVAL_REQUIRED_TOOL_NAMES
    )


def prepare_action_for_policy(action: object, approval_policy: ApprovalPolicy) -> object:
    if approval_policy == "plan" and isinstance(action, ToolSearchAction):
        return replace(action, approval_required=False)
    return action


def initialize_agent_tools(
    workspace: RunWorkspace,
    approval_policy: ApprovalPolicy = "ask",
    excluded_names: frozenset[str] = frozenset(),
) -> set[str]:
    active_names = {
        name for name in initial_agent_tool_names()
        if tool_available_for_policy(name, approval_policy, excluded_names)
    }
    append_session_event(
        workspace.session_dir,
        "tool_catalog_initialized",
        {
            "active": len(active_names),
            "total": len(AGENT_TOOL_DEFINITIONS),
            "approval_policy": approval_policy,
            "tools": sorted(active_names),
        },
    )
    return active_names


def agent_tool_definitions(
    active_names: set[str],
    approval_policy: ApprovalPolicy = "ask",
    excluded_names: frozenset[str] = frozenset(),
) -> list[dict[str, Any]]:
    return [
        tool
        for tool in AGENT_TOOL_DEFINITIONS
        if str(tool["name"]) in active_names
        and tool_available_for_policy(str(tool["name"]), approval_policy, excluded_names)
    ]


def activate_agent_tool_names(
    active_names: set[str],
    requested_names: Iterable[str],
    approval_policy: ApprovalPolicy = "ask",
    excluded_names: frozenset[str] = frozenset(),
) -> list[str]:
    newly_active: list[str] = []
    for name in requested_names:
        if (
            name in active_names
            or name not in TOOL_DEFINITION_BY_NAME
            or not tool_available_for_policy(name, approval_policy, excluded_names)
        ):
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
    approval_policy: ApprovalPolicy = "ask",
) -> list[str]:
    activated = activate_agent_tool_names(active_names, requested_names, approval_policy)
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
    approval_policy: ApprovalPolicy = "ask",
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
        approval_policy=approval_policy,
    )


def validate_core_agent_tools() -> list[str]:
    return sorted(CORE_AGENT_TOOL_NAMES - TOOL_DEFINITION_BY_NAME.keys())
