from __future__ import annotations

import json
from typing import Any

from .action_parsing_helpers import ActionParseError, parse_optional_positive_int
from .mcp_config import MCP_NAME_PATTERN
from .types import (
    McpCallAction,
    McpReadResourceAction,
    McpResourcesAction,
    McpServersAction,
    McpToolsAction,
)


MCP_ACTION_TYPES = {
    "mcp_servers",
    "mcp_tools",
    "mcp_call",
    "mcp_resources",
    "mcp_read_resource",
}


def parse_mcp_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in MCP_ACTION_TYPES:
        return None
    if action_type == "mcp_servers":
        maximum = parse_optional_positive_int(value.get("max_servers", 50), "max_servers", raw, maximum=200) or 50
        return McpServersAction(type="mcp_servers", max_servers=maximum)

    server = _parse_name(value.get("server"), "server", raw)
    timeout_ms = parse_optional_positive_int(value.get("timeout_ms"), "timeout_ms", raw, maximum=120_000)
    if timeout_ms is not None and timeout_ms < 100:
        raise ActionParseError("timeout_ms must be at least 100.", raw)
    if action_type == "mcp_tools":
        max_tools = parse_optional_positive_int(value.get("max_tools", 100), "max_tools", raw, maximum=500) or 100
        return McpToolsAction(type="mcp_tools", server=server, max_tools=max_tools, timeout_ms=timeout_ms or 10_000)
    if action_type == "mcp_resources":
        max_resources = parse_optional_positive_int(
            value.get("max_resources", 100),
            "max_resources",
            raw,
            maximum=500,
        ) or 100
        max_templates = parse_optional_positive_int(
            value.get("max_templates", 100),
            "max_templates",
            raw,
            maximum=500,
        ) or 100
        return McpResourcesAction(
            type="mcp_resources",
            server=server,
            max_resources=max_resources,
            max_templates=max_templates,
            timeout_ms=timeout_ms or 10_000,
        )
    if action_type == "mcp_read_resource":
        uri = _parse_uri(value.get("uri"), raw)
        max_output_chars = parse_optional_positive_int(
            value.get("max_output_chars", 20_000),
            "max_output_chars",
            raw,
            maximum=100_000,
        ) or 20_000
        return McpReadResourceAction(
            type="mcp_read_resource",
            server=server,
            uri=uri,
            timeout_ms=timeout_ms or 30_000,
            max_output_chars=max_output_chars,
        )

    name = _parse_name(value.get("name"), "name", raw)
    arguments = value.get("arguments", {})
    if not isinstance(arguments, dict):
        raise ActionParseError("mcp_call action arguments must be an object.", raw)
    try:
        serialized_arguments = json.dumps(arguments, ensure_ascii=False)
    except (TypeError, ValueError) as error:
        raise ActionParseError(f"mcp_call action arguments must be JSON serializable: {error}", raw) from error
    if len(serialized_arguments) > 50_000:
        raise ActionParseError("mcp_call action arguments exceed 50000 characters.", raw)
    max_output_chars = parse_optional_positive_int(
        value.get("max_output_chars", 20_000), "max_output_chars", raw, maximum=100_000
    ) or 20_000
    return McpCallAction(
        type="mcp_call",
        server=server,
        name=name,
        arguments=arguments,
        timeout_ms=timeout_ms or 30_000,
        max_output_chars=max_output_chars,
    )


def _parse_name(value: object, field: str, raw: str) -> str:
    if not isinstance(value, str) or not MCP_NAME_PATTERN.fullmatch(value):
        raise ActionParseError(
            f"MCP {field} must use 1-64 letters, digits, dots, underscores, or hyphens.", raw
        )
    return value


def _parse_uri(value: object, raw: str) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > 4_096
        or any(ord(character) < 32 for character in value)
    ):
        raise ActionParseError(
            "MCP resource uri must be non-empty, contain no control characters, and use at most 4096 characters.",
            raw,
        )
    return value
