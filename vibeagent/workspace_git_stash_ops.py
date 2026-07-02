from __future__ import annotations

import re

from .workspace_core import GitCommandResult, RunWorkspace
from .workspace_git_utils import run_git_mutation, run_readonly_git


def read_git_stashes(workspace: RunWorkspace, max_entries: int = 20) -> dict[str, object]:
    if max_entries < 1:
        raise ValueError("max_entries must be at least 1.")
    if max_entries > 100:
        raise ValueError("max_entries must be at most 100.")

    result = run_readonly_git(workspace.root, ["stash", "list", "--format=%gd%x09%gs"])
    if not result.ok:
        return {"ok": False, "entries": [], "total": 0, "truncated": False, "message": result.stderr or "git stash list failed."}

    entries = parse_git_stash_list(result.stdout)
    shown = entries[:max_entries]
    return {
        "ok": True,
        "entries": shown,
        "total": len(entries),
        "truncated": len(shown) < len(entries),
        "message": f"Found {len(entries)} git stash entr{'y' if len(entries) == 1 else 'ies'}.",
    }


def preview_stash_git_changes(workspace: RunWorkspace, message: str | None = None, include_untracked: bool = False) -> dict[str, object]:
    stash_message = normalize_git_stash_message(message)
    status = _read_git_status(workspace)
    if not status.ok:
        return {
            "ok": False,
            "message_text": stash_message,
            "include_untracked": include_untracked,
            "paths": [],
            "status": "",
            "diff": "",
            "message": status.stderr or "git status failed.",
        }

    tracked_paths, untracked_paths = git_stash_candidate_paths(status.stdout)
    paths = tracked_paths + (untracked_paths if include_untracked else [])
    if not paths:
        return {
            "ok": False,
            "message_text": stash_message,
            "include_untracked": include_untracked,
            "paths": [],
            "status": status.stdout,
            "diff": "",
            "message": "No stashable non-runtime changes found.",
        }

    diff = run_readonly_git(workspace.root, ["diff", "HEAD", "--", *tracked_paths]) if tracked_paths else GitCommandResult(True, "", "", 0)
    if not diff.ok:
        return {
            "ok": False,
            "message_text": stash_message,
            "include_untracked": include_untracked,
            "paths": paths,
            "status": status.stdout,
            "diff": "",
            "message": diff.stderr or "git diff failed.",
        }

    return {
        "ok": True,
        "message_text": stash_message,
        "include_untracked": include_untracked,
        "paths": paths,
        "status": status.stdout,
        "diff": diff.stdout,
        "message": f"Can stash {len(paths)} path(s).",
    }


def stash_git_changes(workspace: RunWorkspace, message: str | None = None, include_untracked: bool = False) -> dict[str, object]:
    preview = preview_stash_git_changes(workspace, message, include_untracked=include_untracked)
    if not preview["ok"]:
        return {
            "ok": False,
            "message_text": str(preview["message_text"]),
            "include_untracked": include_untracked,
            "stash_ref": "",
            "status": str(preview["status"]),
            "diff": str(preview["diff"]),
            "message": str(preview["message"]),
        }

    before = read_git_stashes(workspace, max_entries=1)
    before_ref = str(before["entries"][0]["name"]) if before["ok"] and before["entries"] else ""
    args = ["stash", "push", "-m", str(preview["message_text"])]
    if include_untracked:
        args.append("--include-untracked")
    args.extend(["--", *list(preview["paths"])])
    result = run_git_mutation(workspace.root, args)
    after = read_git_stashes(workspace, max_entries=1)
    after_ref = str(after["entries"][0]["name"]) if after["ok"] and after["entries"] else ""
    status = _read_git_status(workspace)
    created_ref = after_ref if result.ok and after_ref != before_ref else after_ref
    return {
        "ok": result.ok,
        "message_text": str(preview["message_text"]),
        "include_untracked": include_untracked,
        "stash_ref": created_ref,
        "status": status.stdout if status.ok else "",
        "diff": str(preview["diff"]),
        "message": f"Stashed changes as {created_ref or 'a new stash'}." if result.ok else result.stderr or "git stash push failed.",
    }


def preview_apply_git_stash(workspace: RunWorkspace, stash_ref: str) -> dict[str, object]:
    normalized = validate_git_stash_ref(stash_ref)
    status = _read_git_status(workspace)
    if not status.ok:
        return {
            "ok": False,
            "stash_ref": normalized,
            "worktree_clean": False,
            "patch": "",
            "status": "",
            "message": status.stderr or "git status failed.",
        }
    clean = not _git_status_has_non_runtime_changes(status.stdout)
    patch = run_readonly_git(workspace.root, ["stash", "show", "--patch", normalized])
    if not patch.ok:
        return {
            "ok": False,
            "stash_ref": normalized,
            "worktree_clean": clean,
            "patch": "",
            "status": status.stdout,
            "message": patch.stderr or f"Git stash not found: {normalized}.",
        }
    if not clean:
        return {
            "ok": False,
            "stash_ref": normalized,
            "worktree_clean": False,
            "patch": patch.stdout,
            "status": status.stdout,
            "message": "Working tree has uncommitted changes; commit, stash, or restore changes before applying a stash.",
        }
    return {
        "ok": True,
        "stash_ref": normalized,
        "worktree_clean": True,
        "patch": patch.stdout,
        "status": status.stdout,
        "message": f"Can apply {normalized}.",
    }


def apply_git_stash(workspace: RunWorkspace, stash_ref: str) -> dict[str, object]:
    preview = preview_apply_git_stash(workspace, stash_ref)
    if not preview["ok"]:
        return {
            "ok": False,
            "stash_ref": str(preview["stash_ref"]),
            "patch": str(preview["patch"]),
            "status": str(preview["status"]),
            "message": str(preview["message"]),
        }
    result = run_git_mutation(workspace.root, ["stash", "apply", str(preview["stash_ref"])])
    status = _read_git_status(workspace)
    return {
        "ok": result.ok,
        "stash_ref": str(preview["stash_ref"]),
        "patch": str(preview["patch"]),
        "status": status.stdout if status.ok else "",
        "message": f"Applied {preview['stash_ref']}." if result.ok else result.stderr or "git stash apply failed.",
    }


def preview_drop_git_stash(workspace: RunWorkspace, stash_ref: str) -> dict[str, object]:
    normalized = validate_git_stash_ref(stash_ref)
    stashes = read_git_stashes(workspace, max_entries=100)
    if not stashes["ok"]:
        return {
            "ok": False,
            "stash_ref": normalized,
            "patch": "",
            "summary": "",
            "message": str(stashes["message"]),
        }
    summary = ""
    for entry in list(stashes["entries"]):
        if str(entry["name"]) == normalized:
            summary = str(entry["summary"])
            break
    if not summary:
        return {
            "ok": False,
            "stash_ref": normalized,
            "patch": "",
            "summary": "",
            "message": f"Git stash not found: {normalized}.",
        }

    patch = run_readonly_git(workspace.root, ["stash", "show", "--patch", normalized])
    if not patch.ok:
        return {
            "ok": False,
            "stash_ref": normalized,
            "patch": "",
            "summary": summary,
            "message": patch.stderr or f"Git stash not found: {normalized}.",
        }
    return {
        "ok": True,
        "stash_ref": normalized,
        "patch": patch.stdout,
        "summary": summary,
        "message": f"Can drop {normalized}.",
    }


def drop_git_stash(workspace: RunWorkspace, stash_ref: str) -> dict[str, object]:
    preview = preview_drop_git_stash(workspace, stash_ref)
    if not preview["ok"]:
        return {
            "ok": False,
            "stash_ref": str(preview["stash_ref"]),
            "patch": str(preview["patch"]),
            "summary": str(preview["summary"]),
            "remaining_total": int(read_git_stashes(workspace, max_entries=100).get("total", 0)),
            "message": str(preview["message"]),
        }
    result = run_git_mutation(workspace.root, ["stash", "drop", str(preview["stash_ref"])])
    remaining = read_git_stashes(workspace, max_entries=100)
    return {
        "ok": result.ok,
        "stash_ref": str(preview["stash_ref"]),
        "patch": str(preview["patch"]),
        "summary": str(preview["summary"]),
        "remaining_total": int(remaining["total"]) if remaining["ok"] else 0,
        "message": f"Dropped {preview['stash_ref']}." if result.ok else result.stderr or "git stash drop failed.",
    }


def parse_git_stash_list(output: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        name, _separator, summary = line.partition("\t")
        entries.append({"name": name.strip(), "summary": summary.strip()})
    return entries


def validate_git_stash_ref(stash_ref: str) -> str:
    normalized = stash_ref.strip() if isinstance(stash_ref, str) else ""
    if not normalized:
        raise ValueError("stash_ref must be a non-empty string.")
    if not re.fullmatch(r"stash@\{\d+\}", normalized):
        raise ValueError("stash_ref must look like stash@{0}.")
    return normalized


def normalize_git_stash_message(message: str | None) -> str:
    if message is None:
        return "vibeagent stash"
    normalized = message.strip()
    if not normalized:
        raise ValueError("message must be non-empty when provided.")
    if len(normalized) > 200:
        raise ValueError("message must be at most 200 characters.")
    return normalized


def git_stash_candidate_paths(status: str) -> tuple[list[str], list[str]]:
    tracked: list[str] = []
    untracked: list[str] = []
    for line in status.splitlines():
        if len(line) < 4:
            continue
        raw_path = line[3:]
        if " -> " in raw_path:
            raw_path = raw_path.rsplit(" -> ", 1)[1]
        if raw_path == ".vibeagent" or raw_path.startswith(".vibeagent/"):
            continue
        if line.startswith("?? "):
            untracked.append(raw_path)
        else:
            tracked.append(raw_path)
    return dedupe_paths(tracked), dedupe_paths(untracked)


def dedupe_paths(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            result.append(path)
    return result


def _read_git_status(workspace: RunWorkspace) -> GitCommandResult:
    return run_readonly_git(workspace.root, ["status", "--short", "--untracked-files=all"])


def _git_status_has_non_runtime_changes(status: str) -> bool:
    for line in status.splitlines():
        if len(line) < 4:
            continue
        path = line[3:]
        if path == ".vibeagent" or path.startswith(".vibeagent/"):
            continue
        return True
    return False
