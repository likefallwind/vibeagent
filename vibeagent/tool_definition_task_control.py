from __future__ import annotations

from typing import Any

from .action_parsing_helpers import PLAN_ITEM_SCHEMA_STATUS_VALUES


PLAN_ITEM_STATUS_ENUM = list(PLAN_ITEM_SCHEMA_STATUS_VALUES)

PLAN_ITEM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "step": {"type": "string"},
        "status": {
            "type": "string",
            "enum": PLAN_ITEM_STATUS_ENUM,
        },
        "activeForm": {"type": "string"},
        "active_form": {"type": "string"},
    },
    "required": ["step", "status"],
    "additionalProperties": False,
}

TODO_ITEM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "content": {"type": "string"},
        "status": {
            "type": "string",
            "enum": PLAN_ITEM_STATUS_ENUM,
        },
        "activeForm": {"type": "string"},
        "active_form": {"type": "string"},
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
    "description": "Claude-style todo items. content maps to step; activeForm is stored.",
    "minItems": 1,
    "maxItems": 20,
    "items": TODO_ITEM_SCHEMA,
}

EXIT_PLAN_MODE_PLAN_SCHEMA: dict[str, Any] = {
    "oneOf": [
        {"type": "string"},
        {
            "type": "array",
            "minItems": 1,
            "maxItems": 20,
            "items": PLAN_ITEM_SCHEMA,
        },
    ],
}

ASK_USER_OPTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "label": {"type": "string", "minLength": 1, "maxLength": 200},
        "description": {"type": "string", "minLength": 1, "maxLength": 500},
    },
    "required": ["label", "description"],
    "additionalProperties": False,
}

ASK_USER_QUESTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "question": {"type": "string", "minLength": 1, "maxLength": 1000},
        "header": {"type": "string", "minLength": 1, "maxLength": 12},
        "options": {
            "type": "array",
            "minItems": 2,
            "maxItems": 4,
            "uniqueItems": True,
            "items": ASK_USER_OPTION_SCHEMA,
        },
        "multiSelect": {"type": "boolean"},
    },
    "required": ["question", "header", "options", "multiSelect"],
    "additionalProperties": False,
}


TASK_CONTROL_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "SendUserMessage",
        "description": "Send one concise non-blocking progress update to the user, then continue working. Use this only for meaningful status changes; use AskUserQuestion when an answer is required.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "minLength": 1, "maxLength": 2000},
            },
            "required": ["message"],
            "additionalProperties": False,
        },
    },
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
        "name": "AskUserQuestion",
        "description": "Ask 1 to 4 structured blocking clarification questions. Each question has a short header, 2 to 4 described options, optional multiple selection, and an implicit free-text answer.",
        "input_schema": {
            "type": "object",
            "properties": {
                "questions": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 4,
                    "items": ASK_USER_QUESTION_SCHEMA,
                },
            },
            "required": ["questions"],
            "additionalProperties": False,
        },
    },
    {
        "name": "TaskCreate",
        "description": "Create one persistent task in the current session task graph and return its assigned ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "subject": {"type": "string", "minLength": 1, "maxLength": 500},
                "description": {"type": "string", "minLength": 1, "maxLength": 10000},
                "activeForm": {"type": "string", "minLength": 1, "maxLength": 500},
                "metadata": {"type": "object", "additionalProperties": True},
            },
            "required": ["subject", "description"],
            "additionalProperties": False,
        },
    },
    {
        "name": "TaskGet",
        "description": "Read full details for one current-session task by its assigned ID.",
        "input_schema": {
            "type": "object",
            "properties": {"taskId": {"type": "string", "minLength": 1, "maxLength": 64}},
            "required": ["taskId"],
            "additionalProperties": False,
        },
    },
    {
        "name": "TaskList",
        "description": "List all tasks in the current session with status, owner, and dependency blockers.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "TaskUpdate",
        "description": "Patch one current-session task. Supports status changes, details, ownership, metadata, dependencies, and deletion.",
        "input_schema": {
            "type": "object",
            "properties": {
                "taskId": {"type": "string", "minLength": 1, "maxLength": 64},
                "status": {"type": "string", "enum": ["pending", "in_progress", "completed", "deleted"]},
                "subject": {"type": "string", "minLength": 1, "maxLength": 500},
                "description": {"type": "string", "minLength": 1, "maxLength": 10000},
                "activeForm": {
                    "anyOf": [
                        {"type": "string", "minLength": 1, "maxLength": 500},
                        {"type": "null"},
                    ]
                },
                "addBlocks": {
                    "type": "array",
                    "maxItems": 100,
                    "uniqueItems": True,
                    "items": {"type": "string", "minLength": 1, "maxLength": 64},
                },
                "addBlockedBy": {
                    "type": "array",
                    "maxItems": 100,
                    "uniqueItems": True,
                    "items": {"type": "string", "minLength": 1, "maxLength": 64},
                },
                "owner": {
                    "anyOf": [
                        {"type": "string", "minLength": 1, "maxLength": 200},
                        {"type": "null"},
                    ]
                },
                "metadata": {"type": "object", "additionalProperties": True},
            },
            "required": ["taskId"],
            "anyOf": [
                {"required": ["status"]},
                {"required": ["subject"]},
                {"required": ["description"]},
                {"required": ["activeForm"]},
                {"required": ["addBlocks"]},
                {"required": ["addBlockedBy"]},
                {"required": ["owner"]},
                {"required": ["metadata"]},
            ],
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
                {"required": ["plan"]},
                {"required": ["todos"]},
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
        "name": "TodoRead",
        "description": "Claude-compatible alias for reading the latest task plan.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "TodoWrite",
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
                "explanation": {"type": "string"},
            },
            "anyOf": [
                {"required": ["plan"]},
                {"required": ["todos"]},
            ],
            "additionalProperties": False,
        },
    },
    {
        "name": "EnterPlanMode",
        "description": "Switch the current agent run into read-only plan mode.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "ExitPlanMode",
        "description": "Present the completed plan for approval and leave plan mode when approved.",
        "input_schema": {
            "type": "object",
            "properties": {
                "plan": EXIT_PLAN_MODE_PLAN_SCHEMA,
                "allowedPrompts": {
                    "type": "array",
                    "items": {"type": "object", "additionalProperties": {"type": "string"}},
                    "maxItems": 20,
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
