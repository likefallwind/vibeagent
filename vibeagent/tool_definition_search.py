from __future__ import annotations

from typing import Any


SEARCH_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "search",
        "description": "Search project text for an exact query string or regex, optionally under one path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "path": {"type": "string", "description": "Optional workspace file or directory to search."},
                "file_glob": {
                    "type": "string",
                    "description": "Optional file glob filter, such as *.py or src/**/*.py.",
                },
                "output_mode": {
                    "type": "string",
                    "enum": ["lines", "content", "files_with_matches", "count"],
                    "description": "Whether to return matching lines, contextual content, only files with matches, or per-file match counts. Defaults to lines.",
                },
                "regex": {"type": "boolean", "description": "Treat query as a regular expression."},
                "case_sensitive": {"type": "boolean", "description": "Whether matching is case-sensitive. Defaults to true."},
                "max_matches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum match count to return. Defaults to 80.",
                },
                "context_lines": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 5,
                    "description": "Number of surrounding lines to include around each match. Defaults to 0.",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "search_contexts",
        "description": "Search project text and return structured line-centered context snippets for each match.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "path": {"type": "string", "description": "Optional workspace file or directory to search."},
                "file_glob": {
                    "type": "string",
                    "description": "Optional file glob filter, such as *.py or src/**/*.py.",
                },
                "regex": {"type": "boolean", "description": "Treat query as a regular expression."},
                "case_sensitive": {"type": "boolean", "description": "Whether matching is case-sensitive. Defaults to true."},
                "max_matches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum context count to return. Defaults to 20.",
                },
                "context_lines": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 50,
                    "description": "Number of surrounding lines to include around each match. Defaults to 3.",
                },
                "max_bytes_per_context": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 200000,
                    "description": "Maximum bytes per context snippet. Defaults to 20000.",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "find_files",
        "description": "Find project file paths by substring or regex without reading file contents. Use this when you know part of a filename or path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Filename or workspace path fragment to match."},
                "path": {"type": "string", "description": "Optional workspace file or directory scope to search."},
                "regex": {"type": "boolean", "description": "Treat query as a regular expression. Defaults to false."},
                "case_sensitive": {"type": "boolean", "description": "Whether matching is case-sensitive. Defaults to false."},
                "include_dirs": {"type": "boolean", "description": "Whether directory matches should be returned with trailing slashes. Defaults to false."},
                "max_matches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum path count to return. Defaults to 100.",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "glob",
        "description": "Find project files by relative glob pattern, such as **/*.py or tests/test_*.py. Can include directory matches when requested.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
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
]
