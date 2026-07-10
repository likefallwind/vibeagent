from __future__ import annotations

from typing import Any


TASK_CONTROL_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "ask_user",
        "description": "Ask one blocking clarification question when repository evidence cannot determine a choice that materially changes the implementation. Do not use this for approvals or questions that can be answered by inspecting the project.",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "minLength": 1, "maxLength": 1000},
                "options": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 4,
                    "uniqueItems": True,
                    "items": {"type": "string", "minLength": 1, "maxLength": 200},
                },
                "allow_free_text": {
                    "type": "boolean",
                    "description": "Whether the user may answer with text outside the listed options. Defaults to true.",
                },
            },
            "required": ["question"],
            "dependentRequired": {"allow_free_text": ["options"]},
            "additionalProperties": False,
        },
    },
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
