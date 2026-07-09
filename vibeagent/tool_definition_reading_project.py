from __future__ import annotations

from typing import Any


READING_PROJECT_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "list_files",
        "description": "List project files, optionally under a relative path.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Optional relative path to list."}},
            "additionalProperties": False,
        },
    },
    {
        "name": "list_tree",
        "description": "List a shallow project directory tree with directories and files, optionally under one relative path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Optional relative directory or file path to list."},
                "max_depth": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10,
                    "description": "Maximum directory depth to include from the requested path. Defaults to 3.",
                },
                "max_entries": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000,
                    "description": "Maximum entries to return. Defaults to 200.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "repo_map",
        "description": "Build a bounded project overview with directory tree, file list, and source import/symbol outlines.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Optional project-relative file or directory scope."},
                "max_depth": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10,
                    "description": "Maximum directory depth to include. Defaults to 3.",
                },
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum file and tree entry count to include. Defaults to 80.",
                },
                "max_symbols": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum Python symbol count across mapped files. Defaults to 120.",
                },
            },
            "additionalProperties": False,
        },
    },
]
