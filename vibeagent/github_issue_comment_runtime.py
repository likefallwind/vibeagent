from __future__ import annotations

import re
import shutil
from typing import Any

from .github_comment_runtime import (
    github_comment_metadata,
    github_comment_summary,
    validate_github_comment_body,
)
from .github_issue_context_runtime import normalize_issue_selector
from .github_pr_context_runtime import run_gh_output, select_local_github_repository
from .workspace_core import RunWorkspace
from .workspace_git_utils import redact_git_text


def preview_github_issue_comment(
    workspace: RunWorkspace,
    *,
    body: str,
    issue: str,
    remote: str | None = None,
) -> dict[str, Any]:
    repository, error = select_local_github_repository(workspace, remote)
    selector, selector_error = normalize_issue_selector(issue, repository) if not error else ("", None)
    error = error or selector_error or validate_github_comment_body(body, destination="issue")
    result = {
        "ok": False,
        "repository": repository,
        "selector": selector,
        "issue": issue,
        "remote": remote,
        **github_comment_metadata(body),
        "comment_target": github_issue_comment_target(issue, body),
        "message": error or "",
    }
    if error:
        return result
    if shutil.which("gh") is None:
        result["message"] = "GitHub CLI executable 'gh' was not found."
        return result
    result["ok"] = True
    result["message"] = f"Ready to post {len(body)} characters to {repository} issue {selector}."
    return result


def create_github_issue_comment(workspace: RunWorkspace, **options: Any) -> dict[str, Any]:
    preview = preview_github_issue_comment(workspace, **options)
    if not preview["ok"]:
        return {**preview, "url": ""}
    executable = shutil.which("gh")
    if executable is None:
        return {**preview, "ok": False, "url": "", "message": "GitHub CLI executable 'gh' was not found."}
    body = str(options["body"])
    command = [
        executable,
        "issue",
        "comment",
        str(preview["selector"]),
        "--repo",
        str(preview["repository"]),
        "--body",
        body,
    ]
    stdout, stderr, returncode, error = run_gh_output(command, workspace.root)
    if error:
        return {**preview, "ok": False, "url": "", "message": error}
    if returncode != 0:
        message = redact_git_text(stderr or stdout or "gh issue comment failed.")[:4_000]
        return {**preview, "ok": False, "url": "", "message": message}
    pattern = re.compile(
        rf"https://github\.com/{re.escape(str(preview['repository']))}/issues/\d+#issuecomment-\d+",
        re.IGNORECASE,
    )
    match = pattern.search(stdout)
    if match is None:
        return {**preview, "ok": False, "url": "", "message": "gh issue comment did not return a comment URL."}
    url = match.group(0)
    return {**preview, "url": url, "message": f"Posted GitHub issue comment: {url}"}


def github_issue_comment_target(issue: str, body: str) -> str:
    selector = issue.strip() if isinstance(issue, str) and issue.strip() else "unknown issue"
    return f"{selector}: {github_comment_summary(body)}"
