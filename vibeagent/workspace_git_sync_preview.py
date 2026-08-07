from __future__ import annotations

from collections.abc import Callable


def git_sync_preview_payload(
    *,
    ok: bool,
    remote: str = "",
    branch: str = "",
    current: str = "",
    upstream: str = "",
    ahead: int = 0,
    behind: int = 0,
    worktree_clean: bool = False,
    status: str = "",
    message: str,
) -> dict[str, object]:
    return {
        "ok": ok,
        "remote": remote,
        "branch": branch,
        "current": current,
        "upstream": upstream,
        "ahead": ahead,
        "behind": behind,
        "worktree_clean": worktree_clean,
        "status": status,
        "message": message,
    }


def git_sync_detached_head_payload(*, operation: str, ahead: int, behind: int, status: str) -> dict[str, object]:
    return git_sync_preview_payload(
        ok=False,
        ahead=ahead,
        behind=behind,
        status=status,
        message=f"Cannot {operation} while HEAD is detached.",
    )


def git_sync_missing_upstream_payload(
    *,
    remote: str,
    branch: str,
    current: str,
    upstream: str,
    ahead: int,
    behind: int,
    worktree_clean: bool,
    status: str,
) -> dict[str, object]:
    return git_sync_preview_payload(
        ok=False,
        remote=remote,
        branch=branch,
        current=current,
        upstream=upstream,
        ahead=ahead,
        behind=behind,
        worktree_clean=worktree_clean,
        status=status,
        message="Current branch has no upstream configured.",
    )


def git_sync_dirty_worktree_payload(
    *,
    operation: str,
    remote: str,
    branch: str,
    current: str,
    upstream: str,
    ahead: int,
    behind: int,
    status: str,
) -> dict[str, object]:
    return git_sync_preview_payload(
        ok=False,
        remote=remote,
        branch=branch,
        current=current,
        upstream=upstream,
        ahead=ahead,
        behind=behind,
        status=status,
        message=f"Working tree has uncommitted changes; commit or clean changes before {operation}.",
    )


def git_upstream_sync_preview_payload(
    *,
    operation: str,
    dirty_operation: str,
    info: dict[str, object],
    current: str,
    upstream_parts: dict[str, object],
    worktree_clean: bool,
    status: str,
    readiness: Callable[..., tuple[bool, str]],
) -> dict[str, object]:
    if not info["ok"]:
        return git_sync_preview_payload(ok=False, message=str(info["message"]))
    if not current:
        return git_sync_detached_head_payload(
            operation=operation,
            ahead=int(info["ahead"]),
            behind=int(info["behind"]),
            status=status,
        )

    upstream = str(info["upstream"])
    if not upstream or not upstream_parts["ok"]:
        return git_sync_missing_upstream_payload(
            remote=str(upstream_parts["remote"]),
            branch=str(upstream_parts["branch"]),
            current=current,
            upstream=upstream,
            ahead=int(info["ahead"]),
            behind=int(info["behind"]),
            worktree_clean=worktree_clean,
            status=status,
        )
    if not worktree_clean:
        return git_sync_dirty_worktree_payload(
            operation=dirty_operation,
            remote=str(upstream_parts["remote"]),
            branch=str(upstream_parts["branch"]),
            current=current,
            upstream=upstream,
            ahead=int(info["ahead"]),
            behind=int(info["behind"]),
            status=status,
        )

    ahead = int(info["ahead"])
    behind = int(info["behind"])
    ok, message = readiness(ahead, behind, upstream=upstream, current=current)
    return git_sync_preview_payload(
        ok=ok,
        remote=str(upstream_parts["remote"]),
        branch=str(upstream_parts["branch"]),
        current=current,
        upstream=upstream,
        ahead=ahead,
        behind=behind,
        worktree_clean=True,
        status=status,
        message=message,
    )


def git_fetch_result_payload(
    *,
    ok: bool,
    remote: str,
    remote_url: str,
    branch: str,
    upstream: str,
    ahead_before: int,
    behind_before: int,
    ahead_after: int,
    behind_after: int,
    message: str,
) -> dict[str, object]:
    return {
        "ok": ok,
        "remote": remote,
        "remote_url": remote_url,
        "branch": branch,
        "upstream": upstream,
        "ahead_before": ahead_before,
        "behind_before": behind_before,
        "ahead_after": ahead_after,
        "behind_after": behind_after,
        "message": message,
    }


def git_pull_result_payload(
    *,
    ok: bool,
    remote: str,
    branch: str,
    current_before: str,
    current_after: str,
    upstream: str,
    ahead_before: int,
    behind_before: int,
    ahead_after: int,
    behind_after: int,
    status: str,
    message: str,
) -> dict[str, object]:
    return {
        "ok": ok,
        "remote": remote,
        "branch": branch,
        "current_before": current_before,
        "current_after": current_after,
        "upstream": upstream,
        "ahead_before": ahead_before,
        "behind_before": behind_before,
        "ahead_after": ahead_after,
        "behind_after": behind_after,
        "status": status,
        "message": message,
    }


def git_push_result_payload(
    *,
    ok: bool,
    remote: str,
    branch: str,
    current: str,
    upstream: str,
    ahead_before: int,
    behind_before: int,
    status: str,
    message: str,
) -> dict[str, object]:
    return {
        "ok": ok,
        "remote": remote,
        "branch": branch,
        "current": current,
        "upstream": upstream,
        "ahead_before": ahead_before,
        "behind_before": behind_before,
        "status": status,
        "message": message,
    }


def pull_readiness(ahead: int, behind: int, *, upstream: str, current: str) -> tuple[bool, str]:
    if ahead > 0 and behind > 0:
        return False, "Current branch has diverged from upstream; fast-forward pull is not safe."
    if ahead > 0:
        return False, "Current branch is ahead of upstream; nothing to fast-forward pull."
    if behind == 0:
        return (
            True,
            "Current branch is already up to date with cached upstream state; "
            "git pull --ff-only can still check the remote.",
        )
    return True, f"Can fast-forward pull {upstream} into {current}."


def push_readiness(ahead: int, behind: int, *, upstream: str, current: str) -> tuple[bool, str]:
    if behind > 0:
        return False, "Current branch is behind upstream; fetch and fast-forward pull before pushing."
    if ahead == 0:
        return False, "Current branch has no commits to push."
    return True, f"Can push {ahead} commit(s) from {current} to {upstream}."
