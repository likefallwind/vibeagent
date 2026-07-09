from __future__ import annotations

from typing import Any

from .tool_categories import valid_tool_categories


PROJECT_TOOL_CATALOG_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "tool_search",
        "description": "Search the model tool catalog by tool name, category, description, required inputs, or input property names without executing project actions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search terms such as a rough capability, tool name fragment, input property, or category.",
                },
                "max_matches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum matching tools to return. Defaults to 20.",
                },
                "category": {
                    "type": "string",
                    "enum": list(valid_tool_categories()),
                    "description": "Optional category filter.",
                },
                "approval_required": {
                    "type": "boolean",
                    "description": "Optional approval filter. True returns approval-gated tools; false returns read-only tools.",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
]
