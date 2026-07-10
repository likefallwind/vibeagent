from __future__ import annotations

from typing import Any


MCP_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "mcp_servers",
        "description": "List configured project MCP stdio servers from .mcp.json without starting them or exposing environment values.",
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
        "description": "Start one configured MCP stdio server and list its advertised tools. Requires approval.",
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
        "description": "Start one configured MCP stdio server and call an advertised tool with JSON arguments. Requires approval for every call.",
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
]
