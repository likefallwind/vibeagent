from __future__ import annotations

from typing import Any


TASK_CONTROL_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "update_plan",
        "description": "Replace the current task plan with a concise checklist of remaining work.",
        "input_schema": {
            "type": "object",
            "properties": {
                "explanation": {
                    "type": "string",
                    "description": "Optional short reason for the plan change.",
                },
                "plan": {
                    "type": "array",
                    "description": "Ordered task checklist. Keep it short and update it as work changes.",
                    "minItems": 1,
                    "maxItems": 20,
                    "items": {
                        "type": "object",
                        "properties": {
                            "step": {"type": "string"},
                            "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
                        },
                        "required": ["step", "status"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["plan"],
            "additionalProperties": False,
        },
    },
    {
        "name": "finish",
        "description": "Finish the task with a concise summary for the user.",
        "input_schema": {
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"],
            "additionalProperties": False,
        },
    },
]
