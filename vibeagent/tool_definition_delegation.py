from __future__ import annotations

from typing import Any


DELEGATION_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "delegate_task",
        "description": "Delegate one bounded task to a subagent. Use explore for research or code for implementation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "minLength": 1, "maxLength": 4000},
                "context": {
                    "type": "string",
                    "maxLength": 4000,
                },
                "max_iterations": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 8,
                },
                "mode": {
                    "type": "string",
                    "enum": ["explore", "code"],
                },
                "agent": {
                    "type": "string",
                    "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$",
                },
            },
            "required": ["task"],
            "additionalProperties": False,
        },
    },
    {
        "name": "Task",
        "description": "Claude-compatible alias for delegating one bounded task to a subagent.",
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "minLength": 1, "maxLength": 4000},
                "description": {"type": "string", "maxLength": 4000},
                "subagent_type": {
                    "type": "string",
                    "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$",
                },
                "mode": {"type": "string", "enum": ["explore", "code"]},
                "max_iterations": {"type": "integer", "minimum": 1, "maximum": 8},
            },
            "required": ["prompt"],
            "additionalProperties": False,
        },
    },
    {
        "name": "Agent",
        "description": "Claude-compatible alias for delegating one bounded task to a subagent.",
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "minLength": 1, "maxLength": 4000},
                "description": {"type": "string", "maxLength": 4000},
                "subagent_type": {
                    "type": "string",
                    "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$",
                },
                "mode": {"type": "string", "enum": ["explore", "code"]},
                "max_iterations": {"type": "integer", "minimum": 1, "maximum": 8},
            },
            "required": ["prompt"],
            "additionalProperties": False,
        },
    },
]
