from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .github_pr_runtime import parse_github_repository
from .workspace_core import RunWorkspace
from .workspace_git_remote_ops import read_git_upstream_parts
from .workspace_git_utils import redact_git_text, run_readonly_git


MAX_GH_RESPONSE_BYTES = 2_000_000
MAX_PR_BODY_CHARS = 20_000
MAX_ITEM_BODY_CHARS = 8_000
MAX_COMMENTS = 100
MAX_REVIEWS = 50
MAX_CHECKS = 100
MAX_FILES = 200
_PR_URL = re.compile(r"https://github\.com/[^/\s]+/[^/\s]+/pull/\d+/?$", re.IGNORECASE)

_VIEW_FIELDS = ",".join(
    (
        "additions",
        "author",
        "baseRefName",
        "body",
        "changedFiles",
        "comments",
        "deletions",
        "files",
        "headRefName",
        "isDraft",
        "latestReviews",
        "mergeStateStatus",
        "mergeable",
        "number",
        "reviewDecision",
        "state",
        "statusCheckRollup",
        "title",
        "url",
    )
)


def read_github_pr_context(
    workspace: RunWorkspace,
    *,
    pr: str | None = None,
    remote: str | None = None,
) -> dict[str, Any]:
    repository, error = select_local_github_repository(workspace, remote)
    if error:
        return _failure(error)
    selector, error = normalize_pr_selector(workspace, pr)
    if error:
        return _failure(error, repository=repository)
    executable = shutil.which("gh")
    if executable is None:
        return _failure("GitHub CLI executable 'gh' was not found.", repository=repository)

    command = [executable, "pr", "view"]
    if selector:
        command.append(selector)
    command.extend(["--repo", repository, "--json", _VIEW_FIELDS])
    payload, error = _run_gh_json(command, workspace.root)
    if error:
        return _failure(error, repository=repository)
    if not isinstance(payload, dict):
        return _failure("gh pr view returned a JSON value that was not an object.", repository=repository)
    number = _integer(payload.get("number"))
    if number < 1:
        return _failure("gh pr view did not return a valid pull request number.", repository=repository)

    inline_command = [
        executable,
        "api",
        f"repos/{repository}/pulls/{number}/comments?per_page={MAX_COMMENTS}",
    ]
    inline_payload, error = _run_gh_json(inline_command, workspace.root)
    if error:
        return _failure(error, repository=repository)
    if not isinstance(inline_payload, list):
        return _failure("gh api returned inline pull request comments in an invalid format.", repository=repository)

    comments_source = _list(payload.get("comments"))
    # Keep line-specific review feedback ahead of general discussion when the
    # bounded result must omit older comments.
    comments = [_comment(item, "inline") for item in inline_payload]
    comments.extend(_comment(item, "comment") for item in comments_source)
    reviews_source = _list(payload.get("latestReviews"))
    checks_source = _list(payload.get("statusCheckRollup"))
    files_source = _list(payload.get("files"))
    comments, comments_truncated = _bounded(comments, MAX_COMMENTS)
    reviews, reviews_truncated = _bounded([_review(item) for item in reviews_source], MAX_REVIEWS)
    checks, checks_truncated = _bounded([_check(item) for item in checks_source], MAX_CHECKS)
    files, files_truncated = _bounded([_file(item) for item in files_source], MAX_FILES)
    return {
        "ok": True,
        "repository": repository,
        "number": number,
        "url": _text(payload.get("url"), 2_000),
        "title": _text(payload.get("title"), 1_000),
        "body": _text(payload.get("body"), MAX_PR_BODY_CHARS),
        "author": _author(payload.get("author")),
        "state": _text(payload.get("state"), 100),
        "is_draft": bool(payload.get("isDraft", False)),
        "head": _text(payload.get("headRefName"), 500),
        "base": _text(payload.get("baseRefName"), 500),
        "additions": _integer(payload.get("additions")),
        "deletions": _integer(payload.get("deletions")),
        "changed_files": _integer(payload.get("changedFiles")),
        "mergeable": _text(payload.get("mergeable"), 100),
        "merge_state": _text(payload.get("mergeStateStatus"), 100),
        "review_decision": _text(payload.get("reviewDecision"), 100),
        "comments": comments,
        "comments_total": len(comments_source) + len(inline_payload),
        "comments_truncated": comments_truncated,
        "reviews": reviews,
        "reviews_total": len(reviews_source),
        "reviews_truncated": reviews_truncated,
        "checks": checks,
        "checks_total": len(checks_source),
        "checks_truncated": checks_truncated,
        "files": files,
        "files_total": len(files_source),
        "files_truncated": files_truncated,
        "message": (
            f"Read GitHub pull request #{number}: {len(comments)} comment(s), "
            f"{len(reviews)} latest review(s), {len(checks)} check(s), and {len(files)} file(s)."
        ),
    }


def select_local_github_repository(workspace: RunWorkspace, remote: str | None) -> tuple[str, str | None]:
    requested = remote.strip() if isinstance(remote, str) else ""
    if remote is not None and not requested:
        return "", "GitHub remote must be non-empty when provided."
    if not requested:
        branch = run_readonly_git(workspace.root, ["branch", "--show-current"])
        branch_name = branch.stdout.strip() if branch.ok else ""
        upstream = read_git_upstream_parts(workspace, branch_name) if branch_name else {"ok": False}
        requested = str(upstream.get("remote", "")) if upstream.get("ok") else ""
    if not requested:
        remotes = run_readonly_git(workspace.root, ["remote"])
        names = []
        for name in sorted(set(remotes.stdout.splitlines() if remotes.ok else [])):
            url = run_readonly_git(workspace.root, ["remote", "get-url", name])
            if url.ok and parse_github_repository(url.stdout) is not None:
                names.append(name)
        if len(names) != 1:
            return "", "Could not select one GitHub remote; configure an upstream or provide remote explicitly."
        requested = names[0]
    url = run_readonly_git(workspace.root, ["remote", "get-url", requested])
    parsed = parse_github_repository(url.stdout) if url.ok else None
    if parsed is None:
        return "", f"Git remote {requested!r} is missing or is not a GitHub repository."
    return f"{parsed[0]}/{parsed[1]}", None


def normalize_pr_selector(workspace: RunWorkspace, pr: str | None) -> tuple[str, str | None]:
    if pr is None:
        return "", None
    selector = pr.strip()
    if not selector:
        return "", "Pull request selector must be non-empty when provided."
    if len(selector) > 500 or any(ord(char) < 32 for char in selector):
        return "", "Pull request selector is too long or contains control characters."
    if selector.isdigit():
        return (selector, None) if int(selector) > 0 else ("", "Pull request number must be positive.")
    if _PR_URL.fullmatch(selector):
        return selector.rstrip("/"), None
    if selector.startswith("-"):
        return "", "Pull request branch selector cannot start with '-'."
    valid = run_readonly_git(workspace.root, ["check-ref-format", "--branch", selector])
    if not valid.ok:
        return "", "Pull request selector must be a positive number, GitHub PR URL, or valid branch name."
    return selector, None


def _run_gh_json(command: list[str], cwd: Path) -> tuple[Any, str | None]:
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        try:
            completed = subprocess.run(
                command,
                cwd=cwd,
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                timeout=60,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            return None, f"GitHub CLI failed: {redact_git_text(str(error))}"
        if stdout.tell() > MAX_GH_RESPONSE_BYTES or stderr.tell() > MAX_GH_RESPONSE_BYTES:
            return None, f"GitHub CLI response exceeded the {MAX_GH_RESPONSE_BYTES}-byte safety limit."
        stdout.seek(0)
        stderr.seek(0)
        raw_stdout = stdout.read().decode("utf-8", errors="replace")
        raw_stderr = stderr.read().decode("utf-8", errors="replace")
    if completed.returncode != 0:
        return None, redact_git_text(raw_stderr or raw_stdout or "GitHub CLI request failed.")[:4_000]
    try:
        return json.loads(raw_stdout), None
    except json.JSONDecodeError as error:
        return None, f"GitHub CLI returned invalid JSON: {error}"


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
        "is_draft": False,
        "head": "",
        "base": "",
        "additions": 0,
        "deletions": 0,
        "changed_files": 0,
        "mergeable": "",
        "merge_state": "",
        "review_decision": "",
        "comments": [],
        "comments_total": 0,
        "comments_truncated": False,
        "reviews": [],
        "reviews_total": 0,
        "reviews_truncated": False,
        "checks": [],
        "checks_total": 0,
        "checks_truncated": False,
        "files": [],
        "files_total": 0,
        "files_truncated": False,
        "message": message,
    }


def _comment(value: object, kind: str) -> dict[str, Any]:
    item = value if isinstance(value, dict) else {}
    line = item.get("line", item.get("original_line"))
    return {
        "kind": kind,
        "author": _author(item.get("author", item.get("user"))),
        "body": _text(item.get("body"), MAX_ITEM_BODY_CHARS),
        "created_at": _text(item.get("createdAt", item.get("created_at")), 200),
        "url": _text(item.get("url", item.get("html_url")), 2_000),
        "path": _text(item.get("path"), 2_000),
        "line": _integer(line) or None,
    }


def _review(value: object) -> dict[str, Any]:
    item = value if isinstance(value, dict) else {}
    return {
        "author": _author(item.get("author")),
        "state": _text(item.get("state"), 100),
        "body": _text(item.get("body"), MAX_ITEM_BODY_CHARS),
        "submitted_at": _text(item.get("submittedAt"), 200),
        "url": _text(item.get("url"), 2_000),
    }


def _check(value: object) -> dict[str, Any]:
    item = value if isinstance(value, dict) else {}
    state = _text(_first(item.get("conclusion"), item.get("status"), item.get("state")), 100)
    return {
        "name": _text(item.get("name", item.get("context")), 500),
        "state": state,
        "bucket": _check_bucket(state),
        "workflow": _text(item.get("workflowName", item.get("workflow")), 500),
        "link": _text(item.get("detailsUrl", item.get("targetUrl")), 2_000),
    }


def _file(value: object) -> dict[str, Any]:
    item = value if isinstance(value, dict) else {}
    return {
        "path": _text(item.get("path"), 2_000),
        "additions": _integer(item.get("additions")),
        "deletions": _integer(item.get("deletions")),
    }


def _check_bucket(state: str) -> str:
    normalized = state.lower()
    if normalized in {"success", "neutral"}:
        return "pass"
    if normalized in {"failure", "timed_out", "action_required", "startup_failure"}:
        return "fail"
    if normalized in {"cancelled", "canceled"}:
        return "cancel"
    if normalized in {"skipped", "stale"}:
        return "skipping"
    return "pending"


def _author(value: object) -> str:
    if not isinstance(value, dict):
        return ""
    return _text(value.get("login", value.get("name")), 500)


def _text(value: object, maximum: int) -> str:
    return str(value or "")[:maximum]


def _integer(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def _list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _bounded(values: list[dict[str, Any]], maximum: int) -> tuple[list[dict[str, Any]], bool]:
    return values[:maximum], len(values) > maximum


def _first(*values: object) -> object:
    return next((value for value in values if value not in (None, "")), "")
