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
