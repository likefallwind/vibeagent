from __future__ import annotations

from typing import Any


GIT_SYNC_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "check_git_fetch",
        "description": "Validate which git remote would be fetched and report current ahead/behind state without contacting the remote.",
        "input_schema": {
            "type": "object",
            "properties": {
                "remote": {
                    "type": "string",
                    "description": "Remote name to fetch, such as origin. If omitted, the single configured remote is selected.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "git_fetch",
        "description": "Run git fetch --prune for one configured remote. Requires approval and may contact the remote.",
        "input_schema": {
            "type": "object",
            "properties": {
                "remote": {
                    "type": "string",
                    "description": "Remote name to fetch, such as origin. If omitted, the single configured remote is selected.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "check_git_pull",
        "description": "Validate whether the current branch can be updated from its upstream with git pull --ff-only without changing files.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "git_pull",
        "description": "Update the current branch from its configured upstream using git pull --ff-only. Requires approval, a clean worktree, and no divergent local commits.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "check_git_push",
        "description": "Validate whether the current branch can be pushed to its configured upstream without changing local or remote refs.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "git_push",
        "description": "Push the current branch to its configured upstream. Requires approval, a clean worktree, ahead commits, and no cached behind state. Does not force push.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
]
