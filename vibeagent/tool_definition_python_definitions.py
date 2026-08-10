from __future__ import annotations

from typing import Any


PYTHON_DEFINITION_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "python_definitions",
        "description": "Find Python class/function definitions and return focused source excerpts without executing code.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Python identifier or dotted identifier to inspect, such as run_agent or Runner.run.",
                },
                "path": {"type": "string", "description": "Optional workspace Python file or directory scope."},
                "max_matches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "description": "Maximum definition count to return. Defaults to 50.",
                },
                "max_lines": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000,
                    "description": "Maximum source lines to include for each definition. Defaults to 120.",
                },
            },
            "required": ["symbol"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_replace_python_definition",
        "description": "Validate replacing exactly one Python class/function definition by symbol without changing files. Returns the diff that would be applied.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Python definition name or dotted qualified name, such as run_agent or Runner.run.",
                },
                "content": {
                    "type": "string",
                    "description": "Replacement source text for the full definition, with indentation appropriate for its location.",
                },
                "path": {"type": "string", "description": "Optional workspace Python file or directory scope."},
            },
            "required": ["symbol", "content"],
            "additionalProperties": False,
        },
    },
    {
        "name": "replace_python_definition",
        "description": "Replace exactly one Python class/function definition by symbol after validating the resulting file parses.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Python definition name or dotted qualified name, such as run_agent or Runner.run.",
                },
                "content": {
                    "type": "string",
                    "description": "Replacement source text for the full definition, with indentation appropriate for its location.",
                },
                "path": {"type": "string", "description": "Optional workspace Python file or directory scope."},
            },
            "required": ["symbol", "content"],
            "additionalProperties": False,
        },
    },
]
