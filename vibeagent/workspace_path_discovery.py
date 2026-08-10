from __future__ import annotations

import re
from pathlib import Path

from .workspace_core import RunWorkspace
from .workspace_paths import should_ignore_path
from .workspace_repo_map import build_repo_map
from .workspace_resolve import display_workspace_path, resolve_inside_run, workspace_root_for_path
from .workspace_tree_ignore import list_tree_entry_matches_ignore, normalize_list_tree_ignore


def find_project_files_result(
    workspace: RunWorkspace,
    query: str,
    max_matches: int = 100,
    relative_path: str | None = None,
    regex: bool = False,
    case_sensitive: bool = False,
    include_dirs: bool = False,
) -> dict[str, object]:
    if not query.strip():
        raise ValueError("File query must not be empty.")
    if max_matches < 1:
        raise ValueError("max_matches must be at least 1.")
    if max_matches > 500:
        raise ValueError("max_matches must be at most 500.")

    pattern = None
    needle = query if case_sensitive else query.lower()
    if regex:
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            pattern = re.compile(query, flags)
        except re.error as error:
            raise ValueError(f"Invalid regex query: {error}") from error

    root = workspace.root.resolve()
    if relative_path:
        base = resolve_inside_run(workspace, relative_path)
        if not base.exists():
            raise ValueError(f"Path does not exist: {relative_path}")
    else:
        base = root
    if base.is_file():
        candidates = [base]
    elif base.is_dir():
        candidates = sorted(base.rglob("*"))
    else:
        raise ValueError(f"Path is not a file or directory: {relative_path}")

    matches: list[str] = []
    total = 0
    for path in candidates:
        if path.is_symlink():
            continue
        if not path.is_file() and not (include_dirs and path.is_dir()):
            continue
        try:
            resolved = path.resolve()
        except OSError:
            continue
        access_root = workspace_root_for_path(workspace, resolved)
        if access_root is None or (base != root and workspace_root_for_path(workspace, base) != access_root):
            continue
        if should_ignore_path(access_root, resolved):
            continue
        relative = display_workspace_path(workspace, path)
        display = f"{relative}/" if path.is_dir() else relative
        haystack = display if case_sensitive else display.lower()
        found = bool(pattern.search(display)) if pattern else needle in haystack
        if not found:
            continue
        total += 1
        if len(matches) < max_matches:
            matches.append(display)

    return {
        "matches": matches,
        "total": total,
        "truncated": total > len(matches),
    }


def glob_project_files(workspace: RunWorkspace, pattern: str, max_matches: int = 200, include_dirs: bool = False) -> tuple[list[str], int]:
    if max_matches < 1:
        raise ValueError("max_matches must be at least 1.")
    if max_matches > 500:
        raise ValueError("max_matches must be at most 500.")

    raw_pattern = pattern.strip().replace("\\", "/")
    root = workspace.root.resolve()
    if Path(raw_pattern).is_absolute():
        selected_root = next(
            (
                candidate
                for candidate in (workspace.root.resolve(), *workspace.additional_roots)
                if raw_pattern == str(candidate) or raw_pattern.startswith(f"{candidate.as_posix()}/")
            ),
            None,
        )
        if selected_root is None:
            if not workspace.additional_roots:
                raise ValueError(f"Absolute paths are not allowed: {pattern}")
            raise ValueError(f"Path escapes the project directory: {pattern}")
        relative_pattern = raw_pattern[len(selected_root.as_posix()) :].lstrip("/") or "."
        normalized = validate_glob_pattern(relative_pattern)
        root = selected_root
    else:
        normalized = validate_glob_pattern(raw_pattern)
    matches: list[str] = []
    for path in sorted(root.glob(normalized)):
        if not path.is_file() and not (include_dirs and path.is_dir()):
            continue
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if resolved != root and root not in resolved.parents:
            continue
        if should_ignore_path(root, resolved):
            continue
        relative = display_workspace_path(workspace, path)
        if path.is_dir():
            relative = f"{relative}/"
        matches.append(relative)

    return matches[:max_matches], len(matches)


def validate_glob_pattern(pattern: str) -> str:
    normalized = pattern.strip().replace("\\", "/")
    if not normalized:
        raise ValueError("Glob pattern must not be empty.")
    if Path(normalized).is_absolute():
        raise ValueError(f"Absolute paths are not allowed: {pattern}")

    parts = [part for part in normalized.split("/") if part]
    if any(part == ".." for part in parts):
        raise ValueError(f"Path escapes the project directory: {pattern}")
    if parts and parts[0] in {".git", ".vibeagent"}:
        raise ValueError(f"Path is protected: {pattern}")
    return normalized


def list_project_files(workspace: RunWorkspace, relative_path: str | None = None, max_files: int = 200) -> tuple[list[str], int]:
    base = resolve_inside_run(workspace, relative_path or ".")
    access_root = workspace_root_for_path(workspace, base)
    if access_root is None:
        raise ValueError(f"Path escapes the project directory: {relative_path or '.'}")
    if not base.exists():
        raise ValueError(f"Path does not exist: {relative_path or '.'}")
    if base.is_file():
        return [display_workspace_path(workspace, base)], 1
    files = [
        display_workspace_path(workspace, path)
        for path in sorted(base.rglob("*"))
        if not path.is_symlink() and path.is_file() and not should_ignore_path(access_root, path)
    ]
    return files[:max_files], len(files)


def list_project_tree(
    workspace: RunWorkspace,
    relative_path: str | None = None,
    max_depth: int = 3,
    max_entries: int = 200,
    ignore: tuple[str, ...] = (),
) -> tuple[list[str], int]:
    if max_depth < 1:
        raise ValueError("max_depth must be at least 1.")
    if max_depth > 10:
        raise ValueError("max_depth must be at most 10.")
    if max_entries < 1:
        raise ValueError("max_entries must be at least 1.")
    if max_entries > 1000:
        raise ValueError("max_entries must be at most 1000.")
    ignore_globs = normalize_list_tree_ignore(ignore)

    root = workspace.root.resolve()
    base = resolve_inside_run(workspace, relative_path or ".")
    access_root = workspace_root_for_path(workspace, base)
    if access_root is None:
        raise ValueError(f"Path escapes the project directory: {relative_path or '.'}")
    if not base.exists():
        raise ValueError(f"Path does not exist: {relative_path or '.'}")
    if base != access_root and should_ignore_path(access_root, base):
        raise ValueError(f"Path is ignored: {relative_path or '.'}")
    if base.is_file():
        return [display_workspace_path(workspace, base)], 1

    entries: list[str] = []

    def walk(directory: Path, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            children = sorted(directory.iterdir(), key=lambda path: path.name)
        except OSError:
            return
        for child in children:
            try:
                resolved = child.resolve()
            except OSError:
                continue
            if resolved != access_root and access_root not in resolved.parents:
                continue
            if should_ignore_path(access_root, resolved):
                continue
            suffix = "/" if resolved.is_dir() else ""
            relative = f"{display_workspace_path(workspace, resolved)}{suffix}"
            base_relative = f"{resolved.relative_to(base).as_posix()}{suffix}"
            if list_tree_entry_matches_ignore(relative, ignore_globs) or list_tree_entry_matches_ignore(
                base_relative,
                ignore_globs,
            ):
                continue
            entries.append(relative)
            if resolved.is_dir():
                walk(resolved, depth + 1)

    walk(base, 1)
    return entries[:max_entries], len(entries)
