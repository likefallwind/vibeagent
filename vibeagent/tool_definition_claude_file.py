from __future__ import annotations

from typing import Any


CLAUDE_FILE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "Read",
        "description": "Claude-compatible alias for reading one project file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "offset": {"type": "integer", "minimum": 0},
                "limit": {"type": "integer", "minimum": 1, "maximum": 2000},
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
            },
            "required": ["notebook_path", "cell_number", "new_source"],
            "additionalProperties": False,
        },
    },
    {
        "name": "LS",
        "description": "Claude-compatible alias for listing a project directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "ignore": {"type": "array", "items": {"type": "string"}, "maxItems": 50},
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
                "output_mode": {"type": "string", "enum": ["content", "files_with_matches", "count"]},
                "head_limit": {"type": "integer", "minimum": 1, "maximum": 500},
                "-i": {"type": "boolean"},
                "-C": {"type": "integer", "minimum": 0, "maximum": 5},
                "-A": {"type": "integer", "minimum": 0, "maximum": 5},
                "-B": {"type": "integer", "minimum": 0, "maximum": 5},
            },
            "required": ["pattern"],
            "additionalProperties": False,
        },
    },
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
            "required": ["notebook_path", "cell_number", "new_source"],
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
