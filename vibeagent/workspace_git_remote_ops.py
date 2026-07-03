from __future__ import annotations

from .workspace_core import GitCommandResult, RunWorkspace
from .workspace_git_branch_ops import git_status_has_non_runtime_changes
from .workspace_git_utils import parse_git_remotes, redact_git_text, run_git_mutation, run_readonly_git


def read_git_info(workspace: RunWorkspace) -> dict[str, object]:
    git_probe = run_readonly_git(workspace.root, ["rev-parse", "--is-inside-work-tree"])
    if not git_probe.ok or git_probe.stdout.strip() != "true":
        return {
            "ok": False,
            "is_git_repo": False,
            "branch": "",
            "head": "",
            "upstream": "",
            "ahead": 0,
            "behind": 0,
            "remotes": [],
            "status": "",
            "message": git_probe.stderr or "Not a git repository.",
        }

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
            parts = counts.stdout.strip().split()
            if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                ahead = int(parts[0])
                behind = int(parts[1])

    remotes = parse_git_remotes(remotes_result.stdout if remotes_result.ok else "")
    branch = branch_result.stdout.strip() if branch_result.ok else ""
    head = head_result.stdout.strip() if head_result.ok else ""
    status = status_result.stdout if status_result.ok else ""
    message = f"Git repository on {branch or 'detached HEAD'} at {head or 'unknown'}."
    if upstream:
        message += f" Upstream {upstream}, ahead {ahead}, behind {behind}."
    else:
        message += " No upstream configured."

    return {
        "ok": True,
        "is_git_repo": True,
        "branch": branch,
        "head": head,
        "upstream": upstream,
        "ahead": ahead,
        "behind": behind,
        "remotes": remotes,
        "status": status,
        "message": message,
    }


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
        return {
            "ok": False,
            "remote": str(before["remote"]),
            "remote_url": "",
            "branch": "",
            "upstream": "",
            "ahead_before": 0,
            "behind_before": 0,
            "ahead_after": 0,
            "behind_after": 0,
            "message": str(before["message"]),
        }

    result = run_git_mutation(workspace.root, ["fetch", "--prune", str(before["remote"])])
    after = read_git_info(workspace)
    if not result.ok:
        return {
            "ok": False,
            "remote": str(before["remote"]),
            "remote_url": str(before["remote_url"]),
            "branch": str(after["branch"]),
            "upstream": str(after["upstream"]),
            "ahead_before": int(before["ahead"]),
            "behind_before": int(before["behind"]),
            "ahead_after": int(after["ahead"]),
            "behind_after": int(after["behind"]),
            "message": redact_git_text(result.stderr or result.stdout or "git fetch failed."),
        }

    return {
        "ok": True,
        "remote": str(before["remote"]),
        "remote_url": str(before["remote_url"]),
        "branch": str(after["branch"]),
        "upstream": str(after["upstream"]),
        "ahead_before": int(before["ahead"]),
        "behind_before": int(before["behind"]),
        "ahead_after": int(after["ahead"]),
        "behind_after": int(after["behind"]),
        "message": (
            f"Fetched {before['remote']} with --prune. "
            f"Ahead/behind changed from {before['ahead']}/{before['behind']} to {after['ahead']}/{after['behind']}."
        ),
    }


def preview_pull_git_upstream(workspace: RunWorkspace) -> dict[str, object]:
    info = read_git_info(workspace)
    status = _read_git_status(workspace)
    current = str(info["branch"]) if info["ok"] else ""
    if not info["ok"]:
        return {
            "ok": False,
            "remote": "",
            "branch": "",
            "current": "",
            "upstream": "",
            "ahead": 0,
            "behind": 0,
            "worktree_clean": False,
            "status": "",
            "message": str(info["message"]),
        }
    if not current:
        return {
            "ok": False,
            "remote": "",
            "branch": "",
            "current": "",
            "upstream": "",
            "ahead": int(info["ahead"]),
            "behind": int(info["behind"]),
            "worktree_clean": False,
            "status": status.stdout if status.ok else "",
            "message": "Cannot pull while HEAD is detached.",
        }
    upstream = str(info["upstream"])
    upstream_parts = read_git_upstream_parts(workspace, current)
    clean = status.ok and not git_status_has_non_runtime_changes(status.stdout)
    if not upstream or not upstream_parts["ok"]:
        return {
            "ok": False,
            "remote": str(upstream_parts["remote"]),
            "branch": str(upstream_parts["branch"]),
            "current": current,
            "upstream": upstream,
            "ahead": int(info["ahead"]),
            "behind": int(info["behind"]),
            "worktree_clean": clean,
            "status": status.stdout if status.ok else "",
            "message": "Current branch has no upstream configured.",
        }
    if not clean:
        return {
            "ok": False,
            "remote": str(upstream_parts["remote"]),
            "branch": str(upstream_parts["branch"]),
            "current": current,
            "upstream": upstream,
            "ahead": int(info["ahead"]),
            "behind": int(info["behind"]),
            "worktree_clean": False,
            "status": status.stdout if status.ok else "",
            "message": "Working tree has uncommitted changes; commit or clean changes before pulling.",
        }

    ahead = int(info["ahead"])
    behind = int(info["behind"])
    if ahead > 0 and behind > 0:
        message = "Current branch has diverged from upstream; fast-forward pull is not safe."
        ok = False
    elif ahead > 0:
        message = "Current branch is ahead of upstream; nothing to fast-forward pull."
        ok = False
    elif behind == 0:
        message = "Current branch is already up to date with cached upstream state; git pull --ff-only can still check the remote."
        ok = True
    else:
        message = f"Can fast-forward pull {upstream} into {current}."
        ok = True

    return {
        "ok": ok,
        "remote": str(upstream_parts["remote"]),
        "branch": str(upstream_parts["branch"]),
        "current": current,
        "upstream": upstream,
        "ahead": ahead,
        "behind": behind,
        "worktree_clean": True,
        "status": status.stdout if status.ok else "",
        "message": message,
    }


def pull_git_upstream(workspace: RunWorkspace) -> dict[str, object]:
    before = preview_pull_git_upstream(workspace)
    if not before["ok"]:
        return {
            "ok": False,
            "remote": str(before["remote"]),
            "branch": str(before["branch"]),
            "current_before": str(before["current"]),
            "current_after": str(before["current"]),
            "upstream": str(before["upstream"]),
            "ahead_before": int(before["ahead"]),
            "behind_before": int(before["behind"]),
            "ahead_after": int(before["ahead"]),
            "behind_after": int(before["behind"]),
            "status": str(before["status"]),
            "message": str(before["message"]),
        }

    result = run_git_mutation(workspace.root, ["pull", "--ff-only", str(before["remote"]), str(before["branch"])])
    after = read_git_info(workspace)
    status = _read_git_status(workspace)
    return {
        "ok": result.ok,
        "remote": str(before["remote"]),
        "branch": str(before["branch"]),
        "current_before": str(before["current"]),
        "current_after": str(after["branch"]),
        "upstream": str(after["upstream"]),
        "ahead_before": int(before["ahead"]),
        "behind_before": int(before["behind"]),
        "ahead_after": int(after["ahead"]),
        "behind_after": int(after["behind"]),
        "status": status.stdout if status.ok else "",
        "message": (
            f"Pulled {before['upstream']} with --ff-only. "
            f"Ahead/behind changed from {before['ahead']}/{before['behind']} to {after['ahead']}/{after['behind']}."
            if result.ok
            else redact_git_text(result.stderr or result.stdout or "git pull --ff-only failed.")
        ),
    }


def preview_push_git_upstream(workspace: RunWorkspace) -> dict[str, object]:
    info = read_git_info(workspace)
    status = _read_git_status(workspace)
    current = str(info["branch"]) if info["ok"] else ""
    if not info["ok"]:
        return {
            "ok": False,
            "remote": "",
            "branch": "",
            "current": "",
            "upstream": "",
            "ahead": 0,
            "behind": 0,
            "worktree_clean": False,
            "status": "",
            "message": str(info["message"]),
        }
    if not current:
        return {
            "ok": False,
            "remote": "",
            "branch": "",
            "current": "",
            "upstream": "",
            "ahead": int(info["ahead"]),
            "behind": int(info["behind"]),
            "worktree_clean": False,
            "status": status.stdout if status.ok else "",
            "message": "Cannot push while HEAD is detached.",
        }

    upstream = str(info["upstream"])
    upstream_parts = read_git_upstream_parts(workspace, current)
    clean = status.ok and not git_status_has_non_runtime_changes(status.stdout)
    if not upstream or not upstream_parts["ok"]:
        return {
            "ok": False,
            "remote": str(upstream_parts["remote"]),
            "branch": str(upstream_parts["branch"]),
            "current": current,
            "upstream": upstream,
            "ahead": int(info["ahead"]),
            "behind": int(info["behind"]),
            "worktree_clean": clean,
            "status": status.stdout if status.ok else "",
            "message": "Current branch has no upstream configured.",
        }
    if not clean:
        return {
            "ok": False,
            "remote": str(upstream_parts["remote"]),
            "branch": str(upstream_parts["branch"]),
            "current": current,
            "upstream": upstream,
            "ahead": int(info["ahead"]),
            "behind": int(info["behind"]),
            "worktree_clean": False,
            "status": status.stdout if status.ok else "",
            "message": "Working tree has uncommitted changes; commit or clean changes before pushing.",
        }

    ahead = int(info["ahead"])
    behind = int(info["behind"])
    if behind > 0:
        message = "Current branch is behind upstream; fetch and fast-forward pull before pushing."
        ok = False
    elif ahead == 0:
        message = "Current branch has no commits to push."
        ok = False
    else:
        message = f"Can push {ahead} commit(s) from {current} to {upstream}."
        ok = True

    return {
        "ok": ok,
        "remote": str(upstream_parts["remote"]),
        "branch": str(upstream_parts["branch"]),
        "current": current,
        "upstream": upstream,
        "ahead": ahead,
        "behind": behind,
        "worktree_clean": True,
        "status": status.stdout if status.ok else "",
        "message": message,
    }


def push_git_upstream(workspace: RunWorkspace) -> dict[str, object]:
    before = preview_push_git_upstream(workspace)
    if not before["ok"]:
        return {
            "ok": False,
            "remote": str(before["remote"]),
            "branch": str(before["branch"]),
            "current": str(before["current"]),
            "upstream": str(before["upstream"]),
            "ahead_before": int(before["ahead"]),
            "behind_before": int(before["behind"]),
            "status": str(before["status"]),
            "message": str(before["message"]),
        }

    result = run_git_mutation(workspace.root, ["push", str(before["remote"]), f"HEAD:{before['branch']}"])
    status = _read_git_status(workspace)
    return {
        "ok": result.ok,
        "remote": str(before["remote"]),
        "branch": str(before["branch"]),
        "current": str(before["current"]),
        "upstream": str(before["upstream"]),
        "ahead_before": int(before["ahead"]),
        "behind_before": int(before["behind"]),
        "status": status.stdout if status.ok else "",
        "message": (
            f"Pushed {before['current']} to {before['upstream']}."
            if result.ok
            else redact_git_text(result.stderr or result.stdout or "git push failed.")
        ),
    }


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
    names = sorted({item["name"] for item in fetch_remotes})
    requested = remote.strip() if isinstance(remote, str) else ""
    if remote is not None and not requested:
        return {"ok": False, "remote": "", "remote_url": "", "message": "git_fetch remote must be non-empty when provided."}
    if requested and requested not in names:
        return {
            "ok": False,
            "remote": requested,
            "remote_url": "",
            "message": f"Git remote not found: {requested}.",
        }
    if not requested:
        if not names:
            return {"ok": False, "remote": "", "remote_url": "", "message": "No git remotes are configured."}
        if len(names) > 1:
            return {
                "ok": False,
                "remote": "",
                "remote_url": "",
                "message": "Multiple git remotes are configured; specify one remote.",
            }
        requested = names[0]

    remote_url = next((item["url"] for item in fetch_remotes if item["name"] == requested), "")
    return {"ok": True, "remote": requested, "remote_url": remote_url, "message": "Git remote selected."}


def _read_git_status(workspace: RunWorkspace) -> GitCommandResult:
    return run_readonly_git(workspace.root, ["status", "--short", "--untracked-files=all"])
