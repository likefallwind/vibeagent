from __future__ import annotations

from .workspace_core import GitCommandResult, RunWorkspace
from .workspace_git_branch_ops import (
    git_branch_exists,
    git_status_has_non_runtime_changes,
    normalize_git_index_paths,
    read_git_current_branch,
    read_git_head,
    validate_git_branch_name,
)
from .workspace_git_utils import run_git_mutation, run_readonly_git


def stage_git_paths(workspace: RunWorkspace, paths: list[str]) -> dict[str, object]:
    normalized = normalize_git_index_paths(workspace, paths)
    result = run_git_mutation(workspace.root, ["add", "--", *normalized])
    status = _read_git_status(workspace)
    return {
        "ok": result.ok,
        "paths": normalized,
        "status": status.stdout if status.ok else "",
        "message": f"Staged {len(normalized)} path(s)." if result.ok else result.stderr or "git add failed.",
    }


def preview_stage_git_paths(workspace: RunWorkspace, paths: list[str]) -> dict[str, object]:
    normalized = normalize_git_index_paths(workspace, paths)
    status = _read_git_status(workspace)
    return {
        "ok": status.ok,
        "paths": normalized,
        "status": status.stdout if status.ok else "",
        "message": f"Can stage {len(normalized)} path(s)." if status.ok else status.stderr or "git status failed.",
    }


def unstage_git_paths(workspace: RunWorkspace, paths: list[str]) -> dict[str, object]:
    normalized = normalize_git_index_paths(workspace, paths)
    result = run_git_mutation(workspace.root, ["restore", "--staged", "--", *normalized])
    status = _read_git_status(workspace)
    return {
        "ok": result.ok,
        "paths": normalized,
        "status": status.stdout if status.ok else "",
        "message": f"Unstaged {len(normalized)} path(s)." if result.ok else result.stderr or "git restore --staged failed.",
    }


def preview_unstage_git_paths(workspace: RunWorkspace, paths: list[str]) -> dict[str, object]:
    normalized = normalize_git_index_paths(workspace, paths)
    status = _read_git_status(workspace)
    return {
        "ok": status.ok,
        "paths": normalized,
        "status": status.stdout if status.ok else "",
        "message": f"Can unstage {len(normalized)} path(s)." if status.ok else status.stderr or "git status failed.",
    }


def preview_restore_git_paths(workspace: RunWorkspace, paths: list[str]) -> dict[str, object]:
    normalized = normalize_git_index_paths(workspace, paths)
    tracked = validate_git_tracked_paths(workspace, normalized)
    status = _read_git_status(workspace)
    if not tracked.ok:
        return {
            "ok": False,
            "paths": normalized,
            "diff": "",
            "status": status.stdout if status.ok else "",
            "message": tracked.stderr or "One or more paths are not tracked by git.",
        }

    diff = run_readonly_git(workspace.root, ["diff", "--", *normalized])
    if not diff.ok:
        return {
            "ok": False,
            "paths": normalized,
            "diff": "",
            "status": status.stdout if status.ok else "",
            "message": diff.stderr or "git diff failed.",
        }
    if not diff.stdout:
        return {
            "ok": False,
            "paths": normalized,
            "diff": "",
            "status": status.stdout if status.ok else "",
            "message": "No unstaged tracked changes to restore for the requested path(s).",
        }
    return {
        "ok": True,
        "paths": normalized,
        "diff": diff.stdout,
        "status": status.stdout if status.ok else "",
        "message": f"Can restore unstaged changes for {len(normalized)} tracked path(s).",
    }


def restore_git_paths(workspace: RunWorkspace, paths: list[str]) -> dict[str, object]:
    preview = preview_restore_git_paths(workspace, paths)
    if not preview["ok"]:
        return preview
    result = run_git_mutation(workspace.root, ["restore", "--", *list(preview["paths"])])
    status = _read_git_status(workspace)
    return {
        "ok": result.ok,
        "paths": list(preview["paths"]),
        "diff": str(preview["diff"]),
        "status": status.stdout if status.ok else "",
        "message": f"Restored unstaged changes for {len(preview['paths'])} tracked path(s)." if result.ok else result.stderr or "git restore failed.",
    }


def validate_git_tracked_paths(workspace: RunWorkspace, paths: list[str]) -> GitCommandResult:
    return run_readonly_git(workspace.root, ["ls-files", "--error-unmatch", "--", *paths])


def commit_staged_changes(workspace: RunWorkspace, message: str) -> dict[str, object]:
    message = message.strip()
    if not message:
        raise ValueError("message must be a non-empty string.")
    if len(message) > 500:
        raise ValueError("message must be at most 500 characters.")

    staged_probe = run_readonly_git(workspace.root, ["diff", "--cached", "--quiet"])
    if staged_probe.exit_code == 0:
        return {
            "ok": False,
            "head_before": read_git_head(workspace),
            "head_after": read_git_head(workspace),
            "status": _read_git_status(workspace).stdout,
            "message": "No staged changes to commit.",
        }

    head_before = read_git_head(workspace)
    result = run_git_mutation(workspace.root, ["commit", "--no-verify", "-m", message])
    head_after = read_git_head(workspace)
    status = _read_git_status(workspace)
    return {
        "ok": result.ok,
        "head_before": head_before,
        "head_after": head_after,
        "status": status.stdout if status.ok else "",
        "message": f"Committed staged changes: {head_after}." if result.ok else result.stderr or "git commit failed.",
    }


def preview_commit_staged_changes(workspace: RunWorkspace, message: str) -> dict[str, object]:
    message = message.strip()
    if not message:
        raise ValueError("message must be a non-empty string.")
    if len(message) > 500:
        raise ValueError("message must be at most 500 characters.")

    head = read_git_head(workspace)
    status = _read_git_status(workspace)
    staged_probe = run_readonly_git(workspace.root, ["diff", "--cached", "--quiet"])
    if staged_probe.exit_code == 0:
        return {
            "ok": False,
            "head_before": head,
            "head_after": head,
            "status": status.stdout if status.ok else "",
            "message": "No staged changes to commit.",
        }
    if staged_probe.exit_code == 1:
        return {
            "ok": True,
            "head_before": head,
            "head_after": head,
            "status": status.stdout if status.ok else "",
            "message": "Staged changes can be committed.",
        }
    return {
        "ok": False,
        "head_before": head,
        "head_after": head,
        "status": status.stdout if status.ok else "",
        "message": staged_probe.stderr or "git diff --cached failed.",
    }


def preview_switch_git_branch(workspace: RunWorkspace, branch: str, create: bool = False) -> dict[str, object]:
    normalized = validate_git_branch_name(workspace, branch)
    current = read_git_current_branch(workspace)
    status = _read_git_status(workspace)
    if not status.ok:
        return {
            "ok": False,
            "branch": normalized,
            "create": create,
            "current_before": current,
            "branch_exists": False,
            "worktree_clean": False,
            "status": "",
            "message": status.stderr or "git status failed.",
        }

    clean = not git_status_has_non_runtime_changes(status.stdout)
    exists = git_branch_exists(workspace, normalized)
    ok = True
    if not clean:
        ok = False
        message = "Working tree has uncommitted changes; commit or clean changes before switching branches."
    elif create and exists:
        ok = False
        message = f"Branch already exists: {normalized}."
    elif not create and not exists:
        ok = False
        message = f"Branch does not exist: {normalized}."
    elif create:
        message = f"Can create and switch to branch {normalized}."
    else:
        message = f"Can switch to branch {normalized}."
    return {
        "ok": ok,
        "branch": normalized,
        "create": create,
        "current_before": current,
        "branch_exists": exists,
        "worktree_clean": clean,
        "status": status.stdout,
        "message": message,
    }


def switch_git_branch(workspace: RunWorkspace, branch: str, create: bool = False) -> dict[str, object]:
    preview = preview_switch_git_branch(workspace, branch, create=create)
    current_before = str(preview["current_before"])
    if not bool(preview["ok"]):
        return {
            "ok": False,
            "branch": str(preview["branch"]),
            "create": create,
            "current_before": current_before,
            "current_after": current_before,
            "status": str(preview["status"]),
            "message": str(preview["message"]),
        }

    args = ["switch"]
    if create:
        args.append("-c")
    args.append(str(preview["branch"]))
    result = run_git_mutation(workspace.root, args)
    current_after = read_git_current_branch(workspace)
    status = _read_git_status(workspace)
    return {
        "ok": result.ok,
        "branch": str(preview["branch"]),
        "create": create,
        "current_before": current_before,
        "current_after": current_after,
        "status": status.stdout if status.ok else "",
        "message": (
            f"Switched to branch {current_after or preview['branch']}."
            if result.ok
            else result.stderr or "git switch failed."
        ),
    }


def _read_git_status(workspace: RunWorkspace) -> GitCommandResult:
    return run_readonly_git(workspace.root, ["status", "--short", "--untracked-files=all"])
