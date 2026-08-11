from __future__ import annotations

from typing import Any

from .action_parsing_helpers import ActionParseError
from .types import CheckGitHubPrCreateAction, GitHubPrCreateAction


GITHUB_ACTION_TYPES = {"check_github_pr_create", "github_pr_create"}


def parse_github_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in GITHUB_ACTION_TYPES:
        return None
    title = value.get("title")
    body = value.get("body", "")
    base = value.get("base")
    remote = value.get("remote")
    draft = value.get("draft", False)
    if not isinstance(title, str) or not title.strip():
        raise ActionParseError(f"{action_type} action requires a non-empty title.", raw)
    if len(title) > 256 or "\n" in title or "\r" in title:
        raise ActionParseError(f"{action_type} title must be a single-line string of at most 256 characters.", raw)
    if not isinstance(body, str) or len(body) > 65_536:
        raise ActionParseError(f"{action_type} body must be a string of at most 65536 characters.", raw)
    for field_name, field in (("base", base), ("remote", remote)):
        if field is not None and (not isinstance(field, str) or not field.strip()):
            raise ActionParseError(f"{action_type} {field_name} must be a non-empty string when provided.", raw)
    if not isinstance(draft, bool):
        raise ActionParseError(f"{action_type} draft must be a boolean.", raw)
    options = dict(title=title.strip(), body=body, base=base.strip() if isinstance(base, str) else None, remote=remote.strip() if isinstance(remote, str) else None, draft=draft)
    if action_type == "check_github_pr_create":
        return CheckGitHubPrCreateAction(type="check_github_pr_create", **options)
    return GitHubPrCreateAction(type="github_pr_create", **options)
