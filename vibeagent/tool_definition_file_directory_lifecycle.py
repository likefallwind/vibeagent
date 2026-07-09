from __future__ import annotations

from typing import Any


FILE_DIRECTORY_LIFECYCLE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "check_create_dir",
        "description": "Validate creating one project-relative directory, including missing parent directories, without changing files.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_create_dirs",
        "description": "Validate creating one or more project-relative directories, including missing parent directories, without changing files. Rejects duplicate targets.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 100,
                }
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
    {
        "name": "create_dir",
        "description": "Create one project-relative directory, including missing parent directories. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "create_dirs",
        "description": "Create one or more project-relative directories, including missing parent directories. Validates all targets before creating any directory. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 100,
                }
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_delete_empty_dir",
        "description": "Validate deleting one existing empty project-relative directory without removing it.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_delete_empty_dirs",
        "description": "Validate deleting one or more existing empty project-relative directories without removing them. Parent directories may be included when their listed child directories are also deleted.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 100,
                }
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
    {
        "name": "delete_empty_dir",
        "description": "Delete one existing empty project-relative directory. Does not delete non-empty directories. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "delete_empty_dirs",
        "description": "Delete one or more existing empty project-relative directories after validating all targets. Does not delete non-empty directories. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 100,
                }
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
]
