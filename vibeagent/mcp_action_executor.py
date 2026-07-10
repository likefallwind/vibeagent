from __future__ import annotations

import json
import shlex
from pathlib import Path
from typing import Any

from .command_safety import get_blocked_command_reason
from .mcp_config import get_mcp_server_config, read_mcp_server_configs
from .mcp_stdio import McpStdioClient
from .redaction import redact_sensitive_text
from .types import (
    McpCallAction,
    McpCallObservation,
    McpServerInfo,
    McpServersAction,
    McpServersObservation,
    McpToolInfo,
    McpToolsAction,
    McpToolsObservation,
    Observation,
)
from .workspace_core import RunWorkspace


def execute_mcp_action(workspace: RunWorkspace, action: object) -> Observation | None:
    if isinstance(action, McpServersAction):
        try:
            configs = read_mcp_server_configs(workspace)
            shown = configs[: action.max_servers]
            return McpServersObservation(
                kind="mcp_servers",
                ok=True,
                servers=[
                    McpServerInfo(
                        name=config.name,
                        command=config.command,
                        arg_count=len(config.args),
                        cwd=config.cwd,
                        env_keys=sorted(config.env),
                    )
                    for config in shown
                ],
                total=len(configs),
                truncated=len(configs) > len(shown),
                config_path=".mcp.json",
                message=f"Found {len(configs)} configured MCP server(s).",
            )
        except (OSError, ValueError) as error:
            return McpServersObservation(
                kind="mcp_servers", ok=False, servers=[], total=0, truncated=False, config_path=".mcp.json", message=str(error)
            )

    if isinstance(action, McpToolsAction):
        try:
            config = _safe_server_config(workspace, action.server)
            with McpStdioClient(workspace, config, action.timeout_ms) as client:
                raw_tools, total, truncated = client.list_tools(action.max_tools)
            tools = [_normalize_tool(item) for item in raw_tools]
            return McpToolsObservation(
                kind="mcp_tools",
                ok=True,
                server=action.server,
                tools=tools,
                total=total,
                truncated=truncated,
                timeout_ms=action.timeout_ms,
                error=None,
                message=f"Listed {len(tools)} MCP tool(s) from {action.server}.",
            )
        except (OSError, RuntimeError, TimeoutError, ValueError) as error:
            return McpToolsObservation(
                kind="mcp_tools", ok=False, server=action.server, tools=[], total=0, truncated=False,
                timeout_ms=action.timeout_ms, error=str(error), message=f"Could not list MCP tools from {action.server}: {error}"
            )

    if isinstance(action, McpCallAction):
        try:
            config = _safe_server_config(workspace, action.server)
            with McpStdioClient(workspace, config, action.timeout_ms) as client:
                tools, _, _ = client.list_tools(500)
                if action.name not in {str(tool.get("name")) for tool in tools}:
                    raise ValueError(f"MCP tool {action.name!r} was not advertised by server {action.server!r}.")
                result = client.call_tool(action.name, action.arguments)
            output = redact_sensitive_text(_mcp_result_text(result))
            truncated = len(output) > action.max_output_chars
            output = output[: action.max_output_chars]
            is_error = bool(result.get("isError", False))
            return McpCallObservation(
                kind="mcp_call",
                ok=not is_error,
                server=action.server,
                name=action.name,
                output=output,
                is_error=is_error,
                truncated=truncated,
                max_output_chars=action.max_output_chars,
                timeout_ms=action.timeout_ms,
                error=output if is_error else None,
                message=f"MCP tool {action.server}/{action.name} {'reported an error' if is_error else 'completed'}.",
            )
        except (OSError, RuntimeError, TimeoutError, ValueError) as error:
            return McpCallObservation(
                kind="mcp_call", ok=False, server=action.server, name=action.name, output="", is_error=True,
                truncated=False, max_output_chars=action.max_output_chars, timeout_ms=action.timeout_ms,
                error=str(error), message=f"Could not call MCP tool {action.server}/{action.name}: {error}"
            )
    return None


def _safe_server_config(workspace: RunWorkspace, name: str):
    config = get_mcp_server_config(workspace, name)
    safety_argv = [Path(config.command).name, *config.args]
    blocked = get_blocked_command_reason(shlex.join(safety_argv))
    if blocked:
        raise ValueError(f"MCP server command is blocked: {blocked}")
    return config


def _normalize_tool(item: dict[str, Any]) -> McpToolInfo:
    name = item.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError("MCP tool metadata requires a non-empty name.")
    schema = item.get("inputSchema", {"type": "object"})
    if not isinstance(schema, dict):
        schema = {"type": "object"}
    return McpToolInfo(
        name=name,
        title=str(item.get("title") or ""),
        description=str(item.get("description") or ""),
        input_schema={str(key): value for key, value in schema.items()},
    )


def _mcp_result_text(result: dict[str, Any]) -> str:
    parts: list[str] = []
    content = result.get("content")
    if isinstance(content, list):
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "text" and isinstance(item.get("text"), str):
                parts.append(item["text"])
            else:
                safe_item = {key: value for key, value in item.items() if key not in {"data", "blob"}}
                parts.append(json.dumps(safe_item, ensure_ascii=False))
    structured = result.get("structuredContent")
    if structured is not None:
        parts.append(json.dumps(structured, ensure_ascii=False))
    return "\n".join(parts)
