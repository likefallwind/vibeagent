from __future__ import annotations

from typing import Any

from .tool_definition_output_schema import COMMAND_OUTPUT_EXTRACTION_PROPERTIES


PROJECT_TEST_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "related_tests",
        "description": "Suggest related test files without running tests.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "max_paths": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                },
                "max_candidates": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000,
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "focused_test_commands",
        "description": "Suggest focused test commands without running them.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "max_paths": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                },
                "max_candidates": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000,
                },
                "max_commands": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "check_focused_test_commands",
        "description": "Preflight inferred focused test commands without running them.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "max_paths": {"type": "integer", "minimum": 1, "maximum": 500},
                "max_candidates": {"type": "integer", "minimum": 1, "maximum": 1000},
                "max_commands": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "run_focused_test_commands",
        "description": "Run inferred focused test commands after approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "max_paths": {"type": "integer", "minimum": 1, "maximum": 500},
                "max_candidates": {"type": "integer", "minimum": 1, "maximum": 1000},
                "max_commands": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                },
                "timeout_ms": {
                    "type": "integer",
                    "minimum": 100,
                    "maximum": 600000,
                },
                "max_output_chars": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 50000,
                },
                "stop_on_failure": {
                    "type": "boolean",
                },
                **COMMAND_OUTPUT_EXTRACTION_PROPERTIES,
            },
            "additionalProperties": False,
        },
    },
]
