from __future__ import annotations

from dataclasses import dataclass
import json

from .mcp_scope_store import McpScope, validate_mcp_scope


MCP_USAGE = (
    "Usage: /mcp [list|get <name>|"
    "add [--transport stdio|http] [--scope local|project|user] "
    "[--env KEY=value] [--header NAME:value] [--replace] <name> -- <command-or-url> [args...]|"
    "add-json [--scope local|project|user] [--replace] <name> '<json>'|"
    "remove [--scope local|project|user] <name>]"
)


@dataclass(frozen=True)
class McpAddOptions:
    name: str
    scope: McpScope
    transport: str
    environment: dict[str, str]
    headers: dict[str, str]
    replace: bool
    target: tuple[str, ...]


def parse_mcp_add(parts: list[str]) -> McpAddOptions:
    if "--" not in parts:
        raise ValueError("/mcp add requires -- before the command or URL.")
    separator = parts.index("--")
    option_parts = parts[:separator]
    target = tuple(parts[separator + 1 :])
    if not target:
        raise ValueError("/mcp add requires a command or URL after --.")

    name: str | None = None
    scope: McpScope = "local"
    transport = "stdio"
    environment: dict[str, str] = {}
    headers: dict[str, str] = {}
    replace = False
    index = 0
    while index < len(option_parts):
        token = option_parts[index]
        if token in {
            "--scope",
            "-s",
            "--transport",
            "-t",
            "--env",
            "-e",
            "--header",
            "-H",
        }:
            if index + 1 >= len(option_parts):
                raise ValueError(f"{token} requires a value.")
            value = option_parts[index + 1]
            index += 2
            if token in {"--scope", "-s"}:
                scope = validate_mcp_scope(value)
            elif token in {"--transport", "-t"}:
                if value not in {"stdio", "http"}:
                    raise ValueError("MCP transport must be stdio or http.")
                transport = value
            elif token in {"--env", "-e"}:
                key, item = _split_assignment(value, "environment", "=")
                environment[key] = item
            else:
                key, item = _split_assignment(value, "header", ":")
                headers[key] = item
            continue
        if token == "--replace":
            replace = True
            index += 1
            continue
        if token.startswith("-"):
            raise ValueError(f"Unknown /mcp add option: {token}")
        if name is not None:
            raise ValueError("/mcp add accepts exactly one server name.")
        name = token
        index += 1
    if name is None:
        raise ValueError("/mcp add requires a server name.")
    return McpAddOptions(
        name,
        scope,
        transport,
        environment,
        headers,
        replace,
        target,
    )


def server_from_mcp_add(options: McpAddOptions) -> dict[str, object]:
    if options.transport == "http":
        if len(options.target) != 1:
            raise ValueError("HTTP MCP add accepts exactly one URL after --.")
        if options.environment:
            raise ValueError("HTTP MCP add does not accept --env; use --header.")
        server: dict[str, object] = {"type": "http", "url": options.target[0]}
        if options.headers:
            server["headers"] = options.headers
        return server
    if options.headers:
        raise ValueError("stdio MCP add does not accept --header; use --env.")
    server = {
        "type": "stdio",
        "command": options.target[0],
        "args": list(options.target[1:]),
    }
    if options.environment:
        server["env"] = options.environment
    return server


def parse_mcp_add_json(
    parts: list[str],
) -> tuple[str, McpScope, bool, dict[str, object]]:
    remaining, scope, replace = _extract_simple_options(parts, allow_replace=True)
    if len(remaining) != 2:
        raise ValueError("/mcp add-json requires one name and one JSON object.")
    payload = json.loads(remaining[1])
    if not isinstance(payload, dict):
        raise ValueError("MCP server JSON must be an object.")
    return remaining[0], scope, replace, payload


def parse_mcp_remove(parts: list[str]) -> tuple[str, McpScope]:
    remaining, scope, _replace = _extract_simple_options(parts, allow_replace=False)
    if len(remaining) != 1:
        raise ValueError("/mcp remove requires exactly one server name.")
    return remaining[0], scope


def _extract_simple_options(
    parts: list[str],
    *,
    allow_replace: bool,
) -> tuple[list[str], McpScope, bool]:
    remaining: list[str] = []
    scope: McpScope = "local"
    replace = False
    index = 0
    while index < len(parts):
        token = parts[index]
        if token in {"--scope", "-s"}:
            if index + 1 >= len(parts):
                raise ValueError(f"{token} requires a value.")
            scope = validate_mcp_scope(parts[index + 1])
            index += 2
            continue
        if token == "--replace" and allow_replace:
            replace = True
            index += 1
            continue
        if token.startswith("-"):
            raise ValueError(f"Unknown MCP option: {token}")
        remaining.append(token)
        index += 1
    return remaining, scope, replace


def _split_assignment(value: str, label: str, separator: str) -> tuple[str, str]:
    if separator not in value:
        raise ValueError(f"MCP {label} must use NAME{separator}value syntax.")
    key, item = value.split(separator, 1)
    if not key:
        raise ValueError(f"MCP {label} name must not be empty.")
    return key, item


__all__ = [
    "MCP_USAGE",
    "McpAddOptions",
    "parse_mcp_add",
    "parse_mcp_add_json",
    "parse_mcp_remove",
    "server_from_mcp_add",
]
