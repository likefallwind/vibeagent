from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .final_review_secret_scan import (
    FINAL_REVIEW_SECRET_SCAN_BYTES,
    SECRET_LIKE_PATTERNS,
    find_secret_like_changed_files,
    find_secret_like_git_diff_additions,
    normalize_diff_new_file_path,
    parse_diff_hunk_new_start,
    secret_like_assignment_is_high_confidence,
    secret_like_git_diff_addition_findings,
    secret_like_line_label,
)
from .final_review_session_verification import final_review_session_verification_issues
from .session_verification_state import (
    SESSION_PROJECT_CHANGE_RESULT_KINDS as PROJECT_CHANGE_RESULT_KINDS,
)
from .types import FocusedTestCommand, SuggestedCheck
from .workspace_core import RunWorkspace
from .workspace_git_utils import parse_git_short_status, run_readonly_git, should_ignore_git_path
from .workspace import (
    is_protected_project_path,
    read_git_status,
    should_ignore_path,
)


FINAL_REVIEW_LARGE_FILE_BYTES = 100 * 1024 * 1024


def find_large_changed_files(
    workspace: RunWorkspace,
    files: list[dict[str, object]],
    max_bytes: int | None = None,
    max_files: int = 10,
) -> tuple[list[dict[str, object]], int]:
    size_limit = FINAL_REVIEW_LARGE_FILE_BYTES if max_bytes is None else max_bytes
    root = workspace.root.resolve()
    large_files: list[dict[str, object]] = []
    total = 0
    for item in files:
        raw_path = item.get("path") if isinstance(item, dict) else None
        if not isinstance(raw_path, str) or not raw_path:
            continue
        try:
            path = (root / raw_path).resolve()
            if path != root and root not in path.parents:
                continue
            if not path.is_file():
                continue
            size_bytes = path.stat().st_size
        except OSError:
            continue
        if size_bytes <= size_limit:
            continue
        total += 1
        if len(large_files) < max_files:
            large_files.append({"path": raw_path, "size_bytes": size_bytes})
    return large_files, total


def final_review_scan_file_items(workspace: RunWorkspace, files: list[dict[str, object]]) -> list[dict[str, object]]:
    by_path: dict[str, dict[str, object]] = {}
    for item in files:
        raw_path = item.get("path") if isinstance(item, dict) else None
        if isinstance(raw_path, str) and raw_path:
            by_path.setdefault(raw_path, item)
    for path in session_project_change_paths(workspace):
        by_path.setdefault(path, {"path": path, "status": "session"})
    return list(by_path.values())


def session_project_change_paths(workspace: RunWorkspace) -> list[str]:
    events_path = workspace.session_dir / "events.jsonl"
    try:
        lines = events_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []

    paths: set[str] = set()
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict) or event.get("type") != "tool_result":
            continue
        result = event.get("result")
        if not isinstance(result, dict):
            continue
        if result.get("kind") not in PROJECT_CHANGE_RESULT_KINDS or result.get("ok") is not True:
            continue
        paths.update(extract_project_change_result_paths(result))
    return sorted(paths)


def extract_project_change_result_paths(value: Any) -> set[str]:
    paths: set[str] = set()
    if not isinstance(value, dict):
        return paths
    for key in ("path", "source", "destination"):
        item = value.get(key)
        if isinstance(item, str):
            add_project_change_result_path(paths, item)
    for key in ("paths", "files", "transfers"):
        item = value.get(key)
        if isinstance(item, list):
            for child in item:
                if isinstance(child, str):
                    add_project_change_result_path(paths, child)
                elif isinstance(child, dict):
                    paths.update(extract_project_change_result_paths(child))
        elif isinstance(item, dict):
            paths.update(extract_project_change_result_paths(item))
    return paths


def add_project_change_result_path(paths: set[str], value: str) -> None:
    path = value.strip()
    if not path or "\n" in path:
        return
    if path.startswith("-") or "://" in path:
        return
    candidate = Path(path)
    if candidate.is_absolute() or ".." in candidate.parts:
        return
    paths.add(path)


def find_nested_git_repositories(workspace: RunWorkspace, max_repos: int = 10) -> tuple[list[str], int]:
    root = workspace.root.resolve()
    ignored_dirs = {
        ".agents",
        ".codex",
        ".git",
        ".pytest_cache",
        ".venv",
        ".vibeagent",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
    }
    repos: list[str] = []
    total = 0
    for current, dirs, files in os.walk(root):
        current_path = Path(current)
        if current_path == root:
            if ".git" in dirs:
                dirs.remove(".git")
        elif ".git" in dirs or ".git" in files:
            total += 1
            if len(repos) < max_repos:
                repos.append(current_path.relative_to(root).as_posix())
            if ".git" in dirs:
                dirs.remove(".git")
        dirs[:] = [
            name
            for name in dirs
            if name not in ignored_dirs and not name.endswith(".egg-info")
        ]
    return repos, total


def find_changed_gitlinks(workspace: RunWorkspace, max_links: int = 10) -> tuple[list[str], int, list[str]]:
    links: list[str] = []
    total = 0
    warnings: list[str] = []
    seen: set[str] = set()
    for diff_args in (
        ["diff", "--raw", "--no-renames"],
        ["diff", "--cached", "--raw", "--no-renames"],
    ):
        result = run_readonly_git(workspace.root, diff_args)
        if not result.ok:
            warnings.append(result.stderr.strip() or f"git {' '.join(diff_args)} failed")
            continue
        for line in result.stdout.splitlines():
            path = gitlink_path_from_raw_diff_line(line)
            if path is None or path in seen:
                continue
            seen.add(path)
            total += 1
            if len(links) < max_links:
                links.append(path)
    return links, total, warnings


def gitlink_path_from_raw_diff_line(line: str) -> str | None:
    metadata, separator, path = line.partition("\t")
    if not separator:
        return None
    fields = metadata.split()
    if len(fields) < 2:
        return None
    old_mode = fields[0].removeprefix(":")
    new_mode = fields[1]
    if old_mode != "160000" and new_mode != "160000":
        return None
    return path.strip() or None


def find_hidden_tracked_git_changes(workspace: RunWorkspace, max_files: int = 10) -> tuple[list[dict[str, str]], int, list[str]]:
    status = read_git_status(workspace)
    if not status.ok:
        return [], 0, [status.stderr.strip() or "git status failed"]
    findings: list[dict[str, str]] = []
    total = 0
    for path, short_status in parse_git_short_status(status.stdout):
        if short_status == "??":
            continue
        if not should_ignore_git_path(workspace.root, path):
            continue
        total += 1
        if len(findings) < max_files:
            findings.append({"path": path, "status": short_status})
    return findings, total, []


def find_unsafe_changed_symlinks(
    workspace: RunWorkspace,
    files: list[dict[str, object]],
    max_links: int = 10,
) -> tuple[list[dict[str, str]], int, list[str], set[str]]:
    root = workspace.root.resolve()
    candidates: dict[str, str] = {}
    warnings: list[str] = []

    for item in files:
        raw_path = item.get("path") if isinstance(item, dict) else None
        if not isinstance(raw_path, str) or not raw_path:
            continue
        link_path = root / raw_path
        try:
            if link_path.is_symlink():
                candidates.setdefault(raw_path, "worktree")
        except OSError:
            continue

    for diff_args, source in (
        (["diff", "--raw", "--no-renames"], "worktree"),
        (["diff", "--cached", "--raw", "--no-renames"], "index"),
    ):
        result = run_readonly_git(workspace.root, diff_args)
        if not result.ok:
            warnings.append(result.stderr.strip() or f"git {' '.join(diff_args)} failed")
            continue
        for line in result.stdout.splitlines():
            path = symlink_path_from_raw_diff_line(line)
            if path is not None:
                candidates.setdefault(path, source)

    findings: list[dict[str, str]] = []
    reasons: set[str] = set()
    total = 0
    for relative_path, source in sorted(candidates.items()):
        target = read_changed_symlink_target(workspace, relative_path, source)
        if target is None:
            continue
        risk = changed_symlink_target_risk(root, root / relative_path, target)
        if risk is None:
            continue
        reasons.add(risk)
        total += 1
        if len(findings) < max_links:
            findings.append({"path": relative_path, "target": target, "reason": risk})
    return findings, total, warnings, reasons


def symlink_path_from_raw_diff_line(line: str) -> str | None:
    metadata, separator, path = line.partition("\t")
    if not separator:
        return None
    fields = metadata.split()
    if len(fields) < 2:
        return None
    new_mode = fields[1]
    if new_mode != "120000":
        return None
    return path.strip() or None


def read_changed_symlink_target(workspace: RunWorkspace, relative_path: str, source: str) -> str | None:
    link_path = workspace.root / relative_path
    if source == "worktree" or link_path.is_symlink():
        try:
            return os.readlink(link_path)
        except OSError:
            if source == "worktree":
                return None
    result = run_readonly_git(workspace.root, ["show", f":{relative_path}"])
    if not result.ok:
        return None
    target = result.stdout.strip()
    return target or None


def changed_symlink_target_risk(root: Path, link_path: Path, target: str) -> str | None:
    target_path = Path(target)
    if target_path.is_absolute():
        resolved = target_path.resolve(strict=False)
    else:
        resolved = (link_path.parent / target_path).resolve(strict=False)
    if resolved != root and root not in resolved.parents:
        return "points outside project"
    if is_protected_project_path(root, resolved):
        return "points into protected project path"
    if should_ignore_path(root, resolved):
        return "points into ignored project path"
    return None


def read_git_operation_state(workspace: RunWorkspace) -> dict[str, object]:
    git_dir_result = run_readonly_git(workspace.root, ["rev-parse", "--git-dir"])
    if not git_dir_result.ok:
        return {"ok": False, "operations": [], "message": git_dir_result.stderr or "Not a git repository."}
    raw_git_dir = git_dir_result.stdout.strip().splitlines()[0] if git_dir_result.stdout.strip() else ""
    if not raw_git_dir:
        return {"ok": False, "operations": [], "message": "Could not determine git dir."}
    git_dir = Path(raw_git_dir)
    if not git_dir.is_absolute():
        git_dir = (workspace.root / git_dir).resolve()
    operation_paths = (
        ("merge", "MERGE_HEAD"),
        ("cherry-pick", "CHERRY_PICK_HEAD"),
        ("revert", "REVERT_HEAD"),
        ("rebase", "rebase-merge"),
        ("rebase", "rebase-apply"),
        ("bisect", "BISECT_LOG"),
    )
    operations: list[dict[str, str]] = []
    seen: set[str] = set()
    for name, relative in operation_paths:
        if name in seen:
            continue
        if (git_dir / relative).exists():
            operations.append({"operation": name, "path": relative})
            seen.add(name)
    message = "No git operation in progress." if not operations else "Git operation in progress."
    return {"ok": True, "operations": operations, "message": message}
