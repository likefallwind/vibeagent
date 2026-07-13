from __future__ import annotations

from typing import Any


DELEGATION_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "delegate_task",
        "description": "Delegate one bounded task to an isolated subagent context. Use explore for read-only research and code for a focused implementation whose side effects remain subject to the parent approval policy. Subagents cannot ask the user or delegate again.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "minLength": 1, "maxLength": 4000},
                "context": {
                    "type": "string",
                    "maxLength": 4000,
                    "description": "Optional focused context or constraints the subagent should use.",
                },
                "max_iterations": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 8,
                    "description": "Maximum subagent model turns. Defaults to 4.",
                },
                "mode": {
                    "type": "string",
                    "enum": ["explore", "code"],
                    "description": "Use explore for read-only investigation or code for implementation. Defaults to explore.",
                },
                "agent": {
                    "type": "string",
                    "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$",
                    "description": "Optional exact project agent profile name from the available profile catalog. The profile controls mode, prompt, and tool scope.",
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
                "max_iterations": {"type": "integer", "minimum": 1, "maximum": 8},
            },
            "required": ["prompt"],
            "additionalProperties": False,
        },
    },
]
