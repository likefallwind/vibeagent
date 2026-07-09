from __future__ import annotations

from typing import Any


READING_BATCH_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "tail_file",
        "description": "Read the last lines of a UTF-8 text file from the project, useful for logs and long generated outputs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "line_count": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000,
                    "description": "Number of trailing lines to read. Defaults to 80.",
                },
                "max_bytes": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 200000,
                    "description": "Maximum characters returned from the file tail. Defaults to 20000.",
                },
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "read_files",
        "description": "Read multiple UTF-8 text files from the project in one tool call.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 20,
                    "items": {"type": "string"},
                    "description": "Project-relative file paths to read.",
                },
                "max_bytes_per_file": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 200000,
                    "description": "Maximum characters returned per file. Defaults to 20000.",
                },
                "show_line_numbers": {
                    "type": "boolean",
                    "description": "Prefix returned file lines with 1-based line numbers. Defaults to false.",
                },
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
    {
        "name": "read_file_ranges",
        "description": "Read focused line ranges from one or more UTF-8 text files in one tool call.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ranges": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 20,
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Project-relative file path to read."},
                            "start_line": {
                                "type": "integer",
                                "minimum": 1,
                                "description": "1-based first line to read.",
                            },
                            "line_count": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 1000,
                                "description": "Number of lines to read. Defaults to 120.",
                            },
                        },
                        "required": ["path", "start_line"],
                        "additionalProperties": False,
                    },
                    "description": "Project-relative file line ranges to read.",
                },
                "max_bytes_per_range": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 200000,
                    "description": "Maximum characters returned per range. Defaults to 20000.",
                },
            },
            "required": ["ranges"],
            "additionalProperties": False,
        },
    },
]
