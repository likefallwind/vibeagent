from __future__ import annotations

from typing import Any

from .action_parsing_helpers import ActionParseError, parse_optional_positive_int
from .types import CheckGitHubPrCreateAction, GitHubPrCiLogsAction, GitHubPrContextAction, GitHubPrCreateAction


GITHUB_ACTION_TYPES = {"check_github_pr_create", "github_pr_create", "github_pr_context", "github_pr_ci_logs"}


def parse_github_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in GITHUB_ACTION_TYPES:
        return None
    if action_type in {"github_pr_context", "github_pr_ci_logs"}:
        pr = value.get("pr")
        remote = value.get("remote")
        for field_name, field in (("pr", pr), ("remote", remote)):
            if field is not None and (not isinstance(field, str) or not field.strip()):
                raise ActionParseError(f"{action_type} {field_name} must be a non-empty string when provided.", raw)
        if isinstance(pr, str) and (
            len(pr.strip()) > 500
            or pr.strip().startswith("-")
            or any(ord(char) < 32 for char in pr)
        ):
            raise ActionParseError(f"{action_type} pr is too long, starts with '-', or contains control characters.", raw)
        if isinstance(remote, str) and (
            len(remote.strip()) > 255
            or remote.strip().startswith("-")
            or any(ord(char) < 32 for char in remote)
        ):
            raise ActionParseError(f"{action_type} remote is invalid.", raw)
        if action_type == "github_pr_ci_logs":
            max_runs = parse_optional_positive_int(value.get("max_runs", 3), "max_runs", raw, maximum=10) or 3
            max_output_chars = parse_optional_positive_int(
                value.get("max_output_chars", 30_000),
                "max_output_chars",
                raw,
                maximum=100_000,
            ) or 30_000
            if max_output_chars < 1_000:
                raise ActionParseError("github_pr_ci_logs max_output_chars must be at least 1000.", raw)
            return GitHubPrCiLogsAction(
                type="github_pr_ci_logs",
                pr=pr.strip() if isinstance(pr, str) else None,
                remote=remote.strip() if isinstance(remote, str) else None,
                max_runs=max_runs,
                max_output_chars=max_output_chars,
            )
        return GitHubPrContextAction(
            type="github_pr_context",
            pr=pr.strip() if isinstance(pr, str) else None,
            remote=remote.strip() if isinstance(remote, str) else None,
        )
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
        if isinstance(field, str) and (
            len(field.strip()) > 255
            or field.strip().startswith("-")
            or any(ord(char) < 32 for char in field)
        ):
            raise ActionParseError(f"{action_type} {field_name} is invalid.", raw)
    if any(ord(char) < 32 and char not in "\n\r\t" for char in title + body):
        raise ActionParseError(f"{action_type} title and body cannot contain control characters.", raw)
    if not isinstance(draft, bool):
        raise ActionParseError(f"{action_type} draft must be a boolean.", raw)
    options = dict(title=title.strip(), body=body, base=base.strip() if isinstance(base, str) else None, remote=remote.strip() if isinstance(remote, str) else None, draft=draft)
    if action_type == "check_github_pr_create":
        return CheckGitHubPrCreateAction(type="check_github_pr_create", **options)
    return GitHubPrCreateAction(type="github_pr_create", **options)
