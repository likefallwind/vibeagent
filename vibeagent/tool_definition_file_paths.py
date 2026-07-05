from __future__ import annotations

from typing import Any


FILE_PATH_TOOL_DEFINITIONS: list[dict[str, Any]] = [
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
                    "description": "Explicit project-relative file paths to delete. Globs are not expanded.",
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
                    "description": "Explicit project-relative file paths to delete. Globs are not expanded.",
                }
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
{
        "name": "check_move_file",
        "description": "Validate moving or renaming one existing project file to a new project-relative path without changing files.",
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
        "name": "move_file",
        "description": "Move or rename one existing project file to a new project-relative path.",
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
        "name": "check_move_files",
        "description": "Validate moving or renaming explicit existing project files without changing files. All transfers are validated together.",
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
        "name": "move_files",
        "description": "Move or rename explicit existing project files after approval. All transfers are validated before any file is moved.",
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
        "name": "check_copy_file",
        "description": "Validate copying one existing project file to a new project-relative path without changing files.",
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
        "name": "copy_file",
        "description": "Copy one existing project file to a new project-relative path.",
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
        "name": "check_copy_files",
        "description": "Validate copying explicit existing project files to new project-relative paths without changing files. All transfers are validated together.",
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
        "name": "copy_files",
        "description": "Copy explicit existing project files to new project-relative paths after approval. All transfers are validated before any file is copied.",
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
