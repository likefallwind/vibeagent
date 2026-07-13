from __future__ import annotations

from typing import Any


FILE_EXACT_EDIT_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "check_edit_file",
        "description": "Validate one exact text replacement in an existing project file without writing changes. Returns the diff that would be applied.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old": {"type": "string"},
                "new": {"type": "string"},
            },
            "required": ["path", "old", "new"],
            "additionalProperties": False,
        },
    },
    {
        "name": "edit_file",
        "description": "Replace one exact text block in an existing project file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old": {"type": "string"},
                "new": {"type": "string"},
            },
            "required": ["path", "old", "new"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_multi_edit_file",
        "description": "Validate multiple exact text replacements against one existing project file without writing changes. Returns the diff that would be applied.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "edits": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 20,
                    "items": {
                        "type": "object",
                        "properties": {
                            "old": {"type": "string"},
                            "new": {"type": "string"},
                            "replace_all": {"type": "boolean"},
                        },
                        "required": ["old", "new"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["path", "edits"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_notebook_edit",
        "description": "Validate replacing one notebook cell source without writing changes. Returns the notebook JSON diff that would be applied.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "cell_id": {"type": "string"},
                "cell_number": {"type": "integer", "minimum": 1},
                "new_source": {"type": "string"},
                "cell_type": {"type": "string", "enum": ["code", "markdown", "raw"]},
            },
            "required": ["path", "cell_number", "new_source"],
            "additionalProperties": False,
        },
    },
    {
        "name": "multi_edit_file",
        "description": "Apply multiple exact text replacements to one existing project file atomically.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "edits": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 20,
                    "items": {
                        "type": "object",
                        "properties": {
                            "old": {"type": "string"},
                            "new": {"type": "string"},
                            "replace_all": {"type": "boolean"},
                        },
                        "required": ["old", "new"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["path", "edits"],
            "additionalProperties": False,
        },
    },
]
