from __future__ import annotations

from typing import Any


GENERIC_CODE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "code_references",
        "description": "Find bounded references to one symbol or literal in JavaScript, TypeScript, Go, Rust, Java, Kotlin, C, and C++ source files without executing code.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Symbol or single-line literal to search for."},
                "path": {"type": "string", "description": "Optional project-relative source file or directory scope."},
                "max_matches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum reference count to return. Defaults to 200.",
                },
            },
            "required": ["symbol"],
            "additionalProperties": False,
        },
    },
    {
        "name": "code_reference_contexts",
        "description": "Find non-Python source references and return structured line-centered context snippets for each match.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Symbol or single-line literal to search for."},
                "path": {"type": "string", "description": "Optional project-relative source file or directory scope."},
                "max_matches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum context count to return. Defaults to 50.",
                },
                "context_lines": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 50,
                    "description": "Number of surrounding lines to include around each reference. Defaults to 3.",
                },
                "max_bytes_per_context": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 200000,
                    "description": "Maximum bytes per context snippet. Defaults to 20000.",
                },
            },
            "required": ["symbol"],
            "additionalProperties": False,
        },
    },
    {
        "name": "code_definitions",
        "description": "Find non-Python source definitions by exact symbol name and return focused source excerpts without executing code.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Exact symbol name to inspect."},
                "path": {"type": "string", "description": "Optional project-relative source file or directory scope."},
                "max_matches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "description": "Maximum definition count to return. Defaults to 50.",
                },
                "max_lines": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum source lines to return per definition. Defaults to 80.",
                },
            },
            "required": ["symbol"],
            "additionalProperties": False,
        },
    },
    {
        "name": "code_rename_preview",
        "description": "Preview a bounded non-Python source symbol or literal rename using lexical reference matching without writing changes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Symbol or single-line literal to rename."},
                "new_name": {"type": "string", "description": "Replacement symbol or single-line literal."},
                "path": {"type": "string", "description": "Optional project-relative source file or directory scope."},
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum source file count to inspect. Defaults to 100.",
                },
                "max_replacements": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 2000,
                    "description": "Maximum replacement count to include in diffs. Defaults to 500.",
                },
            },
            "required": ["symbol", "new_name"],
            "additionalProperties": False,
        },
    },
    {
        "name": "code_rename",
        "description": "Apply a bounded non-Python source symbol or literal rename using lexical reference matching.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Symbol or single-line literal to rename."},
                "new_name": {"type": "string", "description": "Replacement symbol or single-line literal."},
                "path": {"type": "string", "description": "Optional project-relative source file or directory scope."},
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum source file count to inspect. Defaults to 100.",
                },
                "max_replacements": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 2000,
                    "description": "Maximum replacement count to apply. Defaults to 2000.",
                },
            },
            "required": ["symbol", "new_name"],
            "additionalProperties": False,
        },
    },
]
