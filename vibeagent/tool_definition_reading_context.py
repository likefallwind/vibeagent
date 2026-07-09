from __future__ import annotations

from typing import Any


READING_CONTEXT_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "read_file",
        "description": "Read a UTF-8 text file from the project, optionally starting at a 1-based line number.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "start_line": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Optional 1-based first line to read.",
                },
                "line_count": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000,
                    "description": "Optional number of lines to read when start_line is provided. Defaults to 200.",
                },
                "max_bytes": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 200000,
                    "description": "Maximum full-file characters to return when start_line is not provided. Defaults to 20000.",
                },
                "show_line_numbers": {
                    "type": "boolean",
                    "description": "Prefix returned full-file lines with 1-based line numbers. Line-range reads already include line numbers. Defaults to false.",
                },
            },
            "required": ["path"],
            "dependentRequired": {"line_count": ["start_line"]},
            "additionalProperties": False,
        },
    },
    {
        "name": "read_file_context",
        "description": "Read a focused line with surrounding context from a UTF-8 project text file, useful for stack traces and test failures.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "line": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "1-based target line number to center in the excerpt.",
                },
                "context_lines": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 500,
                    "description": "Lines to include before and after the target line. Defaults to 20.",
                },
                "max_bytes": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 200000,
                    "description": "Maximum characters returned from the focused context. Defaults to 20000.",
                },
            },
            "required": ["path", "line"],
            "additionalProperties": False,
        },
    },
    {
        "name": "read_file_contexts",
        "description": "Read several focused file:line contexts in one call, useful for stack traces and multi-file test or lint failures.",
        "input_schema": {
            "type": "object",
            "properties": {
                "contexts": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 20,
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Project-relative file path to read."},
                            "line": {
                                "type": "integer",
                                "minimum": 1,
                                "description": "1-based target line number to center in the excerpt.",
                            },
                            "context_lines": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 500,
                                "description": "Lines to include before and after the target line. Defaults to 20.",
                            },
                        },
                        "required": ["path", "line"],
                        "additionalProperties": False,
                    },
                    "description": "Project-relative file line contexts to read.",
                },
                "max_bytes_per_context": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 200000,
                    "description": "Maximum characters returned per context. Defaults to 20000.",
                },
            },
            "required": ["contexts"],
            "additionalProperties": False,
        },
    },
]
