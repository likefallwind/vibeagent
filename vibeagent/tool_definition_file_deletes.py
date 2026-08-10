from __future__ import annotations

from typing import Any


FILE_DELETE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "check_delete_file",
        "description": "Validate deleting one existing UTF-8 text project file without removing it. Returns the diff that would be applied.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "delete_file",
        "description": "Delete one existing project file.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_delete_files",
        "description": "Validate deleting explicit existing UTF-8 text project files without removing them. Returns the combined diff that would be applied.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 100,
                    "description": "Explicit workspace file paths to delete. Globs are not expanded.",
                }
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
    {
        "name": "delete_files",
        "description": "Delete explicit existing project files after approval. All files are validated before any file is removed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 100,
                    "description": "Explicit workspace file paths to delete. Globs are not expanded.",
                }
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
]
