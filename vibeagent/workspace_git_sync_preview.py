from __future__ import annotations


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
