from __future__ import annotations

import hashlib
import re
import shutil
from typing import Any

from .github_pr_context_runtime import (
    normalize_pr_selector,
    run_gh_json,
    run_gh_output,
    select_local_github_repository,
)
from .workspace_core import RunWorkspace
from .workspace_git_utils import redact_git_text


MAX_COMMENT_CHARS = 65_536
_COMMENT_URL = re.compile(r"https://github\.com/[^\s]+/pull/\d+#[^\s]+", re.IGNORECASE)


def preview_github_pr_comment(
    workspace: RunWorkspace,
    *,
    body: str,
    pr: str | None = None,
    remote: str | None = None,
    reply_to: int | None = None,
) -> dict[str, Any]:
    repository, error = select_local_github_repository(workspace, remote)
    selector, selector_error = normalize_pr_selector(workspace, pr)
    error = error or selector_error or _validate_comment(body, reply_to)
    target = github_pr_comment_target(pr, reply_to, body)
    result = {
        "ok": False,
        "repository": repository,
        "selector": selector or "current branch",
        "pr": pr,
        "remote": remote,
        "reply_to": reply_to,
        "body_chars": len(body),
        "body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        "comment_target": target,
        "message": error or "",
    }
    if error:
        return result
    if shutil.which("gh") is None:
        result["message"] = "GitHub CLI executable 'gh' was not found."
        return result
    result["ok"] = True
    destination = f"review comment {reply_to}" if reply_to is not None else "pull request discussion"
    result["message"] = f"Ready to post {len(body)} characters to {repository} {selector or 'current branch'} {destination}."
    return result


def create_github_pr_comment(workspace: RunWorkspace, **options: Any) -> dict[str, Any]:
    preview = preview_github_pr_comment(workspace, **options)
    if not preview["ok"]:
        return {**preview, "url": ""}
    executable = shutil.which("gh")
    if executable is None:
        return {**preview, "ok": False, "url": "", "message": "GitHub CLI executable 'gh' was not found."}
    body = str(options["body"])
    reply_to = options.get("reply_to")
    if isinstance(reply_to, int):
        number, error = _read_pr_number(
            executable,
            workspace,
            str(preview["repository"]),
            str(preview["selector"]),
        )
        if error:
            return {**preview, "ok": False, "url": "", "message": error}
        command = [
            executable,
            "api",
            "--method",
            "POST",
            f"repos/{preview['repository']}/pulls/{number}/comments/{reply_to}/replies",
            "--raw-field",
            f"body={body}",
        ]
        payload, error = run_gh_json(command, workspace.root)
        if error:
            return {**preview, "ok": False, "url": "", "message": error}
        if not isinstance(payload, dict) or not isinstance(payload.get("html_url"), str):
            return {**preview, "ok": False, "url": "", "message": "GitHub reply response did not include html_url."}
        url = str(payload["html_url"])[:2_000]
    else:
        command = [executable, "pr", "comment"]
        selector = str(preview["selector"])
        if selector != "current branch":
            command.append(selector)
        command.extend(["--repo", str(preview["repository"]), "--body", body])
        stdout, stderr, returncode, error = run_gh_output(command, workspace.root)
        if error:
            return {**preview, "ok": False, "url": "", "message": error}
        if returncode != 0:
            message = redact_git_text(stderr or stdout or "gh pr comment failed.")[:4_000]
            return {**preview, "ok": False, "url": "", "message": message}
        match = _COMMENT_URL.search(stdout)
        if match is None:
            return {**preview, "ok": False, "url": "", "message": "gh pr comment did not return a comment URL."}
        url = match.group(0)
    return {**preview, "url": url, "message": f"Posted GitHub pull request comment: {url}"}


def github_pr_comment_target(pr: str | None, reply_to: int | None, body: str) -> str:
    selector = pr.strip() if isinstance(pr, str) and pr.strip() else "current branch pull request"
    destination = f" reply-to={reply_to}" if reply_to is not None else ""
    compact = " ".join(body.split())
    summary = compact if len(compact) <= 120 else compact[:120] + "..."
    return f"{selector}{destination}: {summary}"


def _validate_comment(body: str, reply_to: int | None) -> str | None:
    if not body.strip() or len(body) > MAX_COMMENT_CHARS:
        return f"GitHub pull request comment body must contain 1-{MAX_COMMENT_CHARS} characters."
    if any(ord(char) < 32 and char not in "\n\r\t" for char in body):
        return "GitHub pull request comment body cannot contain control characters."
    if reply_to is not None and (not isinstance(reply_to, int) or isinstance(reply_to, bool) or reply_to < 1):
        return "reply_to must be a positive review comment ID when provided."
    return None


def _read_pr_number(
    executable: str,
    workspace: RunWorkspace,
    repository: str,
    selector: str,
) -> tuple[int, str | None]:
    command = [executable, "pr", "view"]
    if selector != "current branch":
        command.append(selector)
    command.extend(["--repo", repository, "--json", "number"])
    payload, error = run_gh_json(command, workspace.root)
    if error:
        return 0, error
    number = payload.get("number") if isinstance(payload, dict) else None
    if not isinstance(number, int) or isinstance(number, bool) or number < 1:
        return 0, "gh pr view did not return a valid pull request number."
    return number, None
