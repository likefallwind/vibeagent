from __future__ import annotations

from typing import Any


PYTHON_CALL_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "python_calls",
        "description": "Find Python call sites for a function, method, or dotted callable name without executing code.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Python callable name to find, such as run_agent, self.run, or client.complete.",
                },
                "path": {"type": "string", "description": "Optional project-relative Python file or directory scope."},
                "max_matches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum call site count to return. Defaults to 200.",
                },
            },
            "required": ["symbol"],
            "additionalProperties": False,
        },
    },
    {
        "name": "python_call_graph",
        "description": "Inspect Python caller-to-callee edges in a file or directory without executing code.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Optional project-relative Python file or directory scope."},
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum Python file count to inspect. Defaults to 100.",
                },
                "max_edges": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 2000,
                    "description": "Maximum call graph edge count to return. Defaults to 500.",
                },
            },
            "additionalProperties": False,
        },
    },
]
