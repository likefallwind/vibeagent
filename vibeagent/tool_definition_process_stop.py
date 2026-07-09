from __future__ import annotations

from typing import Any


PROCESS_STOP_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "list_processes",
        "description": "List background commands started by start_command for the current project.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "check_stop_all_processes",
        "description": "Preview all background commands for the current project that stop_all_processes would stop.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "check_stop_process",
        "description": "Validate that a background command id exists and report whether stop_process would stop it.",
        "input_schema": {
            "type": "object",
            "properties": {"process_id": {"type": "string"}},
            "required": ["process_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "stop_all_processes",
        "description": "Stop all background commands started by start_command for the current project after approval.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "stop_process",
        "description": "Stop a background command started by start_command after approval.",
        "input_schema": {
            "type": "object",
            "properties": {"process_id": {"type": "string"}},
            "required": ["process_id"],
            "additionalProperties": False,
        },
    },
]
