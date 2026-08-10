from __future__ import annotations

from typing import Any


MCP_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "mcp_servers",
        "description": "List configured project MCP stdio and Streamable HTTP servers from .mcp.json without starting them or exposing secret values.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_servers": {"type": "integer", "minimum": 1, "maximum": 200, "description": "Maximum servers to return. Defaults to 50."}
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "mcp_tools",
        "description": "Connect to one configured MCP server and list its advertised tools. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "server": {"type": "string", "description": "Exact configured MCP server name."},
                "max_tools": {"type": "integer", "minimum": 1, "maximum": 500, "description": "Maximum tools to return. Defaults to 100."},
                "timeout_ms": {"type": "integer", "minimum": 100, "maximum": 120000, "description": "Per-request timeout. Defaults to 10000."},
            },
            "required": ["server"],
            "additionalProperties": False,
        },
    },
    {
        "name": "mcp_call",
        "description": "Connect to one configured MCP server and call an advertised tool with JSON arguments. Requires approval for every call.",
        "input_schema": {
            "type": "object",
            "properties": {
                "server": {"type": "string", "description": "Exact configured MCP server name."},
                "name": {"type": "string", "description": "Exact tool name advertised by the server."},
                "arguments": {"type": "object", "description": "JSON object passed to the MCP tool."},
                "timeout_ms": {"type": "integer", "minimum": 100, "maximum": 120000, "description": "Per-request timeout. Defaults to 30000."},
                "max_output_chars": {"type": "integer", "minimum": 1, "maximum": 100000, "description": "Maximum result text characters. Defaults to 20000."},
            },
            "required": ["server", "name"],
            "additionalProperties": False,
        },
    },
    {
        "name": "mcp_resources",
        "description": "Connect to one configured MCP server and list its advertised resources. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "server": {"type": "string", "description": "Exact configured MCP server name."},
                "max_resources": {"type": "integer", "minimum": 1, "maximum": 500, "description": "Maximum resources to return. Defaults to 100."},
                "timeout_ms": {"type": "integer", "minimum": 100, "maximum": 120000, "description": "Per-request timeout. Defaults to 10000."},
            },
            "required": ["server"],
            "additionalProperties": False,
        },
    },
    {
        "name": "ListMcpResourcesTool",
        "description": "Claude-compatible alias for listing resources advertised by one configured MCP server.",
        "input_schema": {
            "type": "object",
            "properties": {
                "server": {"type": "string", "description": "Exact configured MCP server name."},
                "max_resources": {"type": "integer", "minimum": 1, "maximum": 500},
                "timeout_ms": {"type": "integer", "minimum": 100, "maximum": 120000},
            },
            "required": ["server"],
            "additionalProperties": False,
        },
    },
    {
        "name": "mcp_read_resource",
        "description": "Read one exact resource URI advertised by a configured MCP server. Text is redacted and bounded; binary blobs are not exposed. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "server": {"type": "string", "description": "Exact configured MCP server name."},
                "uri": {"type": "string", "minLength": 1, "maxLength": 4096, "description": "Exact URI returned by mcp_resources."},
                "timeout_ms": {"type": "integer", "minimum": 100, "maximum": 120000},
                "max_output_chars": {"type": "integer", "minimum": 1, "maximum": 100000},
            },
            "required": ["server", "uri"],
            "additionalProperties": False,
        },
    },
    {
        "name": "ReadMcpResourceTool",
        "description": "Claude-compatible alias for reading one exact MCP resource URI after discovery.",
        "input_schema": {
            "type": "object",
            "properties": {
                "server": {"type": "string", "description": "Exact configured MCP server name."},
                "uri": {"type": "string", "minLength": 1, "maxLength": 4096},
                "timeout_ms": {"type": "integer", "minimum": 100, "maximum": 120000},
                "max_output_chars": {"type": "integer", "minimum": 1, "maximum": 100000},
            },
            "required": ["server", "uri"],
            "additionalProperties": False,
        },
    },
]
