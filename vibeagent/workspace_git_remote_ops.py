from __future__ import annotations

from .workspace_core import GitCommandResult, RunWorkspace
from .workspace_git_branch_ops import git_status_has_non_runtime_changes
from .workspace_git_info import git_info_payload, git_not_repo_info, parse_ahead_behind_counts
from .workspace_git_remote_selection import select_fetch_remote_from_remotes
from .workspace_git_sync_preview import (
    git_fetch_result_payload,
    git_pull_result_payload,
    git_push_result_payload,
    git_sync_detached_head_payload,
    git_sync_dirty_worktree_payload,
    git_sync_missing_upstream_payload,
    git_sync_preview_payload,
    pull_readiness,
    push_readiness,
)
from .workspace_git_utils import parse_git_remotes, redact_git_text, run_git_mutation, run_readonly_git


def read_git_info(workspace: RunWorkspace) -> dict[str, object]:
    git_probe = run_readonly_git(workspace.root, ["rev-parse", "--is-inside-work-tree"])
    if not git_probe.ok or git_probe.stdout.strip() != "true":
        return git_not_repo_info(git_probe.stderr or "Not a git repository.")

    branch_result = run_readonly_git(workspace.root, ["branch", "--show-current"])
    head_result = run_readonly_git(workspace.root, ["rev-parse", "--short", "HEAD"])
    upstream_result = run_readonly_git(workspace.root, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    status_result = _read_git_status(workspace)
    remotes_result = run_readonly_git(workspace.root, ["remote", "-v"])

    upstream = upstream_result.stdout.strip() if upstream_result.ok else ""
    ahead = 0
    behind = 0
    if upstream:
        counts = run_readonly_git(workspace.root, ["rev-list", "--left-right", "--count", f"HEAD...{upstream}"])
        if counts.ok:
            ahead, behind = parse_ahead_behind_counts(counts.stdout)

    remotes = parse_git_remotes(remotes_result.stdout if remotes_result.ok else "")
    branch = branch_result.stdout.strip() if branch_result.ok else ""
    head = head_result.stdout.strip() if head_result.ok else ""
    status = status_result.stdout if status_result.ok else ""
    return git_info_payload(
        branch=branch,
        head=head,
        upstream=upstream,
        ahead=ahead,
        behind=behind,
        remotes=remotes,
        status=status,
    )


def preview_fetch_git_remote(workspace: RunWorkspace, remote: str | None = None) -> dict[str, object]:
    selected = select_git_fetch_remote(workspace, remote)
    if not selected["ok"]:
        return {
            "ok": False,
            "remote": str(selected["remote"]),
            "remote_url": "",
            "branch": "",
            "upstream": "",
            "ahead": 0,
            "behind": 0,
            "message": str(selected["message"]),
        }

    info = read_git_info(workspace)
    return {
        "ok": True,
        "remote": str(selected["remote"]),
        "remote_url": str(selected["remote_url"]),
        "branch": str(info["branch"]),
        "upstream": str(info["upstream"]),
        "ahead": int(info["ahead"]),
        "behind": int(info["behind"]),
        "message": (
            f"git fetch --prune {selected['remote']} can run. "
            f"Current branch {info['branch'] or 'detached HEAD'} is ahead {info['ahead']} and behind {info['behind']}."
        ),
    }


def fetch_git_remote(workspace: RunWorkspace, remote: str | None = None) -> dict[str, object]:
    before = preview_fetch_git_remote(workspace, remote)
    if not before["ok"]:
        return git_fetch_result_payload(
            ok=False,
            remote=str(before["remote"]),
            remote_url="",
            branch="",
            upstream="",
            ahead_before=0,
            behind_before=0,
            ahead_after=0,
            behind_after=0,
            message=str(before["message"]),
        )

    result = run_git_mutation(workspace.root, ["fetch", "--prune", str(before["remote"])])
    after = read_git_info(workspace)
    if not result.ok:
        return git_fetch_result_payload(
            ok=False,
            remote=str(before["remote"]),
            remote_url=str(before["remote_url"]),
            branch=str(after["branch"]),
            upstream=str(after["upstream"]),
            ahead_before=int(before["ahead"]),
            behind_before=int(before["behind"]),
            ahead_after=int(after["ahead"]),
            behind_after=int(after["behind"]),
            message=redact_git_text(result.stderr or result.stdout or "git fetch failed."),
        )

    return git_fetch_result_payload(
        ok=True,
        remote=str(before["remote"]),
        remote_url=str(before["remote_url"]),
        branch=str(after["branch"]),
        upstream=str(after["upstream"]),
        ahead_before=int(before["ahead"]),
        behind_before=int(before["behind"]),
        ahead_after=int(after["ahead"]),
        behind_after=int(after["behind"]),
        message=(
            f"Fetched {before['remote']} with --prune. "
            f"Ahead/behind changed from {before['ahead']}/{before['behind']} to {after['ahead']}/{after['behind']}."
        ),
    )


def preview_pull_git_upstream(workspace: RunWorkspace) -> dict[str, object]:
    info = read_git_info(workspace)
    status = _read_git_status(workspace)
    current = str(info["branch"]) if info["ok"] else ""
    if not info["ok"]:
        return git_sync_preview_payload(ok=False, message=str(info["message"]))
    if not current:
        return git_sync_detached_head_payload(
            operation="pull",
            ahead=int(info["ahead"]),
            behind=int(info["behind"]),
            status=status.stdout if status.ok else "",
        )
    upstream = str(info["upstream"])
    upstream_parts = read_git_upstream_parts(workspace, current)
    clean = status.ok and not git_status_has_non_runtime_changes(status.stdout)
    if not upstream or not upstream_parts["ok"]:
        return git_sync_missing_upstream_payload(
            remote=str(upstream_parts["remote"]),
            branch=str(upstream_parts["branch"]),
            current=current,
            upstream=upstream,
            ahead=int(info["ahead"]),
            behind=int(info["behind"]),
            worktree_clean=clean,
            status=status.stdout if status.ok else "",
        )
    if not clean:
        return git_sync_dirty_worktree_payload(
            operation="pulling",
            remote=str(upstream_parts["remote"]),
            branch=str(upstream_parts["branch"]),
            current=current,
            upstream=upstream,
            ahead=int(info["ahead"]),
            behind=int(info["behind"]),
            status=status.stdout if status.ok else "",
        )

    ahead = int(info["ahead"])
    behind = int(info["behind"])
    ok, message = pull_readiness(ahead, behind, upstream=upstream, current=current)
    return git_sync_preview_payload(
        ok=ok,
        remote=str(upstream_parts["remote"]),
        branch=str(upstream_parts["branch"]),
        current=current,
        upstream=upstream,
        ahead=ahead,
        behind=behind,
        worktree_clean=True,
        status=status.stdout if status.ok else "",
        message=message,
    )


def pull_git_upstream(workspace: RunWorkspace) -> dict[str, object]:
    before = preview_pull_git_upstream(workspace)
    if not before["ok"]:
        return git_pull_result_payload(
            ok=False,
            remote=str(before["remote"]),
            branch=str(before["branch"]),
            current_before=str(before["current"]),
            current_after=str(before["current"]),
            upstream=str(before["upstream"]),
            ahead_before=int(before["ahead"]),
            behind_before=int(before["behind"]),
            ahead_after=int(before["ahead"]),
            behind_after=int(before["behind"]),
            status=str(before["status"]),
            message=str(before["message"]),
        )

    result = run_git_mutation(workspace.root, ["pull", "--ff-only", str(before["remote"]), str(before["branch"])])
    after = read_git_info(workspace)
    status = _read_git_status(workspace)
    return git_pull_result_payload(
        ok=result.ok,
        remote=str(before["remote"]),
        branch=str(before["branch"]),
        current_before=str(before["current"]),
        current_after=str(after["branch"]),
        upstream=str(after["upstream"]),
        ahead_before=int(before["ahead"]),
        behind_before=int(before["behind"]),
        ahead_after=int(after["ahead"]),
        behind_after=int(after["behind"]),
        status=status.stdout if status.ok else "",
        message=(
            f"Pulled {before['upstream']} with --ff-only. "
            f"Ahead/behind changed from {before['ahead']}/{before['behind']} to {after['ahead']}/{after['behind']}."
            if result.ok
            else redact_git_text(result.stderr or result.stdout or "git pull --ff-only failed.")
        ),
    )


def preview_push_git_upstream(workspace: RunWorkspace) -> dict[str, object]:
    info = read_git_info(workspace)
    status = _read_git_status(workspace)
    current = str(info["branch"]) if info["ok"] else ""
    if not info["ok"]:
        return git_sync_preview_payload(ok=False, message=str(info["message"]))
    if not current:
        return git_sync_detached_head_payload(
            operation="push",
            ahead=int(info["ahead"]),
            behind=int(info["behind"]),
            status=status.stdout if status.ok else "",
        )

    upstream = str(info["upstream"])
    upstream_parts = read_git_upstream_parts(workspace, current)
    clean = status.ok and not git_status_has_non_runtime_changes(status.stdout)
    if not upstream or not upstream_parts["ok"]:
        return git_sync_missing_upstream_payload(
            remote=str(upstream_parts["remote"]),
            branch=str(upstream_parts["branch"]),
            current=current,
            upstream=upstream,
            ahead=int(info["ahead"]),
            behind=int(info["behind"]),
            worktree_clean=clean,
            status=status.stdout if status.ok else "",
        )
    if not clean:
        return git_sync_dirty_worktree_payload(
            operation="pushing",
            remote=str(upstream_parts["remote"]),
            branch=str(upstream_parts["branch"]),
            current=current,
            upstream=upstream,
            ahead=int(info["ahead"]),
            behind=int(info["behind"]),
            status=status.stdout if status.ok else "",
        )

    ahead = int(info["ahead"])
    behind = int(info["behind"])
    ok, message = push_readiness(ahead, behind, upstream=upstream, current=current)
    return git_sync_preview_payload(
        ok=ok,
        remote=str(upstream_parts["remote"]),
        branch=str(upstream_parts["branch"]),
        current=current,
        upstream=upstream,
        ahead=ahead,
        behind=behind,
        worktree_clean=True,
        status=status.stdout if status.ok else "",
        message=message,
    )


def push_git_upstream(workspace: RunWorkspace) -> dict[str, object]:
    before = preview_push_git_upstream(workspace)
    if not before["ok"]:
        return git_push_result_payload(
            ok=False,
            remote=str(before["remote"]),
            branch=str(before["branch"]),
            current=str(before["current"]),
            upstream=str(before["upstream"]),
            ahead_before=int(before["ahead"]),
            behind_before=int(before["behind"]),
            status=str(before["status"]),
            message=str(before["message"]),
        )

    result = run_git_mutation(workspace.root, ["push", str(before["remote"]), f"HEAD:{before['branch']}"])
    status = _read_git_status(workspace)
    return git_push_result_payload(
        ok=result.ok,
        remote=str(before["remote"]),
        branch=str(before["branch"]),
        current=str(before["current"]),
        upstream=str(before["upstream"]),
        ahead_before=int(before["ahead"]),
        behind_before=int(before["behind"]),
        status=status.stdout if status.ok else "",
        message=(
            f"Pushed {before['current']} to {before['upstream']}."
            if result.ok
            else redact_git_text(result.stderr or result.stdout or "git push failed.")
        ),
    )


def read_git_upstream_parts(workspace: RunWorkspace, branch: str) -> dict[str, object]:
    remote_result = run_readonly_git(workspace.root, ["config", f"branch.{branch}.remote"])
    merge_result = run_readonly_git(workspace.root, ["config", f"branch.{branch}.merge"])
    remote = remote_result.stdout.strip() if remote_result.ok else ""
    merge = merge_result.stdout.strip() if merge_result.ok else ""
    prefix = "refs/heads/"
    upstream_branch = merge[len(prefix) :] if merge.startswith(prefix) else merge
    return {
        "ok": bool(remote and upstream_branch),
        "remote": remote,
        "branch": upstream_branch,
    }


def select_git_fetch_remote(workspace: RunWorkspace, remote: str | None) -> dict[str, object]:
    git_probe = run_readonly_git(workspace.root, ["rev-parse", "--is-inside-work-tree"])
    if not git_probe.ok or git_probe.stdout.strip() != "true":
        return {"ok": False, "remote": remote or "", "remote_url": "", "message": git_probe.stderr or "Not a git repository."}

    remotes_result = run_readonly_git(workspace.root, ["remote", "-v"])
    remotes = parse_git_remotes(remotes_result.stdout if remotes_result.ok else "")
    fetch_remotes = [item for item in remotes if item.get("kind") == "fetch"]
    return select_fetch_remote_from_remotes(fetch_remotes, remote)


def _read_git_status(workspace: RunWorkspace) -> GitCommandResult:
    return run_readonly_git(workspace.root, ["status", "--short", "--untracked-files=all"])
