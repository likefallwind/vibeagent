from __future__ import annotations

from typing import Any


LSP_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "LSP",
        "description": "Claude-compatible read-only code intelligence. Resolve definitions, implementations, references, hover context, and document/workspace symbols from a project file position or explicit symbol.",
        "input_schema": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": [
                        "goToDefinition",
                        "goToImplementation",
                        "findReferences",
                        "hover",
                        "documentSymbol",
                        "workspaceSymbol",
                    ],
                },
                "filePath": {"type": "string", "description": "Project-relative source file."},
                "line": {"type": "integer", "minimum": 0, "description": "One-based source line; zero also selects the first line."},
                "character": {"type": "integer", "minimum": 0, "description": "UTF-16 character offset; accepts zero- or one-based positions."},
                "query": {"type": "string", "description": "Optional explicit symbol, especially for workspaceSymbol."},
                "maxResults": {"type": "integer", "minimum": 1, "maximum": 200},
            },
            "required": ["operation"],
            "oneOf": [
                {
                    "properties": {
                        "operation": {
                            "enum": ["goToDefinition", "goToImplementation", "findReferences", "hover"]
                        }
                    },
                    "required": ["filePath", "line", "character"],
                },
                {
                    "properties": {
                        "operation": {
                            "enum": [
                                "goToDefinition",
                                "goToImplementation",
                                "findReferences",
                                "hover",
                                "workspaceSymbol",
                            ]
                        }
                    },
                    "required": ["query"],
                },
                {
                    "properties": {"operation": {"enum": ["documentSymbol"]}},
                    "required": ["filePath"],
                },
            ],
            "additionalProperties": False,
        },
    }
]
