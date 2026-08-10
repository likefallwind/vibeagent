from __future__ import annotations

from typing import Any


PROJECT_METADATA_TOOL_DEFINITIONS: list[dict[str, Any]] = [
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
        "name": "project_skills",
        "description": "List bounded metadata for reusable personal, project, and plugin skills without loading skill instructions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_skills": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum skill metadata entries to return. Defaults to 100.",
                }
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "project_agents",
        "description": "List bounded metadata for custom personal, project, and plugin agent profiles without loading their system prompt bodies.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_agents": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum agent profile metadata entries to return. Defaults to 100.",
                }
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "skill",
        "description": "Load one named project SKILL.md after selecting it from the available project skill catalog.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Exact project skill directory name."},
                "max_bytes": {
                    "type": "integer",
                    "minimum": 200,
                    "maximum": 50000,
                    "description": "Maximum SKILL.md bytes to return. Defaults to 20000.",
                },
                "arguments": {
                    "type": "string",
                    "maxLength": 4000,
                    "description": "Optional task arguments to apply while following the skill.",
                },
            },
            "required": ["name"],
            "additionalProperties": False,
        },
    },
    {
        "name": "Skill",
        "description": "Claude-compatible alias for loading one named project skill with optional arguments.",
        "input_schema": {
            "type": "object",
            "properties": {
                "skill": {"type": "string", "description": "Exact project skill directory name."},
                "args": {"type": "string", "maxLength": 4000, "description": "Optional skill arguments."},
                "max_bytes": {"type": "integer", "minimum": 200, "maximum": 50000},
            },
            "required": ["skill"],
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
