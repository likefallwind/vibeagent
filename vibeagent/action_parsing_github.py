from __future__ import annotations

import re
from typing import Any

from .action_parsing_helpers import ActionParseError, parse_optional_positive_int
from .github_comment_runtime import validate_github_comment_body
from .types import (
    CheckGitHubIssueCommentAction,
    CheckGitHubPrCommentAction,
    CheckGitHubPrCreateAction,
    GitHubIssueCommentAction,
    GitHubIssueContextAction,
    GitHubPrCiLogsAction,
    GitHubPrCommentAction,
    GitHubPrContextAction,
    GitHubPrCreateAction,
)


GITHUB_ACTION_TYPES = {
    "github_issue_context",
    "check_github_issue_comment",
    "github_issue_comment",
    "check_github_pr_create",
    "github_pr_create",
    "github_pr_context",
    "github_pr_ci_logs",
    "check_github_pr_comment",
    "github_pr_comment",
}


def parse_github_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in GITHUB_ACTION_TYPES:
        return None
    if action_type in {"github_issue_context", "check_github_issue_comment", "github_issue_comment"}:
        selector = _parse_issue_selector(value.get("issue"), raw, str(action_type))
        remote = _parse_remote(value.get("remote"), raw, str(action_type))
        if action_type == "github_issue_context":
            return GitHubIssueContextAction(
                type="github_issue_context",
                issue=selector,
                remote=remote,
            )
        body = value.get("body")
        error = validate_github_comment_body(body, destination="issue")
        if error:
            raise ActionParseError(error, raw)
        assert isinstance(body, str)
        action_class = (
            CheckGitHubIssueCommentAction
            if action_type == "check_github_issue_comment"
            else GitHubIssueCommentAction
        )
        return action_class(
            type=action_type,
            body=body,
            issue=selector,
            remote=remote,
        )
    if action_type in {"check_github_pr_comment", "github_pr_comment"}:
        body = value.get("body")
        error = validate_github_comment_body(body, destination="pull request")
        if error:
            raise ActionParseError(error, raw)
        assert isinstance(body, str)
        pr, remote = _parse_pr_remote(value, raw, str(action_type))
        reply_to = parse_optional_positive_int(
            value.get("reply_to"),
            "reply_to",
            raw,
            maximum=9_223_372_036_854_775_807,
        )
        action_class = CheckGitHubPrCommentAction if action_type == "check_github_pr_comment" else GitHubPrCommentAction
        return action_class(
            type=action_type,
            body=body,
            pr=pr,
            remote=remote,
            reply_to=reply_to,
        )
    if action_type in {"github_pr_context", "github_pr_ci_logs"}:
        pr, remote = _parse_pr_remote(value, raw, str(action_type))
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
                pr=pr,
                remote=remote,
                max_runs=max_runs,
                max_output_chars=max_output_chars,
            )
        return GitHubPrContextAction(
            type="github_pr_context",
            pr=pr,
            remote=remote,
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


def _parse_pr_remote(value: dict[str, Any], raw: str, action_type: str) -> tuple[str | None, str | None]:
    pr = value.get("pr")
    if pr is not None and (not isinstance(pr, str) or not pr.strip()):
        raise ActionParseError(f"{action_type} pr must be a non-empty string when provided.", raw)
    if isinstance(pr, str) and (
        len(pr.strip()) > 500
        or pr.strip().startswith("-")
        or any(ord(char) < 32 for char in pr)
    ):
        raise ActionParseError(f"{action_type} pr is too long, starts with '-', or contains control characters.", raw)
    return (
        pr.strip() if isinstance(pr, str) else None,
        _parse_remote(value.get("remote"), raw, action_type),
    )


def _parse_remote(value: object, raw: str, action_type: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ActionParseError(f"{action_type} remote must be a non-empty string when provided.", raw)
    remote = value.strip()
    if len(remote) > 255 or remote.startswith("-") or any(ord(char) < 32 for char in remote):
        raise ActionParseError(f"{action_type} remote is invalid.", raw)
    return remote


def _parse_issue_selector(value: object, raw: str, action_type: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ActionParseError(f"{action_type} requires a non-empty issue selector.", raw)
    selector = value.strip()
    if (
        len(selector) > 500
        or any(ord(char) < 32 for char in selector)
        or not (
            selector.isdigit() and int(selector) > 0
            or re.fullmatch(
                r"https://github\.com/[^/\s]+/[^/\s]+/issues/[1-9]\d*/?",
                selector,
                re.IGNORECASE,
            )
        )
    ):
        raise ActionParseError(
            f"{action_type} issue must be a positive number or GitHub issue URL.",
            raw,
        )
    return selector.rstrip("/")
