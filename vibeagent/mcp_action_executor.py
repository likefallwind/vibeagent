from __future__ import annotations

import json
import shlex
from pathlib import Path
from typing import Any

from .command_safety import get_blocked_command_reason
from .mcp_config import McpServerConfig, get_mcp_server_config, mcp_config_paths, read_mcp_server_configs, safe_mcp_endpoint
from .mcp_http import McpHttpClient
from .mcp_protocol import MCP_STDIO_PROTOCOL_VERSION
from .mcp_resource_runtime import mcp_resource_result_text, normalize_mcp_resource
from .mcp_stdio import McpStdioClient
from .redaction import redact_jsonable_payload, redact_sensitive_text
from .types import (
    McpCallAction,
    McpCallObservation,
    McpReadResourceAction,
    McpReadResourceObservation,
    McpResourcesAction,
    McpResourcesObservation,
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
            config_path = ", ".join(
                dict.fromkeys(config.config_path for config in configs)
            )
            if not config_path:
                paths = mcp_config_paths(workspace)
                config_path = ", ".join(
                    _config_path_label(workspace, path) for path in paths
                )
                if not config_path:
                    config_path = "none" if workspace.strict_mcp_config else ".mcp.json"
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
                        transport=config.transport,
                        endpoint=safe_mcp_endpoint(config),
                        header_keys=sorted((config.headers or {}).keys()),
                        protocol_version=config.protocol_version if config.transport == "http" else MCP_STDIO_PROTOCOL_VERSION,
                    )
                    for config in shown
                ],
                total=len(configs),
                truncated=len(configs) > len(shown),
                config_path=config_path,
                message=f"Found {len(configs)} configured MCP server(s).",
            )
        except (OSError, ValueError) as error:
            return McpServersObservation(
                kind="mcp_servers", ok=False, servers=[], total=0, truncated=False, config_path=".mcp.json", message=str(error)
            )

    if isinstance(action, McpToolsAction):
        try:
            config = _safe_server_config(workspace, action.server)
            with _mcp_client(workspace, config, action.timeout_ms) as client:
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

    if isinstance(action, McpResourcesAction):
        try:
            config = _safe_server_config(workspace, action.server)
            with _mcp_client(workspace, config, action.timeout_ms) as client:
                raw_resources, total, truncated = client.list_resources(
                    action.max_resources
                )
            resources = [normalize_mcp_resource(item) for item in raw_resources]
            uris = [resource.uri for resource in resources]
            if len(set(uris)) != len(uris):
                raise ValueError("MCP resource catalog contains duplicate URIs.")
            return McpResourcesObservation(
                kind="mcp_resources",
                ok=True,
                server=action.server,
                resources=resources,
                total=total,
                truncated=truncated,
                timeout_ms=action.timeout_ms,
                error=None,
                message=f"Listed {len(resources)} MCP resource(s) from {action.server}.",
            )
        except (OSError, RuntimeError, TimeoutError, ValueError) as error:
            return McpResourcesObservation(
                kind="mcp_resources",
                ok=False,
                server=action.server,
                resources=[],
                total=0,
                truncated=False,
                timeout_ms=action.timeout_ms,
                error=str(error),
                message=f"Could not list MCP resources from {action.server}: {error}",
            )

    if isinstance(action, McpReadResourceAction):
        try:
            config = _safe_server_config(workspace, action.server)
            with _mcp_client(workspace, config, action.timeout_ms) as client:
                raw_resources, _, truncated_catalog = client.list_resources(500)
                advertised = {
                    resource.uri
                    for resource in map(normalize_mcp_resource, raw_resources)
                }
                if truncated_catalog:
                    raise ValueError(
                        "MCP resource catalog exceeds the safe discovery limit; narrow server resources before reading."
                    )
                if action.uri not in advertised:
                    raise ValueError(
                        f"MCP resource {action.uri!r} was not advertised by server {action.server!r}."
                    )
                result = client.read_resource(action.uri)
            raw_output, mime_types = mcp_resource_result_text(result, action.uri)
            output = redact_sensitive_text(raw_output)
            truncated = len(output) > action.max_output_chars
            output = output[: action.max_output_chars]
            return McpReadResourceObservation(
                kind="mcp_read_resource",
                ok=True,
                server=action.server,
                uri=action.uri,
                output=output,
                mime_types=mime_types,
                truncated=truncated,
                max_output_chars=action.max_output_chars,
                timeout_ms=action.timeout_ms,
                error=None,
                message=f"Read MCP resource {action.server}/{action.uri}.",
            )
        except (OSError, RuntimeError, TimeoutError, ValueError) as error:
            return McpReadResourceObservation(
                kind="mcp_read_resource",
                ok=False,
                server=action.server,
                uri=action.uri,
                output="",
                mime_types=[],
                truncated=False,
                max_output_chars=action.max_output_chars,
                timeout_ms=action.timeout_ms,
                error=str(error),
                message=f"Could not read MCP resource {action.server}/{action.uri}: {error}",
            )

    if isinstance(action, McpCallAction):
        try:
            config = _safe_server_config(workspace, action.server)
            with _mcp_client(workspace, config, action.timeout_ms) as client:
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
                arguments=_redacted_arguments(action.arguments),
            )
        except (OSError, RuntimeError, TimeoutError, ValueError) as error:
            return McpCallObservation(
                kind="mcp_call", ok=False, server=action.server, name=action.name, output="", is_error=True,
                truncated=False, max_output_chars=action.max_output_chars, timeout_ms=action.timeout_ms,
                error=str(error), message=f"Could not call MCP tool {action.server}/{action.name}: {error}",
                arguments=_redacted_arguments(action.arguments),
            )
    return None


def _safe_server_config(workspace: RunWorkspace, name: str) -> McpServerConfig:
    config = get_mcp_server_config(workspace, name)
    if config.transport == "stdio":
        expanded = config.argv
        safety_argv = [Path(expanded[0]).name, *expanded[1:]]
        blocked = get_blocked_command_reason(shlex.join(safety_argv))
        if blocked:
            raise ValueError(f"MCP server command is blocked: {blocked}")
    return config


def _mcp_client(workspace: RunWorkspace, config: McpServerConfig, timeout_ms: int):
    if config.transport == "http":
        return McpHttpClient(config, timeout_ms)
    return McpStdioClient(workspace, config, timeout_ms)


def _redacted_arguments(arguments: dict[str, Any]) -> dict[str, object]:
    redacted = redact_jsonable_payload(arguments)
    return redacted if isinstance(redacted, dict) else {}


def _config_path_label(workspace: RunWorkspace, path: Path) -> str:
    try:
        return path.resolve().relative_to(workspace.root).as_posix()
    except ValueError:
        return path.resolve().as_posix()


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
