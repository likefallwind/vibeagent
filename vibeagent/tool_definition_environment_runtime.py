from __future__ import annotations

from typing import Any


ENVIRONMENT_RUNTIME_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "environment_info",
        "description": "Read fixed runtime environment facts such as Python version, platform, git repository status, and common tool availability without executing arbitrary project commands.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
]
