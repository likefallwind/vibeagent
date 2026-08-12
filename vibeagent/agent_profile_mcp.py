from __future__ import annotations

from dataclasses import replace

from .managed_customization import (
    managed_mcp_path,
    read_managed_customization_policy,
)
from .mcp_config import read_mcp_server_configs, validate_mcp_server_definition
from .workspace_core import RunWorkspace


def with_agent_mcp_servers(
    workspace: RunWorkspace,
    entries: tuple[object, ...],
    *,
    source: str,
) -> RunWorkspace:
    if not entries:
        return workspace
    existing = {config.name: config for config in read_mcp_server_configs(workspace)}
    managed_exclusive = managed_mcp_path().exists() or managed_mcp_path().is_symlink()
    plugin_only = read_managed_customization_policy(workspace).locks("mcp")
    inline = []
    for entry in entries:
        if isinstance(entry, str):
            if entry not in existing:
                raise ValueError(
                    f"Agent profile references unavailable MCP server {entry!r}."
                )
            continue
        if not isinstance(entry, dict) or len(entry) != 1:
            raise ValueError("Agent profile MCP server entry is invalid.")
        if managed_exclusive:
            raise ValueError(
                "Agent profile inline MCP servers are disabled by managed-mcp.json."
            )
        if plugin_only and not source.startswith("managed:"):
            raise ValueError(
                "Agent profile inline MCP servers must come from a managed agent "
                "when strictPluginOnlyCustomization locks mcp."
            )
        name, definition = next(iter(entry.items()))
        if name in existing or any(config.name == name for config in inline):
            raise ValueError(
                f"Agent profile inline MCP server {name!r} conflicts with an existing server."
            )
        if not isinstance(name, str) or not isinstance(definition, dict):
            raise ValueError("Agent profile inline MCP server entry is invalid.")
        inline.append(
            validate_mcp_server_definition(
                workspace,
                name,
                definition,
                source,
            )
        )
    if not inline:
        return workspace
    return replace(
        workspace,
        profile_mcp_server_configs=(
            *workspace.profile_mcp_server_configs,
            *inline,
        ),
    )


__all__ = ["with_agent_mcp_servers"]
