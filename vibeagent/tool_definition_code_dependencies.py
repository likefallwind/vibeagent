from __future__ import annotations

from typing import Any


CODE_DEPENDENCY_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "python_dependencies",
        "description": "Inspect Python imports without executing code, classifying local project modules versus external modules.",
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
                "max_imports": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 2000,
                    "description": "Maximum import entries to return across files. Defaults to 500.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "code_dependencies",
        "description": "Inspect imports, includes, and use statements in JavaScript, TypeScript, Go, Rust, Java, Kotlin, C, and C++ files without executing code.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Optional project-relative source file or directory scope."},
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum source file count to inspect. Defaults to 100.",
                },
                "max_imports": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 2000,
                    "description": "Maximum import/include/use entries to return across files. Defaults to 500.",
                },
            },
            "additionalProperties": False,
        },
    },
]
