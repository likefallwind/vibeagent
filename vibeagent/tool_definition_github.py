from __future__ import annotations

from typing import Any


_PR_PROPERTIES: dict[str, Any] = {
    "title": {"type": "string", "description": "Pull request title, at most 256 characters."},
    "body": {"type": "string", "description": "Pull request description in Markdown."},
    "base": {"type": "string", "description": "Target branch. Defaults to the target remote's cached default branch."},
    "remote": {"type": "string", "description": "Target GitHub remote. Defaults to the current branch upstream remote."},
    "draft": {"type": "boolean", "description": "Create the pull request as a draft."},
}

GITHUB_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "github_pr_ci_logs",
        "description": "Read failed checks for a GitHub pull request and bounded failed-step logs for GitHub Actions runs through gh. Contacts GitHub and requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pr": {
                    "type": "string",
                    "description": "Optional positive PR number, GitHub pull request URL, or branch. Defaults to the current branch PR.",
                },
                "remote": {
                    "type": "string",
                    "description": "Optional local GitHub remote used to select the repository.",
                },
                "max_runs": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10,
                    "description": "Maximum distinct GitHub Actions runs whose failed-step logs are fetched.",
                },
                "max_output_chars": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 100000,
                    "description": "Maximum returned log characters per Actions run.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "github_pr_context",
        "description": "Read a GitHub pull request's metadata, comments, latest reviews, inline review comments, changed files, and CI status through gh. Contacts GitHub and requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pr": {
                    "type": "string",
                    "description": "Optional positive PR number, GitHub pull request URL, or branch. Defaults to the current branch PR.",
                },
                "remote": {
                    "type": "string",
                    "description": "Optional local GitHub remote used to select the repository.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "check_github_pr_create",
        "description": "Locally validate a GitHub pull request without contacting GitHub. Requires a fully pushed branch and cached base ref.",
        "input_schema": {"type": "object", "properties": _PR_PROPERTIES, "required": ["title"], "additionalProperties": False},
    },
    {
        "name": "github_pr_create",
        "description": "Create a GitHub pull request with gh after local validation. Requires approval and a matching check_github_pr_create preview.",
        "input_schema": {"type": "object", "properties": _PR_PROPERTIES, "required": ["title"], "additionalProperties": False},
    },
]
