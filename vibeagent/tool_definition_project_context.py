from __future__ import annotations

from typing import Any

from .tool_categories import valid_tool_categories
from .tool_definition_output_schema import COMMAND_OUTPUT_EXTRACTION_PROPERTIES


PROJECT_CONTEXT_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "project_commands",
        "description": "List project-defined commands from package.json scripts, pyproject.toml console scripts, and Makefile targets without running them, including cwd and executable availability.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_commands": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum command count to return. Defaults to 100.",
                },
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "description": "Maximum command metadata files to scan. Defaults to 30.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "tool_search",
        "description": "Search the model tool catalog by tool name, category, description, required inputs, or input property names without executing project actions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search terms such as a rough capability, tool name fragment, input property, or category.",
                },
                "max_matches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum matching tools to return. Defaults to 20.",
                },
                "category": {
                    "type": "string",
                    "enum": list(valid_tool_categories()),
                    "description": "Optional category filter.",
                },
                "approval_required": {
                    "type": "boolean",
                    "description": "Optional approval filter. True returns approval-gated tools; false returns read-only tools.",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
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
    {
        "name": "project_manifests",
        "description": "Read project manifest metadata and dependency/script groups from package.json and pyproject.toml files without executing code.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "description": "Maximum manifest file count to scan. Defaults to 30.",
                },
                "max_items": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 2000,
                    "description": "Maximum dependency/script item count to return across manifests. Defaults to 500.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "project_instructions",
        "description": "Read project instruction sources from AGENTS.md and CLAUDE.md files, including scope, file metadata, truncation status, and bounded instruction text.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "description": "Maximum instruction file count to scan. Defaults to 20.",
                },
                "max_bytes": {
                    "type": "integer",
                    "minimum": 200,
                    "maximum": 50000,
                    "description": "Maximum instruction text bytes to return. Defaults to 12000.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "project_todos",
        "description": "Scan project text files for TODO, FIXME, HACK, XXX, and BUG markers without executing code.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Optional project-relative file or directory scope."},
                "max_items": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum TODO marker count to return. Defaults to 100.",
                },
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5000,
                    "description": "Maximum project file count to scan. Defaults to 1000.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "project_overview",
        "description": "Read a compact project orientation bundle without executing code: shallow repo map, git identity/status, manifest summaries, project commands, suggested checks, and runtime tool availability.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "description": "Maximum repo-map file/tree entries to report. Defaults to 80.",
                },
                "max_commands": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum project command count to report. Defaults to 20.",
                },
                "max_checks": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "description": "Maximum suggested check count to report. Defaults to 10.",
                },
                "max_manifests": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "description": "Maximum manifest file count to scan. Defaults to 10.",
                },
            },
            "additionalProperties": False,
        },
    },
]
