from __future__ import annotations

from typing import Any

from .tool_definition_output_schema import COMMAND_OUTPUT_EXTRACTION_PROPERTIES


GIT_REVIEW_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "check_git_commit",
        "description": "Validate that currently staged changes can be committed with the provided message without creating a commit.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Commit message to validate.",
                },
            },
            "required": ["message"],
            "additionalProperties": False,
        },
    },
    {
        "name": "git_commit",
        "description": "Commit currently staged changes with a message. Uses --no-verify and does not run git hooks. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Commit message, up to 500 characters.",
                },
            },
            "required": ["message"],
            "additionalProperties": False,
        },
    },
    {
        "name": "review_changes",
        "description": "Run a read-only pre-final review: structured changed files, git diff whitespace checks, and Python syntax checks for changed Python files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum changed file and Python file count to report. Defaults to 200.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "final_review",
        "description": "Run a read-only final handoff review that summarizes blocking issues, warnings, changed files, suggested verification commands, and focused test commands inferred from changed files before finishing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum changed file count to report. Defaults to 200.",
                },
                "max_checks": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum suggested verification command count to report. Defaults to 10.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "suggest_checks",
        "description": "Suggest relevant test, build, lint, and syntax-check commands from project metadata and current changed files without running them, including whether each command's main executable is available on PATH.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_commands": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum suggested command count to return. Defaults to 20.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "check_suggested_checks",
        "description": "Preflight the project's suggested test, build, lint, and syntax-check commands without running them.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_commands": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10,
                    "description": "Maximum suggested command count to preflight. Defaults to 10.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "run_suggested_checks",
        "description": "Run the project's available suggested test, build, lint, and syntax-check commands after approval. Stops at the first failure by default.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_commands": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10,
                    "description": "Maximum suggested command count to run. Defaults to 10.",
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
