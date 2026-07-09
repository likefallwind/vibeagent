from __future__ import annotations

from typing import Any


PYTHON_REFERENCE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "python_references",
        "description": "Find Python definitions, imports, and AST references for one identifier without executing code.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Python identifier to find, such as Client or run_agent."},
                "path": {"type": "string", "description": "Optional project-relative file or directory scope."},
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
        "name": "python_reference_contexts",
        "description": "Find Python definitions, imports, and AST references, then return structured line-centered context snippets for each match.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Python identifier to find, such as Client or run_agent."},
                "path": {"type": "string", "description": "Optional project-relative file or directory scope."},
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
]
