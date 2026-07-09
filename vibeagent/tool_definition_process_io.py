from __future__ import annotations

from typing import Any


PROCESS_IO_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "wait_process",
        "description": "Wait for a background command to exit up to a timeout, returning recent stdout/stderr without stopping it on timeout.",
        "input_schema": {
            "type": "object",
            "properties": {
                "process_id": {"type": "string"},
                "timeout_ms": {
                    "type": "integer",
                    "minimum": 100,
                    "maximum": 600000,
                    "description": "Optional wait timeout in milliseconds. Defaults to 5000.",
                },
                "stdout_contains": {
                    "type": "string",
                    "description": "Optional stdout text or regex pattern to wait for before returning.",
                },
                "stderr_contains": {
                    "type": "string",
                    "description": "Optional stderr text or regex pattern to wait for before returning.",
                },
                "regex": {
                    "type": "boolean",
                    "description": "Treat stdout_contains and stderr_contains as Python regular expressions. Defaults to false.",
                },
                "max_output_chars": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 50000,
                    "description": "Optional maximum characters to keep for each output stream. Defaults to 4000.",
                },
            },
            "required": ["process_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_write_process",
        "description": "Preview whether text can be written to stdin of a running background command without writing it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "process_id": {"type": "string"},
                "content": {
                    "type": "string",
                    "description": "Exact text intended for stdin. Include \\n when pressing Enter is required.",
                },
            },
            "required": ["process_id", "content"],
            "additionalProperties": False,
        },
    },
    {
        "name": "write_process",
        "description": "Write exact text to stdin of a running background command started by start_command.",
        "input_schema": {
            "type": "object",
            "properties": {
                "process_id": {"type": "string"},
                "content": {
                    "type": "string",
                    "description": "Exact text to write to stdin. Include \\n when pressing Enter is required.",
                },
            },
            "required": ["process_id", "content"],
            "additionalProperties": False,
        },
    },
]
