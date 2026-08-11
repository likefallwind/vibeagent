from __future__ import annotations

import re
import shutil
from typing import Any
from urllib.parse import urlparse

from .github_pr_context_runtime import run_gh_json, select_local_github_repository
from .workspace_core import RunWorkspace


MAX_ISSUE_BODY_CHARS = 20_000
MAX_COMMENT_BODY_CHARS = 8_000
MAX_COMMENTS = 100
MAX_LABELS = 100
MAX_ASSIGNEES = 100
_ISSUE_URL = re.compile(
    r"https://github\.com/(?P<owner>[^/\s]+)/(?P<repo>[^/\s]+)/issues/(?P<number>[1-9]\d*)/?$",
    re.IGNORECASE,
)
_VIEW_FIELDS = ",".join(
    (
        "assignees",
        "author",
        "body",
        "comments",
        "createdAt",
        "labels",
        "milestone",
        "number",
        "state",
        "stateReason",
        "title",
        "updatedAt",
        "url",
    )
)


def read_github_issue_context(
    workspace: RunWorkspace,
    *,
    issue: str,
    remote: str | None = None,
) -> dict[str, Any]:
    repository, error = select_local_github_repository(workspace, remote)
    if error:
        return _failure(error)
    selector, error = normalize_issue_selector(issue, repository)
    if error:
        return _failure(error, repository=repository)
    executable = shutil.which("gh")
    if executable is None:
        return _failure("GitHub CLI executable 'gh' was not found.", repository=repository)

    command = [
        executable,
        "issue",
        "view",
        selector,
        "--repo",
        repository,
        "--json",
        _VIEW_FIELDS,
    ]
    payload, error = run_gh_json(command, workspace.root)
    if error:
        return _failure(error, repository=repository)
    if not isinstance(payload, dict):
        return _failure("gh issue view returned a JSON value that was not an object.", repository=repository)
    number = _integer(payload.get("number"))
    if number < 1:
        return _failure("gh issue view did not return a valid issue number.", repository=repository)

    comments_source = _list(payload.get("comments"))
    labels_source = _list(payload.get("labels"))
    assignees_source = _list(payload.get("assignees"))
    comments, comments_truncated = _bounded(
        [_comment(item) for item in comments_source],
        MAX_COMMENTS,
    )
    labels = [name for item in labels_source[:MAX_LABELS] if (name := _name(item))]
    labels_truncated = len(labels_source) > MAX_LABELS
    assignees = [name for item in assignees_source[:MAX_ASSIGNEES] if (name := _author(item))]
    assignees_truncated = len(assignees_source) > MAX_ASSIGNEES
    milestone = payload.get("milestone")
    milestone_title = _name(milestone)
    return {
        "ok": True,
        "repository": repository,
        "number": number,
        "url": _text(payload.get("url"), 2_000),
        "title": _text(payload.get("title"), 1_000),
        "body": _text(payload.get("body"), MAX_ISSUE_BODY_CHARS),
        "author": _author(payload.get("author")),
        "state": _text(payload.get("state"), 100),
        "state_reason": _text(payload.get("stateReason"), 100),
        "created_at": _text(payload.get("createdAt"), 200),
        "updated_at": _text(payload.get("updatedAt"), 200),
        "milestone": milestone_title,
        "labels": labels,
        "labels_total": len(labels_source),
        "labels_truncated": labels_truncated,
        "assignees": assignees,
        "assignees_total": len(assignees_source),
        "assignees_truncated": assignees_truncated,
        "comments": comments,
        "comments_total": len(comments_source),
        "comments_truncated": comments_truncated,
        "message": (
            f"Read GitHub issue #{number}: {len(comments)} comment(s), "
            f"{len(labels)} label(s), and {len(assignees)} assignee(s)."
        ),
    }


def normalize_issue_selector(issue: str, repository: str) -> tuple[str, str | None]:
    selector = issue.strip() if isinstance(issue, str) else ""
    if not selector:
        return "", "Issue selector must be non-empty."
    if len(selector) > 500 or any(ord(char) < 32 for char in selector):
        return "", "Issue selector is too long or contains control characters."
    if selector.isdigit():
        return (selector, None) if int(selector) > 0 else ("", "Issue number must be positive.")
    match = _ISSUE_URL.fullmatch(selector)
    if match is None:
        return "", "Issue selector must be a positive number or GitHub issue URL."
    selected_repository = f"{match.group('owner')}/{match.group('repo')}"
    if selected_repository.casefold() != repository.casefold():
        return "", f"Issue URL repository {selected_repository!r} does not match local repository {repository!r}."
    parsed = urlparse(selector)
    normalized = f"https://github.com{parsed.path.rstrip('/')}"
    return normalized, None


def _failure(message: str, *, repository: str = "") -> dict[str, Any]:
    return {
        "ok": False,
        "repository": repository,
        "number": 0,
        "url": "",
        "title": "",
        "body": "",
        "author": "",
        "state": "",
        "state_reason": "",
        "created_at": "",
        "updated_at": "",
        "milestone": "",
        "labels": [],
        "labels_total": 0,
        "labels_truncated": False,
        "assignees": [],
        "assignees_total": 0,
        "assignees_truncated": False,
        "comments": [],
        "comments_total": 0,
        "comments_truncated": False,
        "message": message,
    }


def _comment(value: object) -> dict[str, Any]:
    item = value if isinstance(value, dict) else {}
    return {
        "author": _author(item.get("author")),
        "body": _text(item.get("body"), MAX_COMMENT_BODY_CHARS),
        "created_at": _text(item.get("createdAt"), 200),
        "url": _text(item.get("url"), 2_000),
    }


def _author(value: object) -> str:
    if not isinstance(value, dict):
        return ""
    return _text(value.get("login", value.get("name")), 500)


def _name(value: object) -> str:
    if not isinstance(value, dict):
        return ""
    return _text(value.get("name", value.get("title")), 500)


def _text(value: object, maximum: int) -> str:
    return str(value or "")[:maximum]


def _integer(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def _list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _bounded(values: list[Any], maximum: int) -> tuple[list[Any], bool]:
    return values[:maximum], len(values) > maximum
