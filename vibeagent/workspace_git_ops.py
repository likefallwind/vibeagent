from __future__ import annotations

from .workspace_core import (
    GIT_CONFLICT_MARKERS,
    GIT_UNMERGED_STATUS_CODES,
    GitCommandResult,
    RunWorkspace,
)
from .workspace_git_utils import (
    parse_git_remotes,
    redact_git_text,
    run_git_mutation,
    run_readonly_git,
)
from .workspace_git_read_ops import (
    parse_git_diff_file_path,
    parse_git_diff_hunks,
    read_git_blame,
    read_git_diff,
    read_git_diff_hunks,
    read_git_log,
    read_git_show,
)
from .workspace_git_stash_ops import (
    apply_git_stash,
    dedupe_paths,
    drop_git_stash,
    git_stash_candidate_paths,
    normalize_git_stash_message,
    parse_git_stash_list,
    preview_apply_git_stash,
    preview_drop_git_stash,
    preview_stash_git_changes,
    read_git_stashes,
    stash_git_changes,
    validate_git_stash_ref,
)
from .workspace_project_info import list_search_files
from .workspace_resolve import resolve_inside_run
def read_git_status(workspace: RunWorkspace) -> GitCommandResult:
    return run_readonly_git(workspace.root, ["status", "--short", "--untracked-files=all"])


def read_git_conflicts(
    workspace: RunWorkspace,
    relative_path: str | None = None,
    max_markers: int = 200,
    max_files: int = 5000,
) -> dict[str, object]:
    if max_markers < 1:
        raise ValueError("max_markers must be at least 1.")
    if max_markers > 1000:
        raise ValueError("max_markers must be at most 1000.")
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 10000:
        raise ValueError("max_files must be at most 10000.")

    selected_path = relative_path.strip() if relative_path else None
    status_args = ["status", "--porcelain=v1", "-z", "--untracked-files=all"]
    if selected_path:
        resolve_inside_run(workspace.root, selected_path)
        status_args.extend(["--", selected_path])
    status_result = run_readonly_git(workspace.root, status_args)
    if not status_result.ok:
        return {
            "ok": False,
            "path": selected_path or ".",
            "unmerged": [],
            "unmerged_total": 0,
            "markers": [],
            "markers_total": 0,
            "scanned_files": 0,
            "total_files": 0,
            "truncated": False,
            "message": status_result.stderr or "git status failed.",
        }

    unmerged = parse_git_unmerged_status(status_result.stdout)
    try:
        files = list_search_files(workspace, selected_path)
    except ValueError as error:
        if selected_path and unmerged:
            files = []
        else:
            raise error

    scanned_files = files[:max_files]
    markers: list[dict[str, object]] = []
    markers_total = 0
    for relative in scanned_files:
        path = resolve_inside_run(workspace.root, relative)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for line_number, line in enumerate(lines, start=1):
            marker = next((item for item in GIT_CONFLICT_MARKERS if line.startswith(item)), None)
            if marker is None:
                continue
            markers_total += 1
            if len(markers) >= max_markers:
                continue
            markers.append(
                {
                    "path": relative,
                    "line": line_number,
                    "marker": marker,
                    "text": line.strip(),
                }
            )

    truncated = len(files) > len(scanned_files) or markers_total > len(markers)
    return {
        "ok": True,
        "path": selected_path or ".",
        "unmerged": unmerged,
        "unmerged_total": len(unmerged),
        "markers": markers,
        "markers_total": markers_total,
        "scanned_files": len(scanned_files),
        "total_files": len(files),
        "truncated": truncated,
        "message": (
            f"Found {len(unmerged)} unmerged file(s) and {markers_total} conflict marker(s) "
            f"in {len(scanned_files)}/{len(files)} scanned file(s)."
        ),
    }


def parse_git_unmerged_status(output: str) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    parts = [part for part in output.split("\0") if part]
    index = 0
    while index < len(parts):
        entry = parts[index]
        index += 1
        if len(entry) < 4:
            continue
        status = entry[:2]
        path = entry[3:]
        if status in {"R ", "C "} and index < len(parts):
            index += 1
        if status not in GIT_UNMERGED_STATUS_CODES:
            continue
        entries.append({"path": path, "status": status})
    return entries


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
    status_result = read_git_status(workspace)
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


def read_git_branches(workspace: RunWorkspace, max_branches: int = 100) -> dict[str, object]:
    if max_branches < 1:
        raise ValueError("max_branches must be at least 1.")
    if max_branches > 500:
        raise ValueError("max_branches must be at most 500.")
    git_probe = run_readonly_git(workspace.root, ["rev-parse", "--is-inside-work-tree"])
    if not git_probe.ok or git_probe.stdout.strip() != "true":
        return {
            "ok": False,
            "current": "",
            "branches": [],
            "total": 0,
            "truncated": False,
            "status": "",
            "message": git_probe.stderr or "Not a git repository.",
        }

    current_result = run_readonly_git(workspace.root, ["branch", "--show-current"])
    branches_result = run_readonly_git(workspace.root, ["branch", "--list", "--format=%(refname:short)"])
    status = read_git_status(workspace)
    if not branches_result.ok:
        return {
            "ok": False,
            "current": current_result.stdout.strip() if current_result.ok else "",
            "branches": [],
            "total": 0,
            "truncated": False,
            "status": status.stdout if status.ok else "",
            "message": branches_result.stderr or "git branch failed.",
        }

    current = current_result.stdout.strip() if current_result.ok else ""
    names = [line.strip() for line in branches_result.stdout.splitlines() if line.strip()]
    total = len(names)
    shown = names[:max_branches]
    return {
        "ok": True,
        "current": current,
        "branches": [{"name": name, "current": name == current} for name in shown],
        "total": total,
        "truncated": len(shown) < total,
        "status": status.stdout if status.ok else "",
        "message": f"Found {total} local git branch(es).",
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
    status = read_git_status(workspace)
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
    status = read_git_status(workspace)
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
    status = read_git_status(workspace)
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
    status = read_git_status(workspace)
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





def stage_git_paths(workspace: RunWorkspace, paths: list[str]) -> dict[str, object]:
    normalized = normalize_git_index_paths(workspace, paths)
    result = run_git_mutation(workspace.root, ["add", "--", *normalized])
    status = read_git_status(workspace)
    return {
        "ok": result.ok,
        "paths": normalized,
        "status": status.stdout if status.ok else "",
        "message": f"Staged {len(normalized)} path(s)." if result.ok else result.stderr or "git add failed.",
    }


def preview_stage_git_paths(workspace: RunWorkspace, paths: list[str]) -> dict[str, object]:
    normalized = normalize_git_index_paths(workspace, paths)
    status = read_git_status(workspace)
    return {
        "ok": status.ok,
        "paths": normalized,
        "status": status.stdout if status.ok else "",
        "message": f"Can stage {len(normalized)} path(s)." if status.ok else status.stderr or "git status failed.",
    }


def unstage_git_paths(workspace: RunWorkspace, paths: list[str]) -> dict[str, object]:
    normalized = normalize_git_index_paths(workspace, paths)
    result = run_git_mutation(workspace.root, ["restore", "--staged", "--", *normalized])
    status = read_git_status(workspace)
    return {
        "ok": result.ok,
        "paths": normalized,
        "status": status.stdout if status.ok else "",
        "message": f"Unstaged {len(normalized)} path(s)." if result.ok else result.stderr or "git restore --staged failed.",
    }


def preview_unstage_git_paths(workspace: RunWorkspace, paths: list[str]) -> dict[str, object]:
    normalized = normalize_git_index_paths(workspace, paths)
    status = read_git_status(workspace)
    return {
        "ok": status.ok,
        "paths": normalized,
        "status": status.stdout if status.ok else "",
        "message": f"Can unstage {len(normalized)} path(s)." if status.ok else status.stderr or "git status failed.",
    }


def preview_restore_git_paths(workspace: RunWorkspace, paths: list[str]) -> dict[str, object]:
    normalized = normalize_git_index_paths(workspace, paths)
    tracked = validate_git_tracked_paths(workspace, normalized)
    status = read_git_status(workspace)
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
    status = read_git_status(workspace)
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
            "status": read_git_status(workspace).stdout,
            "message": "No staged changes to commit.",
        }

    head_before = read_git_head(workspace)
    result = run_git_mutation(workspace.root, ["commit", "--no-verify", "-m", message])
    head_after = read_git_head(workspace)
    status = read_git_status(workspace)
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
    status = read_git_status(workspace)
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
    status = read_git_status(workspace)
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
    status = read_git_status(workspace)
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


def validate_git_branch_name(workspace: RunWorkspace, branch: str) -> str:
    normalized = branch.strip()
    if not normalized:
        raise ValueError("branch must be a non-empty string.")
    if len(normalized) > 200:
        raise ValueError("branch must be at most 200 characters.")
    result = run_readonly_git(workspace.root, ["check-ref-format", "--branch", normalized])
    if not result.ok:
        raise ValueError(result.stderr.strip() or f"Invalid git branch name: {normalized}")
    return normalized


def git_branch_exists(workspace: RunWorkspace, branch: str) -> bool:
    result = run_readonly_git(workspace.root, ["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"])
    return result.exit_code == 0


def read_git_current_branch(workspace: RunWorkspace) -> str:
    result = run_readonly_git(workspace.root, ["branch", "--show-current"])
    return result.stdout.strip() if result.ok else ""


def git_status_has_non_runtime_changes(status: str) -> bool:
    for line in status.splitlines():
        path = line[3:] if len(line) > 3 else line
        if path == ".vibeagent" or path.startswith(".vibeagent/"):
            continue
        return True
    return False


def read_git_head(workspace: RunWorkspace) -> str:
    result = run_readonly_git(workspace.root, ["rev-parse", "--short", "HEAD"])
    return result.stdout.strip() if result.ok else ""


def normalize_git_index_paths(workspace: RunWorkspace, paths: list[str]) -> list[str]:
    if not paths:
        raise ValueError("paths must contain at least one path.")
    if len(paths) > 100:
        raise ValueError("paths must contain at most 100 paths.")

    normalized: list[str] = []
    seen: set[str] = set()
    for path in paths:
        if not isinstance(path, str) or not path.strip():
            raise ValueError("paths must contain non-empty strings.")
        raw = path.strip()
        resolve_inside_run(workspace.root, raw)
        if raw not in seen:
            seen.add(raw)
            normalized.append(raw)
    return normalized
