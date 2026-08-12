from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from typing import Any

from .action_tool_aliases import CLAUDE_MCP_TOOL_NAME_PATTERN, tool_name_is_restricted
from .agent_core_tools import CORE_AGENT_TOOL_NAMES
from .agent_runtime_utils import append_session_event
from .scheduled_task_store import CRON_TOOL_NAMES, scheduled_tasks_enabled
from .tool_catalog_core import tool_name_requires_approval
from .tool_definitions import AGENT_TOOL_DEFINITIONS
from .types import ApprovalPolicy, Observation, ToolSearchAction
from .workspace_core import RunWorkspace

TOOL_DEFINITION_BY_NAME = {
    str(tool["name"]): tool
    for tool in AGENT_TOOL_DEFINITIONS
}
TEAM_TOOL_NAMES = frozenset({"TeamCreate", "TeamDelete"})
_DYNAMIC_TOOL_DEFINITION_BY_NAME: dict[str, dict[str, Any]] = {}


def clear_dynamic_tool_definitions() -> None:
    _DYNAMIC_TOOL_DEFINITION_BY_NAME.clear()


@dataclass(frozen=True)
class ToolVisibilityPolicy:
    approval_policy: ApprovalPolicy = "ask"
    excluded_names: frozenset[str] = frozenset()
    allowed_names: frozenset[str] | None = None

    def allows(self, name: str) -> bool:
        plan_transition_visible = (
            name == "ExitPlanMode" if self.approval_policy == "plan" else name == "EnterPlanMode"
        )
        if name in {"EnterPlanMode", "ExitPlanMode"} and not plan_transition_visible:
            return False
        return (
            not tool_name_is_restricted(self.excluded_names, name)
            and (self.allowed_names is None or name in self.allowed_names)
            and (
                self.approval_policy != "plan"
                or name == "ExitPlanMode"
                or not tool_name_requires_approval(name)
            )
        )


def _visibility_policy(
    approval_policy: ApprovalPolicy,
    excluded_names: frozenset[str],
    allowed_names: frozenset[str] | None = None,
) -> ToolVisibilityPolicy:
    effective_exclusions = _effective_excluded_names(excluded_names)
    return ToolVisibilityPolicy(
        approval_policy=approval_policy,
        excluded_names=effective_exclusions,
        allowed_names=allowed_names,
    )


def _effective_excluded_names(excluded_names: frozenset[str]) -> frozenset[str]:
    effective = excluded_names
    if not scheduled_tasks_enabled():
        effective = effective | CRON_TOOL_NAMES
    effective = effective | TEAM_TOOL_NAMES
    return effective


def initial_agent_tool_names() -> set[str]:
    return set(CORE_AGENT_TOOL_NAMES)


def tool_available_for_policy(
    name: str,
    approval_policy: ApprovalPolicy,
    excluded_names: frozenset[str] = frozenset(),
    allowed_names: frozenset[str] | None = None,
) -> bool:
    return _visibility_policy(approval_policy, excluded_names, allowed_names).allows(name)


def prepare_action_for_policy(action: object, approval_policy: ApprovalPolicy) -> object:
    if approval_policy == "plan" and isinstance(action, ToolSearchAction):
        return replace(action, approval_required=False)
    return action


def prepare_action_for_visibility(
    action: object,
    excluded_names: frozenset[str] = frozenset(),
    allowed_names: frozenset[str] | None = None,
) -> object:
    if not isinstance(action, ToolSearchAction):
        return action
    return replace(
        action,
        excluded_tool_names=_effective_excluded_names(excluded_names),
        allowed_tool_names=allowed_names,
    )


def initialize_agent_tools(
    workspace: RunWorkspace,
    approval_policy: ApprovalPolicy = "ask",
    excluded_names: frozenset[str] = frozenset(),
    allowed_names: frozenset[str] | None = None,
) -> set[str]:
    clear_dynamic_tool_definitions()
    policy = _visibility_policy(approval_policy, excluded_names, allowed_names)
    active_names = {
        name for name in initial_agent_tool_names()
        if policy.allows(name)
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
    allowed_names: frozenset[str] | None = None,
) -> list[dict[str, Any]]:
    policy = _visibility_policy(approval_policy, excluded_names, allowed_names)
    definitions = [
        tool
        for tool in AGENT_TOOL_DEFINITIONS
        if str(tool["name"]) in active_names
        and policy.allows(str(tool["name"]))
    ]
    definitions.extend(
        tool
        for name, tool in sorted(_DYNAMIC_TOOL_DEFINITION_BY_NAME.items())
        if name in active_names and policy.allows(name)
    )
    return definitions


def activate_agent_tool_names(
    active_names: set[str],
    requested_names: Iterable[str],
    approval_policy: ApprovalPolicy = "ask",
    excluded_names: frozenset[str] = frozenset(),
    allowed_names: frozenset[str] | None = None,
) -> list[str]:
    policy = _visibility_policy(approval_policy, excluded_names, allowed_names)
    newly_active: list[str] = []
    for name in requested_names:
        if (
            name in active_names
            or _tool_definition_for_name(name) is None
            or not policy.allows(name)
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


def mcp_tools_activation_names(observation: object) -> list[str]:
    if getattr(observation, "kind", None) != "mcp_tools" or not getattr(observation, "ok", False):
        return []
    server = getattr(observation, "server", None)
    tools = getattr(observation, "tools", None)
    if not isinstance(server, str) or not isinstance(tools, list):
        return []
    names: list[str] = []
    for tool in tools:
        tool_name = getattr(tool, "name", None)
        if not isinstance(tool_name, str) or not tool_name:
            continue
        name = f"mcp__{server}__{tool_name}"
        if not CLAUDE_MCP_TOOL_NAME_PATTERN.fullmatch(name):
            continue
        _DYNAMIC_TOOL_DEFINITION_BY_NAME[name] = _mcp_tool_definition(server, tool)
        names.append(name)
    return names


def mcp_resources_activation_names(observation: object) -> list[str]:
    if (
        getattr(observation, "kind", None) != "mcp_resources"
        or not getattr(observation, "ok", False)
    ):
        return []
    return ["mcp_read_resource", "ReadMcpResourceTool"]


def background_task_activation_names(observation: object) -> list[str]:
    if (
        getattr(observation, "kind", None) == "delegate_task"
        and getattr(observation, "background", False)
        and getattr(observation, "running", False)
    ):
        return ["TaskOutput", "TaskStop"]
    return []


def worktree_activation_names(observation: object) -> list[str]:
    if getattr(observation, "kind", None) == "enter_worktree" and getattr(observation, "ok", False):
        return ["ExitWorktree"]
    return []


def scheduled_task_activation_names(observation: object) -> list[str]:
    if getattr(observation, "kind", None) == "cron_create" and getattr(observation, "ok", False):
        return ["CronList", "CronDelete"]
    return []


def activate_tools_for_run(
    workspace: RunWorkspace,
    active_names: set[str],
    requested_names: list[str],
    iteration: int,
    *,
    source: str,
    approval_policy: ApprovalPolicy = "ask",
    excluded_names: frozenset[str] = frozenset(),
    allowed_names: frozenset[str] | None = None,
) -> list[str]:
    activated = activate_agent_tool_names(
        active_names, requested_names, approval_policy, excluded_names, allowed_names
    )
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
    excluded_names: frozenset[str] = frozenset(),
    allowed_names: frozenset[str] | None = None,
) -> list[str]:
    activated: list[str] = []
    requested_names: list[str] = []
    for observation in observations:
        requested_names.extend(tool_search_activation_names(observation))
        requested_names.extend(scheduled_task_activation_names(observation))
    activated.extend(
        activate_tools_for_run(
            workspace,
            active_names,
            requested_names,
            iteration,
            source="tool_search",
            approval_policy=approval_policy,
            excluded_names=excluded_names,
            allowed_names=allowed_names,
        )
    )

    requested_names = []
    for observation in observations:
        requested_names.extend(mcp_tools_activation_names(observation))
        requested_names.extend(mcp_resources_activation_names(observation))
    activated.extend(
        activate_tools_for_run(
            workspace,
            active_names,
            requested_names,
            iteration,
            source="mcp_discovery",
            approval_policy=approval_policy,
            excluded_names=excluded_names,
            allowed_names=allowed_names,
        )
    )

    requested_names = []
    for observation in observations:
        requested_names.extend(background_task_activation_names(observation))
    activated.extend(
        activate_tools_for_run(
            workspace,
            active_names,
            requested_names,
            iteration,
            source="background_task",
            approval_policy=approval_policy,
            excluded_names=excluded_names,
            allowed_names=allowed_names,
        )
    )
    requested_names = []
    for observation in observations:
        requested_names.extend(worktree_activation_names(observation))
    activated.extend(
        activate_tools_for_run(
            workspace,
            active_names,
            requested_names,
            iteration,
            source="worktree",
            approval_policy=approval_policy,
            excluded_names=excluded_names,
            allowed_names=allowed_names,
        )
    )
    return sorted(activated)


def validate_core_agent_tools() -> list[str]:
    return sorted(CORE_AGENT_TOOL_NAMES - TOOL_DEFINITION_BY_NAME.keys())


def _tool_definition_for_name(name: str) -> dict[str, Any] | None:
    return TOOL_DEFINITION_BY_NAME.get(name) or _DYNAMIC_TOOL_DEFINITION_BY_NAME.get(name)


def _mcp_tool_definition(server: str, tool: object) -> dict[str, Any]:
    tool_name = str(getattr(tool, "name", ""))
    description = str(getattr(tool, "description", "") or "")
    schema = getattr(tool, "input_schema", {"type": "object"})
    if not isinstance(schema, dict):
        schema = {"type": "object"}
    return {
        "name": f"mcp__{server}__{tool_name}",
        "description": description or f"Claude-compatible MCP tool alias for {server}/{tool_name}. Requires approval.",
        "input_schema": dict(schema),
    }
