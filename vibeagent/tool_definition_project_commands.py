from __future__ import annotations

from typing import Any


PROJECT_COMMAND_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "project_commands",
        "description": "List project-defined commands from package.json scripts, pyproject.toml console scripts, and Makefile targets without running them, including cwd and executable availability.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_commands": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum command count to return. Defaults to 100.",
                },
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "description": "Maximum command metadata files to scan. Defaults to 30.",
                },
            },
            "additionalProperties": False,
        },
    },
]
