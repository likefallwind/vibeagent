from __future__ import annotations

from typing import Any


PLAN_ITEM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "step": {"type": "string"},
        "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
    },
    "required": ["step", "status"],
    "additionalProperties": False,
}

TODO_ITEM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "content": {"type": "string"},
        "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
        "activeForm": {"type": "string"},
    },
    "required": ["content", "status"],
    "additionalProperties": True,
}

PLAN_ARRAY_SCHEMA: dict[str, Any] = {
    "type": "array",
    "description": "Ordered task checklist. Keep it short and update it as work changes.",
    "minItems": 1,
    "maxItems": 20,
    "items": PLAN_ITEM_SCHEMA,
}

TODO_PLAN_ARRAY_SCHEMA: dict[str, Any] = {
    **PLAN_ARRAY_SCHEMA,
    "description": "VibeAgent plan items with step and status.",
}

TODO_ARRAY_SCHEMA: dict[str, Any] = {
    "type": "array",
    "description": "Claude-style todo items. content is mapped to the plan step; activeForm is accepted but not stored separately.",
    "minItems": 1,
    "maxItems": 20,
    "items": TODO_ITEM_SCHEMA,
}


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
                    **PLAN_ARRAY_SCHEMA,
                },
            },
            "required": ["plan"],
            "additionalProperties": False,
        },
    },
    {
        "name": "todo_write",
        "description": "Claude-compatible alias for replacing the current task plan. Accepts either a VibeAgent plan list or a Claude-style todos list.",
        "input_schema": {
            "type": "object",
            "properties": {
                "plan": {
                    **TODO_PLAN_ARRAY_SCHEMA,
                },
                "todos": {
                    **TODO_ARRAY_SCHEMA,
                },
                "explanation": {
                    "type": "string",
                    "description": "Optional short reason for the todo update.",
                },
            },
            "anyOf": [
                {
                    "type": "object",
                    "properties": {
                        "plan": {
                            **TODO_PLAN_ARRAY_SCHEMA,
                        }
                    },
                    "required": ["plan"],
                },
                {
                    "type": "object",
                    "properties": {
                        "todos": {
                            **TODO_ARRAY_SCHEMA,
                        }
                    },
                    "required": ["todos"],
                },
            ],
            "additionalProperties": False,
        },
    },
    {
        "name": "todo_read",
        "description": "Claude-compatible alias for reading the latest task plan from the current session.",
        "input_schema": {
            "type": "object",
            "properties": {},
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
