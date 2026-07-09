from __future__ import annotations

from typing import Any


READING_SOURCE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "python_symbols",
        "description": "Read a Python source outline without executing code. Returns imports and class/function definitions with line numbers.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 20,
                    "items": {"type": "string"},
                    "description": "Project-relative .py file paths to inspect.",
                }
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
    {
        "name": "code_outline",
        "description": "Read a lightweight source outline for Python, JavaScript/TypeScript, Go, Rust, Java/Kotlin, C, or C++ files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 20,
                    "items": {"type": "string"},
                    "description": "Project-relative source file paths to inspect.",
                },
                "max_symbols": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000,
                    "description": "Maximum symbol count per file. Defaults to 200.",
                },
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
    {
        "name": "python_check",
        "description": "Check Python files for syntax errors without executing code, optionally scoped to one project-relative file or directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Optional project-relative Python file or directory scope."},
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum Python file count to check. Defaults to 200.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "config_check",
        "description": "Check JSON and TOML config files for syntax errors without executing project code, optionally scoped to one project-relative file or directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Optional project-relative JSON/TOML file or directory scope."},
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum config file count to check. Defaults to 200.",
                },
            },
            "additionalProperties": False,
        },
    },
]
