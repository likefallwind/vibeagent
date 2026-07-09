from __future__ import annotations

from typing import Any


GIT_STASH_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "git_stashes",
        "description": "List recent git stash entries without changing the repository.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_entries": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum stash entry count to return. Defaults to 20.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "check_git_stash",
        "description": "Preview saving current non-runtime changes to git stash without changing the repository.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Optional stash message. Defaults to 'vibeagent stash'."},
                "include_untracked": {
                    "type": "boolean",
                    "description": "Also stash non-runtime untracked files. Defaults to false.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "git_stash",
        "description": "Save current non-runtime changes to git stash. Requires approval. Excludes .vibeagent runtime files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Optional stash message. Defaults to 'vibeagent stash'."},
                "include_untracked": {
                    "type": "boolean",
                    "description": "Also stash non-runtime untracked files. Defaults to false.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "check_git_stash_apply",
        "description": "Preview applying one stash entry to a clean worktree without changing files or dropping the stash.",
        "input_schema": {
            "type": "object",
            "properties": {
                "stash_ref": {"type": "string", "description": "Stash reference such as stash@{0}."},
            },
            "required": ["stash_ref"],
            "additionalProperties": False,
        },
    },
    {
        "name": "git_stash_apply",
        "description": "Apply one stash entry to a clean worktree. Requires approval. Does not drop the stash.",
        "input_schema": {
            "type": "object",
            "properties": {
                "stash_ref": {"type": "string", "description": "Stash reference such as stash@{0}."},
            },
            "required": ["stash_ref"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_git_stash_drop",
        "description": "Preview dropping one stash entry without changing the repository.",
        "input_schema": {
            "type": "object",
            "properties": {
                "stash_ref": {"type": "string", "description": "Stash reference such as stash@{0}."},
            },
            "required": ["stash_ref"],
            "additionalProperties": False,
        },
    },
    {
        "name": "git_stash_drop",
        "description": "Drop one stash entry after approval. This permanently removes the stash entry.",
        "input_schema": {
            "type": "object",
            "properties": {
                "stash_ref": {"type": "string", "description": "Stash reference such as stash@{0}."},
            },
            "required": ["stash_ref"],
            "additionalProperties": False,
        },
    },
]
