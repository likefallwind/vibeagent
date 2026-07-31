from __future__ import annotations

from typing import Any


CLAUDE_PROCESS_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "Bash",
        "description": "Claude-compatible alias for running a shell command after approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "description": {"type": "string"},
                "timeout": {
                    "type": "integer",
                    "minimum": 100,
                    "maximum": 600000,
                },
                "max_output_chars": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 50000,
                },
                "run_in_background": {
                    "type": "boolean",
                },
                "cwd": {
                    "type": "string",
                },
                "extract_output_contexts": {"type": "boolean"},
                "extract_output_diagnostics": {"type": "boolean"},
                "context_lines": {"type": "integer", "minimum": 0, "maximum": 500},
                "max_diagnostics": {"type": "integer", "minimum": 1, "maximum": 200},
                "max_contexts": {"type": "integer", "minimum": 1, "maximum": 100},
                "max_bytes_per_context": {"type": "integer", "minimum": 1000, "maximum": 200000},
            },
            "required": ["command"],
            "additionalProperties": False,
        },
    },
    {
        "name": "BashOutput",
        "description": "Claude-compatible alias for reading recent stdout/stderr from a background command.",
        "input_schema": {
            "type": "object",
            "properties": {
                "bash_id": {"type": "string"},
                "max_output_chars": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 50000,
                    "description": "Optional maximum characters to keep for each output stream.",
                },
                "filter": {
                    "type": "string",
                    "description": "Optional regex used to keep only matching output lines.",
                },
            },
            "required": ["bash_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "KillBash",
        "description": "Claude-compatible alias for stopping a background command after approval.",
        "input_schema": {
            "type": "object",
            "properties": {"bash_id": {"type": "string"}},
            "required": ["bash_id"],
            "additionalProperties": False,
        },
    },
]
