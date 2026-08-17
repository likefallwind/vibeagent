from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
import shlex

from .mcp_config import (
    get_mcp_server_config,
    read_mcp_server_configs,
    safe_mcp_endpoint,
    validate_mcp_server_definition,
)
from .mcp_command_parsing import (
    MCP_USAGE,
    parse_mcp_add,
    parse_mcp_add_json,
    parse_mcp_remove,
    server_from_mcp_add,
)
from .mcp_scope_store import (
    McpScope,
    mcp_scope_source,
    remove_mcp_scope_server,
    write_mcp_scope_server,
)
from .workspace_core import create_local_workspace


@dataclass(frozen=True)
class McpCommandResult:
    text: str
    changed: bool = False


def handle_mcp_command(project_root: Path, argument: str | None) -> McpCommandResult:
    try:
        parts = shlex.split(argument or "")
    except ValueError as error:
        return McpCommandResult(f"{MCP_USAGE}\nError: {error}")
    return handle_mcp_command_parts(project_root, parts)


def handle_mcp_command_parts(
    project_root: Path,
    parts: Sequence[str],
) -> McpCommandResult:
    values = list(parts)
    try:
        if not values or values in (["list"], ["ls"]):
            return McpCommandResult(_format_mcp_list(project_root))
        operation = values[0]
        if operation == "get" and len(values) == 2:
            return McpCommandResult(_format_mcp_details(project_root, values[1]))
        if operation == "add":
            options = parse_mcp_add(values[1:])
            server = server_from_mcp_add(options)
            _validate_and_write(project_root, options.name, options.scope, server, options.replace)
            return McpCommandResult(
                f"Added MCP server {options.name} at {options.scope} scope.",
                changed=True,
            )
        if operation == "add-json":
            name, scope, replace, server = parse_mcp_add_json(values[1:])
            _validate_and_write(project_root, name, scope, server, replace)
            return McpCommandResult(
                f"Added MCP server {name} at {scope} scope.",
                changed=True,
            )
        if operation in {"remove", "rm"}:
            name, scope = parse_mcp_remove(values[1:])
            remove_mcp_scope_server(project_root, scope, name)
            return McpCommandResult(
                f"Removed MCP server {name} from {scope} scope.",
                changed=True,
            )
        return McpCommandResult(MCP_USAGE)
    except (OSError, ValueError) as error:
        return McpCommandResult(f"{MCP_USAGE}\nError: {error}")


def _format_mcp_list(project_root: Path) -> str:
    workspace = create_local_workspace(project_root, "local-mcp-list")
    configs = read_mcp_server_configs(workspace)
    if not configs:
        return "No MCP servers configured."
    lines = [f"MCP servers ({len(configs)}):"]
    for config in configs:
        lines.append(
            f"- {config.name} [{_scope_from_source(config.config_path)}, "
            f"{config.transport}] {config.config_path}"
        )
    return "\n".join(lines)


def _format_mcp_details(project_root: Path, name: str) -> str:
    workspace = create_local_workspace(project_root, "local-mcp-get")
    config = get_mcp_server_config(workspace, name)
    lines = [
        f"MCP server {config.name}:",
        f"  scope: {_scope_from_source(config.config_path)}",
        f"  source: {config.config_path}",
        f"  transport: {config.transport}",
    ]
    if config.transport == "stdio":
        lines.extend(
            [
                f"  command: {config.command}",
                f"  args: {len(config.args)}",
                f"  cwd: {config.cwd}",
                f"  env: {', '.join(sorted(config.env)) or 'none'}",
            ]
        )
    else:
        lines.extend(
            [
                f"  endpoint: {safe_mcp_endpoint(config)}",
                f"  headers: {', '.join(sorted(config.headers or {})) or 'none'}",
                f"  protocol: {config.protocol_version}",
            ]
        )
    return "\n".join(lines)


def _validate_and_write(
    project_root: Path,
    name: str,
    scope: McpScope,
    server: dict[str, object],
    replace: bool,
) -> None:
    workspace = create_local_workspace(project_root, "local-mcp-add")
    validate_mcp_server_definition(
        workspace,
        name,
        server,
        mcp_scope_source(project_root, scope),
    )
    write_mcp_scope_server(
        project_root,
        scope,
        name,
        server,
        replace_existing=replace,
    )


def _scope_from_source(source: str) -> str:
    if source == "~/.claude.json#mcpServers":
        return "user"
    if source == "~/.claude.json#projects[current].mcpServers":
        return "local"
    if source == ".mcp.json":
        return "project"
    if source.startswith("plugin:"):
        return "plugin"
    return "explicit"


__all__ = [
    "MCP_USAGE",
    "McpCommandResult",
    "handle_mcp_command",
    "handle_mcp_command_parts",
]
