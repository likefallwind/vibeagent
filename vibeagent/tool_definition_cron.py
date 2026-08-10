from __future__ import annotations

from typing import Any


CRON_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "CronCreate",
        "description": (
            "Schedule a prompt in the current session using a standard five-field cron expression. "
            "Set recurring false for a one-shot reminder or true for a task that repeats for up to seven days."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cron": {
                    "type": "string",
                    "description": "Five fields: minute hour day-of-month month day-of-week, interpreted in local time.",
                },
                "prompt": {"type": "string", "minLength": 1, "maxLength": 25000},
                "recurring": {"type": "boolean"},
            },
            "required": ["cron", "prompt", "recurring"],
            "additionalProperties": False,
        },
    },
    {
        "name": "CronList",
        "description": "List scheduled tasks in the current session, including IDs, schedules, prompts, and next runs.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "CronDelete",
        "description": "Cancel one current-session scheduled task by its 8-character ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "taskId": {"type": "string", "minLength": 8, "maxLength": 8},
            },
            "required": ["taskId"],
            "additionalProperties": False,
        },
    },
]
