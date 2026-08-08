from __future__ import annotations

from typing import Any


GIT_WORKTREE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "EnterWorktree",
        "description": "Create an isolated git worktree and switch this agent session into it, or switch into an existing worktree from the same repository. Creating a worktree requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Optional safe name for a new worktree. A unique name is generated when omitted.",
                },
                "path": {
                    "type": "string",
                    "description": "Optional path of an existing registered worktree from the same repository.",
                },
            },
            "oneOf": [
                {"required": ["name"], "not": {"required": ["path"]}},
                {"required": ["path"], "not": {"required": ["name"]}},
                {"maxProperties": 0},
            ],
            "additionalProperties": False,
        },
    },
    {
        "name": "ExitWorktree",
        "description": "Switch this agent session from an isolated linked worktree back to the repository's main checkout. The linked worktree and all of its changes are preserved.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "check_git_switch",
        "description": "Validate switching to an existing local branch or creating a new local branch without changing HEAD.",
        "input_schema": {
            "type": "object",
            "properties": {
                "branch": {"type": "string", "description": "Local branch name to switch to or create."},
                "create": {
                    "type": "boolean",
                    "description": "Create the branch with git switch -c when true. Defaults to false.",
                },
            },
            "required": ["branch"],
            "additionalProperties": False,
        },
    },
    {
        "name": "git_switch",
        "description": "Switch to an existing local branch, or create and switch to a new local branch. Requires approval and a clean worktree.",
        "input_schema": {
            "type": "object",
            "properties": {
                "branch": {"type": "string", "description": "Local branch name to switch to or create."},
                "create": {
                    "type": "boolean",
                    "description": "Create the branch with git switch -c when true. Defaults to false.",
                },
            },
            "required": ["branch"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_git_stage",
        "description": "Validate staging one or more project-relative paths without changing the git index.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 100,
                    "items": {"type": "string"},
                    "description": "Project-relative paths to stage, such as src/app.py or tests.",
                },
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
    {
        "name": "git_stage",
        "description": "Stage one or more project-relative paths in the git index. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 100,
                    "items": {"type": "string"},
                    "description": "Project-relative paths to stage, such as src/app.py or tests.",
                },
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_git_unstage",
        "description": "Validate unstaging one or more project-relative paths without changing the git index.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 100,
                    "items": {"type": "string"},
                    "description": "Project-relative paths to unstage, such as src/app.py or tests.",
                },
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
    {
        "name": "git_unstage",
        "description": "Unstage one or more project-relative paths from the git index. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 100,
                    "items": {"type": "string"},
                    "description": "Project-relative paths to unstage, such as src/app.py or tests.",
                },
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_git_restore",
        "description": "Preview discarding unstaged changes for tracked project-relative paths without changing files or the git index.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 100,
                    "items": {"type": "string"},
                    "description": "Tracked project-relative paths whose unstaged changes would be restored from HEAD.",
                },
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
    {
        "name": "git_restore",
        "description": "Discard unstaged changes for tracked project-relative paths with git restore. Requires approval. Does not delete untracked files or change the git index.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 100,
                    "items": {"type": "string"},
                    "description": "Tracked project-relative paths whose unstaged changes should be restored from HEAD.",
                },
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
]
