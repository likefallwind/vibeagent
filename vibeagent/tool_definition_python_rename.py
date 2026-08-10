from __future__ import annotations

from typing import Any


PYTHON_RENAME_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "python_rename_preview",
        "description": "Preview an AST-guided Python identifier rename across files without writing changes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Simple Python identifier to rename."},
                "new_name": {"type": "string", "description": "Replacement simple Python identifier."},
                "path": {"type": "string", "description": "Optional workspace Python file or directory scope."},
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum Python file count to inspect. Defaults to 100.",
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
        "name": "python_rename",
        "description": "Apply an AST-guided Python identifier rename across files after validating updated files parse.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Simple Python identifier to rename."},
                "new_name": {"type": "string", "description": "Replacement simple Python identifier."},
                "path": {"type": "string", "description": "Optional workspace Python file or directory scope."},
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum Python file count to inspect. Defaults to 100.",
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
