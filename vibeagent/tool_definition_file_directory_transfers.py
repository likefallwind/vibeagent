from __future__ import annotations

from typing import Any


FILE_DIRECTORY_TRANSFER_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "check_move_dir",
        "description": "Validate moving or renaming one existing project directory to a new workspace path without changing files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "destination": {"type": "string"},
            },
            "required": ["source", "destination"],
            "additionalProperties": False,
        },
    },
    {
        "name": "move_dir",
        "description": "Move or rename one existing project directory to a new workspace path without overwriting.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "destination": {"type": "string"},
            },
            "required": ["source", "destination"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_move_dirs",
        "description": "Validate moving or renaming one or more existing project directories to new workspace paths without changing files. Rejects overlapping sources or destinations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "transfers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "destination": {"type": "string"},
                        },
                        "required": ["source", "destination"],
                        "additionalProperties": False,
                    },
                    "minItems": 1,
                    "maxItems": 100,
                }
            },
            "required": ["transfers"],
            "additionalProperties": False,
        },
    },
    {
        "name": "move_dirs",
        "description": "Move or rename one or more existing project directories to new workspace paths without overwriting after validating the whole batch. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "transfers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "destination": {"type": "string"},
                        },
                        "required": ["source", "destination"],
                        "additionalProperties": False,
                    },
                    "minItems": 1,
                    "maxItems": 100,
                }
            },
            "required": ["transfers"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_copy_dir",
        "description": "Validate copying one existing project directory tree to a new workspace path without changing files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "destination": {"type": "string"},
            },
            "required": ["source", "destination"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_copy_dirs",
        "description": "Validate copying one or more existing project directory trees to new workspace paths without changing files. Rejects symbolic links, very large directories, protected paths, and overlapping destinations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "transfers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "destination": {"type": "string"},
                        },
                        "required": ["source", "destination"],
                        "additionalProperties": False,
                    },
                    "minItems": 1,
                    "maxItems": 100,
                }
            },
            "required": ["transfers"],
            "additionalProperties": False,
        },
    },
    {
        "name": "copy_dir",
        "description": "Copy one existing project directory to a new workspace path without overwriting. Refuses symbolic links, very large directories, and protected paths.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "destination": {"type": "string"},
            },
            "required": ["source", "destination"],
            "additionalProperties": False,
        },
    },
    {
        "name": "copy_dirs",
        "description": "Copy one or more existing project directories to new workspace paths without overwriting after validating the whole batch. Refuses symbolic links, very large directories, and protected paths. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "transfers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "destination": {"type": "string"},
                        },
                        "required": ["source", "destination"],
                        "additionalProperties": False,
                    },
                    "minItems": 1,
                    "maxItems": 100,
                }
            },
            "required": ["transfers"],
            "additionalProperties": False,
        },
    },
]
