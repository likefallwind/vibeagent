from __future__ import annotations

from typing import Any


PROCESS_OUTPUT_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "read_process",
        "description": "Read status and recent stdout/stderr from a background command started by start_command.",
        "input_schema": {
            "type": "object",
            "properties": {
                "process_id": {"type": "string"},
                "max_output_chars": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 50000,
                    "description": "Optional maximum characters to keep for each output stream. Defaults to 4000.",
                },
                "output_filter": {
                    "type": "string",
                    "description": "Optional regex used to keep only matching output lines.",
                },
            },
            "required": ["process_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "process_output_contexts",
        "description": "Extract file:line references from recent stdout/stderr of a background command started by start_command and include source context.",
        "input_schema": {
            "type": "object",
            "properties": {
                "process_id": {"type": "string"},
                "max_output_chars": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 50000,
                    "description": "Maximum recent characters to scan from each output stream. Defaults to the process start limit or 4000.",
                },
                "context_lines": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 500,
                    "description": "Lines before and after each extracted reference. Defaults to 5.",
                },
                "max_contexts": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum extracted contexts to include. Defaults to 20.",
                },
                "max_bytes_per_context": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 200000,
                    "description": "Maximum bytes per extracted file context. Defaults to 20000.",
                },
            },
            "required": ["process_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "process_output_diagnostics",
        "description": "Summarize error, warning, and failure lines from recent stdout/stderr of a background command started by start_command and include referenced source context.",
        "input_schema": {
            "type": "object",
            "properties": {
                "process_id": {"type": "string"},
                "max_output_chars": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 50000,
                    "description": "Maximum recent characters to scan from each output stream. Defaults to the process start limit or 4000.",
                },
                "context_lines": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 500,
                    "description": "Lines before and after each referenced source line. Defaults to 2.",
                },
                "max_diagnostics": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "description": "Maximum diagnostic rows to include. Defaults to 50.",
                },
                "max_contexts": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum referenced source contexts to include. Defaults to 20.",
                },
                "max_bytes_per_context": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 200000,
                    "description": "Maximum bytes per extracted file context. Defaults to 20000.",
                },
            },
            "required": ["process_id"],
            "additionalProperties": False,
        },
    },
]
