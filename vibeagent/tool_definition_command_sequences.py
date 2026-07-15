from __future__ import annotations

from typing import Any

from .tool_definition_output_schema import COMMAND_OUTPUT_EXTRACTION_PROPERTIES


COMMAND_SEQUENCE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "command_check",
        "description": "Preflight one proposed shell command without running it: validate project-relative cwd, dangerous-command blocking, and main executable availability.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to preflight without executing."},
                "cwd": {"type": "string", "description": "Optional project-relative directory to run from. Defaults to project root."},
            },
            "required": ["command"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_run_commands",
        "description": "Preflight several finite shell commands without running them. Validates cwd, dangerous-command blocking, and executable availability for each command.",
        "input_schema": {
            "type": "object",
            "properties": {
                "commands": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 10,
                    "items": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "Shell command to preflight without executing."},
                            "description": {"type": "string", "description": "Short human-readable reason for this command."},
                            "cwd": {"type": "string", "description": "Optional project-relative directory to run from. Defaults to project root."},
                            "timeout_ms": {
                                "type": "integer",
                                "minimum": 100,
                                "maximum": 600000,
                                "description": "Optional timeout in milliseconds for run_commands. Defaults to the agent command timeout.",
                            },
                            "max_output_chars": {
                                "type": "integer",
                                "minimum": 1000,
                                "maximum": 50000,
                                "description": "Optional stdout/stderr character cap per command. Defaults to 12000.",
                            },
                            **COMMAND_OUTPUT_EXTRACTION_PROPERTIES,
                        },
                        "required": ["command"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["commands"],
            "additionalProperties": False,
        },
    },
    {
        "name": "run_commands",
        "description": "Run several finite shell commands sequentially from the project directory after approval. Stops at the first failure by default.",
        "input_schema": {
            "type": "object",
            "properties": {
                "commands": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 10,
                    "items": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "Shell command to run."},
                            "description": {"type": "string", "description": "Short human-readable reason for this command."},
                            "cwd": {"type": "string", "description": "Optional project-relative directory to run from. Defaults to project root."},
                            "timeout_ms": {
                                "type": "integer",
                                "minimum": 100,
                                "maximum": 600000,
                                "description": "Optional timeout in milliseconds. Defaults to the agent command timeout.",
                            },
                            "max_output_chars": {
                                "type": "integer",
                                "minimum": 1000,
                                "maximum": 50000,
                                "description": "Optional stdout/stderr character cap per command. Defaults to 12000.",
                            },
                            **COMMAND_OUTPUT_EXTRACTION_PROPERTIES,
                        },
                        "required": ["command"],
                        "additionalProperties": False,
                    },
                },
                "stop_on_failure": {
                    "type": "boolean",
                    "description": "Stop running later commands after the first nonzero, timed-out, blocked, or invalid command. Defaults to true.",
                },
            },
            "required": ["commands"],
            "additionalProperties": False,
        },
    },
]
