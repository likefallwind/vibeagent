from __future__ import annotations

from typing import Any


READING_INSPECTION_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "file_info",
        "description": "Inspect project paths without reading full content. Returns existence, type, byte size, text line count, and binary detection.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 50,
                    "items": {"type": "string"},
                    "description": "Project-relative file or directory paths to inspect.",
                }
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
    {
        "name": "image_info",
        "description": "Inspect project-relative PNG, JPEG, GIF, or WebP image files without reading full binary payload. Returns format, byte size, and dimensions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 20,
                    "items": {"type": "string"},
                    "description": "Project-relative image file paths to inspect.",
                }
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
]
