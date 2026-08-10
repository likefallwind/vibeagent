from __future__ import annotations

from typing import Any

from .tool_definition_output_schema import COMMAND_OUTPUT_EXTRACTION_PROPERTIES


PROCESS_RUN_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "run_command",
        "description": "Run a shell command from the project directory with a timeout and safety checks.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "timeout_ms": {
                    "type": "integer",
                    "minimum": 100,
                    "maximum": 600000,
                    "description": "Optional command timeout in milliseconds. Defaults to the session timeout.",
                },
                "cwd": {
                    "type": "string",
                    "description": "Optional workspace directory to run in. Defaults to the project root.",
                },
                "max_output_chars": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 50000,
                    "description": "Optional maximum characters to keep for each output stream. Defaults to 12000.",
                },
                **COMMAND_OUTPUT_EXTRACTION_PROPERTIES,
            },
            "required": ["command"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_start_command",
        "description": "Validate starting a long-running shell command from the project directory without launching it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "cwd": {
                    "type": "string",
                    "description": "Optional workspace directory to run in. Defaults to the project root.",
                },
            },
            "required": ["command"],
            "additionalProperties": False,
        },
    },
    {
        "name": "start_command",
        "description": "Start a long-running shell command from the project directory and return a process id.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "cwd": {
                    "type": "string",
                    "description": "Optional workspace directory to run in. Defaults to the project root.",
                },
                "max_output_chars": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 50000,
                    "description": "Optional output tail size to preserve with the start request.",
                },
            },
            "required": ["command"],
            "additionalProperties": False,
        },
    },
]
