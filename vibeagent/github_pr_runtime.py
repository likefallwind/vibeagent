from __future__ import annotations

import re
import shutil
import subprocess
from typing import Any

from .workspace_core import RunWorkspace
from .workspace_git_info import parse_ahead_behind_counts
from .workspace_git_remote_ops import read_git_upstream_parts
from .workspace_git_utils import redact_git_text, run_readonly_git


_GITHUB_REMOTE_PATTERNS = (
    re.compile(r"^(?:https?|git)://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", re.IGNORECASE),
    re.compile(r"^(?:ssh://)?git@github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$", re.IGNORECASE),
)
_PR_URL_PATTERN = re.compile(r"https://github\.com/[^\s/]+/[^\s/]+/pull/\d+")


def parse_github_repository(remote_url: str) -> tuple[str, str] | None:
    clean = remote_url.strip()
    for pattern in _GITHUB_REMOTE_PATTERNS:
        match = pattern.fullmatch(clean)
        if match:
            return match.group(1), match.group(2)
    return None


def preview_github_pr_create(
    workspace: RunWorkspace,
    *,
    title: str,
    body: str = "",
    base: str | None = None,
    remote: str | None = None,
    draft: bool = False,
) -> dict[str, Any]:
    result = _empty_result(title, draft)
    invalid = _validate_text(title, body)
    if invalid:
        result["message"] = invalid
        return result

    branch_result = run_readonly_git(workspace.root, ["branch", "--show-current"])
    branch = branch_result.stdout.strip() if branch_result.ok else ""
    if not branch:
        result["message"] = "A checked-out git branch is required; detached HEAD cannot create a pull request."
        return result

    upstream = read_git_upstream_parts(workspace, branch)
    if not upstream["ok"]:
        result["message"] = "The current branch must have a configured upstream before creating a pull request."
        return result
    head_remote = str(upstream["remote"])
    head_branch = str(upstream["branch"])
    target_remote = remote.strip() if isinstance(remote, str) else head_remote
    if not target_remote:
        result["message"] = "The target remote must be non-empty."
        return result

    head_repo = _read_remote_repository(workspace, head_remote)
    target_repo = _read_remote_repository(workspace, target_remote)
    if head_repo is None:
        result["message"] = f"The current upstream remote {head_remote!r} is not a GitHub repository."
        return result
    if target_repo is None:
        result["message"] = f"The target remote {target_remote!r} is missing or is not a GitHub repository."
        return result

    base_branch = base.strip() if isinstance(base, str) else _default_base_branch(workspace, target_remote)
    if not base_branch:
        result["message"] = f"Could not determine the default branch for {target_remote}; provide base explicitly."
        return result
    if not _valid_branch(workspace, base_branch):
        result["message"] = f"Invalid pull request base branch: {base_branch!r}."
        return result
    if branch == base_branch and head_repo == target_repo:
        result["message"] = "The pull request head and base branches must be different."
        return result

    counts = run_readonly_git(workspace.root, ["rev-list", "--left-right", "--count", f"HEAD...{head_remote}/{head_branch}"])
    ahead, behind = parse_ahead_behind_counts(counts.stdout) if counts.ok else (0, 0)
    result.update(
        repository=f"{target_repo[0]}/{target_repo[1]}",
        remote=target_remote,
        head=branch if head_repo == target_repo else f"{head_repo[0]}:{branch}",
        base=base_branch,
        ahead=ahead,
        behind=behind,
    )
    if not counts.ok:
        result["message"] = "Could not compare the current branch with its upstream."
        return result
    if ahead or behind:
        result["message"] = (
            "The current branch must match its cached upstream before creating a pull request "
            f"(ahead {ahead}, behind {behind}); fetch and push first."
        )
        return result

    base_ref = f"refs/remotes/{target_remote}/{base_branch}"
    base_exists = run_readonly_git(workspace.root, ["show-ref", "--verify", "--quiet", base_ref])
    if not base_exists.ok:
        result["message"] = f"Cached base branch {target_remote}/{base_branch} was not found; fetch the remote first."
        return result
    commit_count = run_readonly_git(workspace.root, ["rev-list", "--count", f"{base_ref}..HEAD"])
    commits = int(commit_count.stdout.strip()) if commit_count.ok and commit_count.stdout.strip().isdigit() else 0
    result["commits"] = commits
    if commits < 1:
        result["message"] = f"The current branch has no commits ahead of {target_remote}/{base_branch}."
        return result
    if shutil.which("gh") is None:
        result["message"] = "GitHub CLI executable 'gh' was not found."
        return result

    result["ok"] = True
    result["message"] = (
        f"Ready to create a{' draft' if draft else ''} pull request in {result['repository']} "
        f"from {result['head']} to {base_branch} with {commits} commit(s)."
    )
    return result


def create_github_pr(workspace: RunWorkspace, **options: Any) -> dict[str, Any]:
    preview = preview_github_pr_create(workspace, **options)
    if not preview["ok"]:
        return {**preview, "url": ""}
    executable = shutil.which("gh")
    if executable is None:
        return {**preview, "ok": False, "url": "", "message": "GitHub CLI executable 'gh' was not found."}
    command = [
        executable,
        "pr",
        "create",
        "--repo",
        str(preview["repository"]),
        "--head",
        str(preview["head"]),
        "--base",
        str(preview["base"]),
        "--title",
        str(options["title"]),
        "--body",
        str(options.get("body", "")),
    ]
    if options.get("draft", False):
        command.append("--draft")
    try:
        completed = subprocess.run(command, cwd=workspace.root, text=True, capture_output=True, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        return {**preview, "ok": False, "url": "", "message": f"GitHub CLI failed: {redact_git_text(str(error))}"}
    output = (completed.stdout + "\n" + completed.stderr).strip()
    match = _PR_URL_PATTERN.search(output)
    if completed.returncode != 0 or match is None:
        return {**preview, "ok": False, "url": "", "message": redact_git_text(output or "gh pr create failed.")[:4000]}
    return {**preview, "url": match.group(0), "message": f"Created pull request: {match.group(0)}"}


def _empty_result(title: str, draft: bool) -> dict[str, Any]:
    return {"ok": False, "repository": "", "remote": "", "head": "", "base": "", "title": title, "draft": draft, "ahead": 0, "behind": 0, "commits": 0, "message": ""}


def _validate_text(title: str, body: str) -> str | None:
    if not title.strip() or len(title) > 256 or "\n" in title or "\r" in title:
        return "Pull request title must be a non-empty single-line string of at most 256 characters."
    if len(body) > 65_536:
        return "Pull request body must contain at most 65536 characters."
    if any(ord(char) < 32 and char not in "\n\r\t" for char in title + body):
        return "Pull request title and body cannot contain control characters."
    return None


def _read_remote_repository(workspace: RunWorkspace, remote: str) -> tuple[str, str] | None:
    url = run_readonly_git(workspace.root, ["remote", "get-url", remote])
    return parse_github_repository(url.stdout) if url.ok else None


def _default_base_branch(workspace: RunWorkspace, remote: str) -> str:
    result = run_readonly_git(workspace.root, ["symbolic-ref", "--short", f"refs/remotes/{remote}/HEAD"])
    value = result.stdout.strip() if result.ok else ""
    prefix = f"{remote}/"
    return value[len(prefix):] if value.startswith(prefix) else ""


def _valid_branch(workspace: RunWorkspace, branch: str) -> bool:
    if branch.startswith("-"):
        return False
    return run_readonly_git(workspace.root, ["check-ref-format", "--branch", branch]).ok
