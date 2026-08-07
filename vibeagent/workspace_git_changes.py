from __future__ import annotations

from .workspace_core import RunWorkspace
from .workspace_git_ops import read_git_status
from .workspace_git_utils import (
    empty_git_change,
    parse_git_numstat,
    parse_git_short_status,
    run_readonly_git,
    should_ignore_git_path,
)


def read_git_changes(workspace: RunWorkspace) -> dict[str, object]:
    status = read_git_status(workspace)
    if not status.ok:
        return {
            "ok": False,
            "files": [],
            "status": status.stdout,
            "message": status.stderr or "git status failed.",
        }

    unstaged = run_readonly_git(workspace.root, ["diff", "--numstat"])
    staged = run_readonly_git(workspace.root, ["diff", "--cached", "--numstat"])
    if not unstaged.ok:
        return {"ok": False, "files": [], "status": status.stdout, "message": unstaged.stderr or "git diff failed."}
    if not staged.ok:
        return {"ok": False, "files": [], "status": status.stdout, "message": staged.stderr or "git diff --cached failed."}

    entries: dict[str, dict[str, object]] = {}
    for path, short_status in parse_git_short_status(status.stdout):
        if should_ignore_git_path(workspace.root, path):
            continue
        entry = entries.setdefault(path, empty_git_change(path))
        entry["status"] = short_status
        entry["staged"] = short_status[:1] not in {" ", "?"}
        entry["unstaged"] = short_status[1:2] not in {" ", ""}
        if short_status == "??":
            entry["untracked"] = True

    for path, insertions, deletions, binary in parse_git_numstat(staged.stdout):
        if should_ignore_git_path(workspace.root, path):
            continue
        entry = entries.setdefault(path, empty_git_change(path))
        entry["staged"] = True
        entry["staged_insertions"] = insertions
        entry["staged_deletions"] = deletions
        entry["binary"] = bool(entry["binary"]) or binary

    for path, insertions, deletions, binary in parse_git_numstat(unstaged.stdout):
        if should_ignore_git_path(workspace.root, path):
            continue
        entry = entries.setdefault(path, empty_git_change(path))
        entry["unstaged"] = True
        entry["unstaged_insertions"] = insertions
        entry["unstaged_deletions"] = deletions
        entry["binary"] = bool(entry["binary"]) or binary

    files = sorted(entries.values(), key=lambda item: str(item["path"]))
    message = f"Found {len(files)} changed file(s)."
    return {"ok": True, "files": files, "status": status.stdout, "message": message}
