from __future__ import annotations

from typing import Any


TEAM_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "TeamCreate",
        "description": (
            "Create the one experimental agent team for this session before spawning named teammates with Agent."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "team_name": {
                    "type": "string",
                    "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$",
                },
                "description": {"type": "string", "minLength": 1, "maxLength": 1000},
            },
            "required": ["team_name", "description"],
            "additionalProperties": False,
        },
    },
    {
        "name": "TeamDelete",
        "description": (
            "Disband the current experimental agent team after every named teammate has stopped."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
]


__all__ = ["TEAM_TOOL_DEFINITIONS"]
