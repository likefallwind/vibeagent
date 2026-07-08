from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .final_review_git_safety import (
    changed_symlink_target_risk,
    find_changed_gitlinks,
    find_hidden_tracked_git_changes,
    find_nested_git_repositories,
    find_unsafe_changed_symlinks,
    gitlink_path_from_raw_diff_line,
    read_changed_symlink_target,
    read_git_operation_state,
    symlink_path_from_raw_diff_line,
)
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
