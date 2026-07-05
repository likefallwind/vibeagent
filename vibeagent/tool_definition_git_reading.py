from __future__ import annotations

from typing import Any


GIT_READING_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "git_diff",
        "description": "Read the current git diff for the project, optionally limited to one path or staged changes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Optional project-relative path to diff."},
                "staged": {"type": "boolean", "description": "Show staged diff instead of unstaged diff."},
                "max_output_chars": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 50000,
                    "description": "Maximum diff characters to return. Defaults to 12000.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "git_diff_hunks",
        "description": "Read a structured summary of current git diff hunks with file paths, old/new ranges, changed-line counts, and bounded hunk lines.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Optional project-relative path to diff."},
                "staged": {"type": "boolean", "description": "Show staged diff hunks instead of unstaged diff hunks."},
                "max_hunks": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum hunk count to return. Defaults to 80.",
                },
                "max_lines_per_hunk": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum diff lines to return per hunk. Defaults to 80.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "git_diff_contexts",
        "description": "Read current source context around each git diff hunk so changed code can be reviewed without manually requesting file ranges.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Optional project-relative path to diff."},
                "staged": {"type": "boolean", "description": "Show staged diff contexts instead of unstaged diff contexts."},
                "context_lines": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 50,
                    "description": "Source context lines before and after each hunk's new range start. Defaults to 5.",
                },
                "max_hunks": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum hunk context count to return. Defaults to 80.",
                },
                "max_bytes_per_context": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 200000,
                    "description": "Maximum bytes per source context excerpt. Defaults to 20000.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "git_log",
        "description": "Read recent git commit history in one-line format, optionally limited to one path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_count": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "description": "Maximum commit count to return. Defaults to 5.",
                },
                "path": {"type": "string", "description": "Optional project-relative path to limit history."},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "git_show",
        "description": "Read one git revision with metadata, stat, and patch, optionally limited to one path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "rev": {
                    "type": "string",
                    "description": "Revision to inspect. Defaults to HEAD.",
                },
                "path": {"type": "string", "description": "Optional project-relative path to limit output."},
                "max_output_chars": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 50000,
                    "description": "Maximum output characters to return. Defaults to 12000.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "git_blame",
        "description": "Read git blame attribution for one project file, optionally limited to a line range.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Project-relative file path to blame."},
                "start_line": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Optional starting line for a focused blame range.",
                },
                "line_count": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000,
                    "description": "Optional number of lines to include when start_line is provided. Defaults to 120.",
                },
                "max_output_chars": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 50000,
                    "description": "Maximum blame output characters to return. Defaults to 12000.",
                },
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    },
]
