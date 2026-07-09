from __future__ import annotations

from typing import Any

from .tool_definition_output_schema import COMMAND_OUTPUT_EXTRACTION_PROPERTIES


PROJECT_TEST_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "related_tests",
        "description": "Suggest likely related test files for explicit project paths or the current git changes without running tests.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional project-relative source or test paths. Defaults to current git changed files.",
                },
                "max_paths": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum target path count to analyze. Defaults to 100.",
                },
                "max_candidates": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000,
                    "description": "Maximum related test candidate count to return. Defaults to 200.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "focused_test_commands",
        "description": "Suggest focused test commands for explicit project paths or the current git changes by mapping likely related test files to runnable commands without running them.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional project-relative source or test paths. Defaults to current git changed files.",
                },
                "max_paths": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum target path count to analyze. Defaults to 100.",
                },
                "max_candidates": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000,
                    "description": "Maximum related test candidate count to consider. Defaults to 200.",
                },
                "max_commands": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum focused test command count to return. Defaults to 50.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "check_focused_test_commands",
        "description": "Preflight focused test commands inferred from explicit project paths or the current git changes without running them.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional project-relative source or test paths. Defaults to current git changed files.",
                },
                "max_paths": {"type": "integer", "minimum": 1, "maximum": 500},
                "max_candidates": {"type": "integer", "minimum": 1, "maximum": 1000},
                "max_commands": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "description": "Maximum focused test command count to preflight. Defaults to 10.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "run_focused_test_commands",
        "description": "Run focused test commands inferred from explicit project paths or the current git changes after approval. Stops at the first failure by default.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional project-relative source or test paths. Defaults to current git changed files.",
                },
                "max_paths": {"type": "integer", "minimum": 1, "maximum": 500},
                "max_candidates": {"type": "integer", "minimum": 1, "maximum": 1000},
                "max_commands": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "description": "Maximum focused test command count to run. Defaults to 10.",
                },
                "timeout_ms": {
                    "type": "integer",
                    "minimum": 100,
                    "maximum": 600000,
                    "description": "Optional timeout in milliseconds per command. Defaults to the agent command timeout.",
                },
                "max_output_chars": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 50000,
                    "description": "Optional stdout/stderr character cap per command. Defaults to 12000.",
                },
                "stop_on_failure": {
                    "type": "boolean",
                    "description": "Stop after the first failing command. Defaults to true.",
                },
                **COMMAND_OUTPUT_EXTRACTION_PROPERTIES,
            },
            "additionalProperties": False,
        },
    },
]
