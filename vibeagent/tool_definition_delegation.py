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
                "run_in_background": {"type": "boolean"},
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
                "run_in_background": {"type": "boolean"},
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
                "run_in_background": {"type": "boolean"},
            },
            "required": ["prompt"],
            "additionalProperties": False,
        },
    },
    {
        "name": "ListAgents",
        "description": "List running and resumable subagent instances in the current session. This lists agent runs, not project profile definitions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_agents": {"type": "integer", "minimum": 1, "maximum": 500},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "SendMessage",
        "description": "Resume a completed subagent by ID with its full prior context and a follow-up message.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"},
                "message": {"type": "string", "minLength": 1, "maxLength": 4000},
            },
            "required": ["to", "message"],
            "additionalProperties": False,
        },
    },
    {
        "name": "TaskOutput",
        "description": "Read the current or final result of a background subagent task.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"},
                "block": {"type": "boolean"},
                "timeout_ms": {"type": "integer", "minimum": 0, "maximum": 600000},
            },
            "required": ["task_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "TaskStop",
        "description": "Request cancellation of a running background subagent task.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"},
            },
            "required": ["task_id"],
            "additionalProperties": False,
        },
    },
]
