from __future__ import annotations

from typing import Any


CLAUDE_READ_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "Read",
        "description": "Claude-compatible alias for reading one project file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "offset": {"type": "integer", "minimum": 0},
                "limit": {"type": "integer", "minimum": 1, "maximum": 2000},
                "read_range": {
                    "description": "Inclusive line range: object, [start,end], or 'start-end'.",
                    "oneOf": [
                        {
                            "type": "object",
                            "properties": {
                                "start": {"type": "integer", "minimum": 1},
                                "end": {"type": "integer", "minimum": 1},
                                "start_line": {"type": "integer", "minimum": 1},
                                "end_line": {"type": "integer", "minimum": 1},
                            },
                            "anyOf": [
                                {"required": ["start", "end"]},
                                {"required": ["start_line", "end_line"]},
                            ],
                            "additionalProperties": False,
                        },
                        {"type": "array", "minItems": 2, "maxItems": 2},
                        {"type": "string"},
                    ],
                },
                "max_bytes": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 200000,
                    "description": "Maximum full-file characters to return when offset is not provided. Defaults to 20000.",
                },
                "show_line_numbers": {
                    "type": "boolean",
                    "description": "Prefix returned full-file lines with 1-based line numbers. Range reads already include line numbers.",
                },
            },
            "required": ["file_path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "NotebookRead",
        "description": "Claude-compatible alias for reading a project notebook as structured cell summaries.",
        "input_schema": {
            "type": "object",
            "properties": {
                "notebook_path": {"type": "string"},
                "offset": {"type": "integer", "minimum": 0},
                "limit": {"type": "integer", "minimum": 1, "maximum": 2000},
                "include_outputs": {"type": "boolean"},
            },
            "required": ["notebook_path"],
            "additionalProperties": False,
        },
    },
]


CLAUDE_SEARCH_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "LS",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "ignore": {"type": "array", "items": {"type": "string"}, "maxItems": 50},
                "max_depth": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10,
                },
                "max_entries": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000,
                },
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "Glob",
        "description": "Claude-compatible alias for finding project files by glob pattern.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string"},
                "max_matches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum match count to return. Defaults to 200.",
                },
                "include_dirs": {
                    "type": "boolean",
                    "description": "Whether directory matches should be returned with trailing slashes. Defaults to false.",
                },
            },
            "required": ["pattern"],
            "additionalProperties": False,
        },
    },
    {
        "name": "Grep",
        "description": "Claude-compatible alias for searching project text.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string"},
                "glob": {"type": "string"},
                "type": {"type": "string"},
                "output_mode": {"type": "string", "enum": ["lines", "content", "files_with_matches", "count"]},
                "head_limit": {"type": "integer", "minimum": 1, "maximum": 500},
                "regex": {"type": "boolean"},
                "case_sensitive": {"type": "boolean"},
                "-i": {"type": "boolean"},
                "-C": {"type": "integer", "minimum": 0, "maximum": 5},
                "-A": {"type": "integer", "minimum": 0, "maximum": 5},
                "-B": {"type": "integer", "minimum": 0, "maximum": 5},
            },
            "required": ["pattern"],
            "additionalProperties": False,
        },
    },
]


CLAUDE_EDIT_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "Write",
        "description": "Claude-compatible alias for writing one project file after approval.",
        "input_schema": {
            "type": "object",
            "properties": {"file_path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["file_path", "content"],
            "additionalProperties": False,
        },
    },
    {
        "name": "Edit",
        "description": "Claude-compatible alias for editing one project file after approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "old_string": {"type": "string"},
                "new_string": {"type": "string"},
                "replace_all": {"type": "boolean"},
            },
            "required": ["file_path", "old_string", "new_string"],
            "additionalProperties": False,
        },
    },
    {
        "name": "NotebookEdit",
        "description": "Claude-compatible alias for editing one project notebook cell after approval. Also accepts old_string/new_string for legacy raw-text notebook edits.",
        "input_schema": {
            "type": "object",
            "properties": {
                "notebook_path": {"type": "string"},
                "cell_id": {"type": "string"},
                "cell_number": {"type": "integer", "minimum": 1},
                "new_source": {"type": "string"},
                "cell_type": {"type": "string", "enum": ["code", "markdown", "raw"]},
                "old_string": {"type": "string"},
                "new_string": {"type": "string"},
                "replace_all": {"type": "boolean"},
            },
            "required": ["notebook_path"],
            "anyOf": [
                {"required": ["cell_number", "new_source"]},
                {"required": ["cell_id", "new_source"]},
                {"required": ["old_string", "new_string"]},
            ],
            "additionalProperties": False,
        },
    },
    {
        "name": "MultiEdit",
        "description": "Claude-compatible alias for applying multiple edits to one project file after approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "edits": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 20,
                    "items": {
                        "type": "object",
                        "properties": {
                            "old_string": {"type": "string"},
                            "new_string": {"type": "string"},
                            "replace_all": {"type": "boolean"},
                        },
                        "required": ["old_string", "new_string"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["file_path", "edits"],
            "additionalProperties": False,
        },
    },
]


CLAUDE_FILE_TOOL_DEFINITIONS: list[dict[str, Any]] = (
    CLAUDE_READ_TOOL_DEFINITIONS + CLAUDE_SEARCH_TOOL_DEFINITIONS + CLAUDE_EDIT_TOOL_DEFINITIONS
)
