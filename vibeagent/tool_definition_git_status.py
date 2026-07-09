from __future__ import annotations

from typing import Any


GIT_STATUS_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "git_status",
        "description": "Read git status in short format for the current project.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "git_conflicts",
        "description": "Scan for merge/rebase conflicts by reading unmerged git index entries and conflict marker lines in project text files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Optional project-relative file or directory to scan."},
                "max_markers": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000,
                    "description": "Maximum conflict marker entries to return. Defaults to 200.",
                },
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10000,
                    "description": "Maximum project text files to scan for conflict markers. Defaults to 5000.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "git_info",
        "description": "Read git repository identity and collaboration state: branch, HEAD, upstream, ahead/behind counts, remotes, and short status. Does not fetch from the network.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "git_changes",
        "description": "Read a structured summary of changed git files, including status and staged/unstaged insertion/deletion counts.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "git_branches",
        "description": "List local git branches and the current branch without fetching from the network.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_branches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum local branch count to return. Defaults to 100.",
                },
            },
            "additionalProperties": False,
        },
    },
]
