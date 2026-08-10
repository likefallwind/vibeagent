from __future__ import annotations

from types import SimpleNamespace

from .action_tool_aliases import CLAUDE_TOOL_ACTION_ALIASES, tool_name_candidates
from .tool_definitions import AGENT_TOOL_DEFINITIONS
from .workspace_permissions import ProjectPermissions


KNOWN_TOOL_NAMES = tuple(str(tool["name"]) for tool in AGENT_TOOL_DEFINITIONS)


def globally_denied_tool_names(
    permissions: ProjectPermissions,
) -> frozenset[str]:
    denied: set[str] = set()
    for rule in permissions.rules:
        if rule.effect != "deny" or rule.specifier is not None:
            continue
        if rule.tool.startswith("mcp__"):
            denied.add(_normalize_mcp_restriction(rule.tool))
            continue
        matched = {
            name
            for name in KNOWN_TOOL_NAMES
            if rule.tool
            in tool_name_candidates(
                name,
                SimpleNamespace(type=CLAUDE_TOOL_ACTION_ALIASES.get(name, name)),
            )
        }
        denied.update(matched or {rule.tool})
    return frozenset(denied)


def _normalize_mcp_restriction(name: str) -> str:
    return name if name.count("__") != 1 else f"{name}__*"


__all__ = ["globally_denied_tool_names"]
