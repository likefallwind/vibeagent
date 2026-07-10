from __future__ import annotations

from typing import Any


DELEGATION_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "delegate_task",
        "description": "Delegate one bounded read-only repository investigation to an isolated subagent context. Use it for independent codebase research or impact analysis that benefits from separate context. The subagent cannot edit files, run commands, ask the user, or delegate again.",
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
            },
            "required": ["task"],
            "additionalProperties": False,
        },
    }
]
