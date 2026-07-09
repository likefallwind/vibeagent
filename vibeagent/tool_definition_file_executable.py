from __future__ import annotations

from typing import Any


FILE_EXECUTABLE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "check_set_executable",
        "description": "Validate setting or clearing executable permission bits on one existing project file without changing mode bits.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "executable": {
                    "type": "boolean",
                    "description": "True to add executable bits, false to remove them. Defaults to true.",
                },
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "set_executable",
        "description": "Set or clear executable permission bits on one existing project file. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "executable": {
                    "type": "boolean",
                    "description": "True to add executable bits, false to remove them. Defaults to true.",
                },
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    },
]
