from __future__ import annotations

from typing import Any


FILE_PATCH_EDIT_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "check_regex_replace",
        "description": "Preview a Python regular expression replacement in one existing UTF-8 project file without writing changes. Returns replacement count and diff.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "pattern": {"type": "string", "description": "Python regular expression pattern. Must not be empty."},
                "replacement": {"type": "string", "description": "Python regex replacement text, including backreferences if needed."},
                "count": {"type": "integer", "minimum": 0, "description": "Maximum replacements to preview. Use 0 for all matches."},
                "case_sensitive": {"type": "boolean", "description": "Whether matching is case-sensitive. Defaults to true."},
                "multiline": {"type": "boolean", "description": "Whether ^ and $ match line boundaries. Defaults to false."},
                "max_replacements": {"type": "integer", "minimum": 1, "maximum": 1000},
            },
            "required": ["path", "pattern", "replacement"],
            "additionalProperties": False,
        },
    },
    {
        "name": "regex_replace",
        "description": "Apply a Python regular expression replacement to one existing UTF-8 project file after bounding the replacement count. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "pattern": {"type": "string", "description": "Python regular expression pattern. Must not be empty."},
                "replacement": {"type": "string", "description": "Python regex replacement text, including backreferences if needed."},
                "count": {"type": "integer", "minimum": 0, "description": "Maximum replacements to apply. Use 0 for all matches."},
                "case_sensitive": {"type": "boolean", "description": "Whether matching is case-sensitive. Defaults to true."},
                "multiline": {"type": "boolean", "description": "Whether ^ and $ match line boundaries. Defaults to false."},
                "max_replacements": {"type": "integer", "minimum": 1, "maximum": 1000},
            },
            "required": ["path", "pattern", "replacement"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_patch",
        "description": "Validate one unified diff patch against an existing project file without writing changes. Returns the diff that would be applied.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "patch": {
                    "type": "string",
                    "description": "Unified diff text with @@ hunk headers. The file path is provided separately.",
                },
            },
            "required": ["path", "patch"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_patches",
        "description": "Validate a multi-file unified diff without writing changes. The diff may modify existing text files, create new text files, or delete text files. Returns the combined diff that would be applied.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patch": {
                    "type": "string",
                    "description": "Unified diff text with ---/+++ file headers and @@ hunk headers.",
                },
            },
            "required": ["patch"],
            "additionalProperties": False,
        },
    },
    {
        "name": "patch_file",
        "description": "Apply one or more unified diff hunks to an existing project file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "patch": {
                    "type": "string",
                    "description": "Unified diff text with @@ hunk headers. The file path is provided separately.",
                },
            },
            "required": ["path", "patch"],
            "additionalProperties": False,
        },
    },
    {
        "name": "patch_files",
        "description": "Apply a multi-file unified diff atomically. The diff may modify existing text files, create new text files, or delete text files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patch": {
                    "type": "string",
                    "description": "Unified diff text with ---/+++ file headers and @@ hunk headers.",
                },
            },
            "required": ["patch"],
            "additionalProperties": False,
        },
    },
]
