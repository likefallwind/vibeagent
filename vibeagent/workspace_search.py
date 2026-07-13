from __future__ import annotations

import fnmatch
import re
from pathlib import Path

from .workspace_code_intel import (
    code_language_for_path,
    read_code_outline,
    read_python_symbol_outline,
    supports_code_outline_path,
)
from .workspace_core import RunWorkspace
from .workspace_file_read import read_project_file_context_result
from .workspace_project_info import list_search_files
from .workspace_paths import should_ignore_path
from .workspace_resolve import resolve_inside_run


def search_project(
    workspace: RunWorkspace,
    query: str,
    max_matches: int = 80,
    relative_path: str | None = None,
    file_glob: str | None = None,
    regex: bool = False,
    case_sensitive: bool = True,
    context_lines: int = 0,
) -> list[str]:
    return list(
        search_project_result(
            workspace,
            query,
            max_matches=max_matches,
            relative_path=relative_path,
            file_glob=file_glob,
            regex=regex,
            case_sensitive=case_sensitive,
            context_lines=context_lines,
        )["matches"]
    )


def search_project_result(
    workspace: RunWorkspace,
    query: str,
    max_matches: int = 80,
    relative_path: str | None = None,
    file_glob: str | None = None,
    regex: bool = False,
    case_sensitive: bool = True,
    context_lines: int = 0,
) -> dict[str, object]:
    if not query.strip():
        raise ValueError("Search query must not be empty.")
    if max_matches < 1:
        raise ValueError("max_matches must be at least 1.")
    if max_matches > 500:
        raise ValueError("max_matches must be at most 500.")
    if context_lines < 0:
        raise ValueError("context_lines must be at least 0.")
    if context_lines > 5:
        raise ValueError("context_lines must be at most 5.")
    normalized_file_glob = normalize_search_file_glob(file_glob)

    pattern = None
    needle = query if case_sensitive else query.lower()
    if regex:
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            pattern = re.compile(query, flags)
        except re.error as error:
            raise ValueError(f"Invalid regex query: {error}") from error

    matches: list[str] = []
    total = 0
    for relative in list_search_files(workspace, relative_path):
        if not search_file_matches_glob(relative, normalized_file_glob):
            continue
        path = resolve_inside_run(workspace.root, relative)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(lines, start=1):
            haystack = line if case_sensitive else line.lower()
            found = bool(pattern.search(line)) if pattern else needle in haystack
            if found:
                total += 1
                if len(matches) < max_matches:
                    if context_lines:
                        matches.append(format_search_context(relative, lines, line_number, context_lines))
                    else:
                        matches.append(f"{relative}:{line_number}: {line.strip()}")
    return {
        "matches": matches,
        "total": total,
        "truncated": total > len(matches),
    }


def search_project_contexts_result(
    workspace: RunWorkspace,
    query: str,
    max_matches: int = 20,
    relative_path: str | None = None,
    file_glob: str | None = None,
    regex: bool = False,
    case_sensitive: bool = True,
    context_lines: int = 3,
    max_bytes_per_context: int = 20_000,
) -> dict[str, object]:
    if not query.strip():
        raise ValueError("Search query must not be empty.")
    if max_matches < 1:
        raise ValueError("max_matches must be at least 1.")
    if max_matches > 100:
        raise ValueError("max_matches must be at most 100.")
    if context_lines < 0:
        raise ValueError("context_lines must be at least 0.")
    if context_lines > 50:
        raise ValueError("context_lines must be at most 50.")
    if max_bytes_per_context < 1000:
        raise ValueError("max_bytes_per_context must be at least 1000.")
    if max_bytes_per_context > 200_000:
        raise ValueError("max_bytes_per_context must be at most 200000.")
    normalized_file_glob = normalize_search_file_glob(file_glob)

    pattern = None
    needle = query if case_sensitive else query.lower()
    if regex:
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            pattern = re.compile(query, flags)
        except re.error as error:
            raise ValueError(f"Invalid regex query: {error}") from error

    contexts: list[dict[str, object]] = []
    total = 0
    for relative in list_search_files(workspace, relative_path):
        if not search_file_matches_glob(relative, normalized_file_glob):
            continue
        path = resolve_inside_run(workspace.root, relative)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(lines, start=1):
            haystack = line if case_sensitive else line.lower()
            found = bool(pattern.search(line)) if pattern else needle in haystack
            if not found:
                continue
            total += 1
            if len(contexts) >= max_matches:
                continue
            context = read_project_file_context_result(
                workspace,
                relative,
                line=line_number,
                context_lines=context_lines,
                max_bytes=max_bytes_per_context,
            )
            contexts.append(
                {
                    "path": relative,
                    "line": line_number,
                    "matched_line": line,
                    "content": context["content"],
                    "context_lines": context["context_lines"],
                    "start_line": context["start_line"],
                    "end_line": context["end_line"],
                    "line_count": context["line_count"],
                    "total_lines": context["total_lines"],
                    "truncated": context["truncated"],
                    "max_bytes": context["max_bytes"],
                }
            )
    return {
        "contexts": contexts,
        "total": total,
        "truncated": total > len(contexts),
    }


def normalize_search_file_glob(file_glob: str | None) -> str | None:
    if file_glob is None:
        return None
    normalized = file_glob.strip().replace("\\", "/")
    if not normalized:
        raise ValueError("file_glob must not be empty.")
    return normalized


def search_file_matches_glob(relative_path: str, file_glob: str | None) -> bool:
    if file_glob is None:
        return True
    normalized_path = relative_path.replace("\\", "/")
    target = normalized_path if "/" in file_glob else Path(normalized_path).name
    return fnmatch.fnmatchcase(target, file_glob)


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
        base = resolve_inside_run(workspace.root, relative_path)
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
        if resolved != root and root not in resolved.parents:
            continue
        if should_ignore_path(root, resolved):
            continue
        relative = path.relative_to(root).as_posix()
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


def format_search_context(relative_path: str, lines: list[str], line_number: int, context_lines: int) -> str:
    start = max(1, line_number - context_lines)
    end = min(len(lines), line_number + context_lines)
    parts = []
    for current in range(start, end + 1):
        marker = ">" if current == line_number else " "
        parts.append(f"{relative_path}:{current}:{marker} {lines[current - 1]}")
    return "\n".join(parts)


def glob_project_files(workspace: RunWorkspace, pattern: str, max_matches: int = 200, include_dirs: bool = False) -> tuple[list[str], int]:
    if max_matches < 1:
        raise ValueError("max_matches must be at least 1.")
    if max_matches > 500:
        raise ValueError("max_matches must be at most 500.")

    normalized = validate_glob_pattern(pattern)
    root = workspace.root.resolve()
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
        relative = path.relative_to(root).as_posix()
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
    base = resolve_inside_run(workspace.root, relative_path or ".")
    if not base.exists():
        raise ValueError(f"Path does not exist: {relative_path or '.'}")
    if base.is_file():
        return [base.relative_to(workspace.root).as_posix()], 1
    files = [
        path.relative_to(workspace.root).as_posix()
        for path in sorted(base.rglob("*"))
        if not path.is_symlink() and path.is_file() and not should_ignore_path(workspace.root, path)
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
    base = resolve_inside_run(root, relative_path or ".")
    if not base.exists():
        raise ValueError(f"Path does not exist: {relative_path or '.'}")
    if base != root and should_ignore_path(root, base):
        raise ValueError(f"Path is ignored: {relative_path or '.'}")
    if base.is_file():
        return [base.relative_to(root).as_posix()], 1

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
            if resolved != root and root not in resolved.parents:
                continue
            if should_ignore_path(root, resolved):
                continue
            suffix = "/" if resolved.is_dir() else ""
            relative = f"{resolved.relative_to(root).as_posix()}{suffix}"
            if list_tree_entry_matches_ignore(relative, ignore_globs):
                continue
            entries.append(relative)
            if resolved.is_dir():
                walk(resolved, depth + 1)

    walk(base, 1)
    return entries[:max_entries], len(entries)


def normalize_list_tree_ignore(ignore: tuple[str, ...]) -> tuple[str, ...]:
    normalized: list[str] = []
    for pattern in ignore:
        item = pattern.strip().replace("\\", "/")
        if not item:
            raise ValueError("ignore patterns must not be empty.")
        normalized.append(item)
    return tuple(normalized)


def list_tree_entry_matches_ignore(relative_path: str, ignore_globs: tuple[str, ...]) -> bool:
    if not ignore_globs:
        return False
    normalized_path = relative_path.strip("/").replace("\\", "/")
    basename = Path(normalized_path).name
    for pattern in ignore_globs:
        normalized_pattern = pattern.strip("/").replace("\\", "/")
        if not normalized_pattern:
            continue
        if normalized_pattern.endswith("/**"):
            prefix = normalized_pattern[:-3].rstrip("/")
            if normalized_path == prefix or normalized_path.startswith(f"{prefix}/"):
                return True
        target = normalized_path if "/" in normalized_pattern else basename
        if fnmatch.fnmatchcase(target, normalized_pattern):
            return True
    return False


def build_repo_map(
    workspace: RunWorkspace,
    relative_path: str | None = None,
    max_depth: int = 3,
    max_files: int = 80,
    max_symbols: int = 120,
) -> dict[str, object]:
    if max_depth < 1:
        raise ValueError("max_depth must be at least 1.")
    if max_depth > 10:
        raise ValueError("max_depth must be at most 10.")
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 500:
        raise ValueError("max_files must be at most 500.")
    if max_symbols < 1:
        raise ValueError("max_symbols must be at least 1.")
    if max_symbols > 500:
        raise ValueError("max_symbols must be at most 500.")

    path_label = relative_path or "."
    tree_entries, total_tree_entries = list_project_tree(
        workspace,
        relative_path,
        max_depth=max_depth,
        max_entries=max_files,
    )
    files, total_files = list_project_files(workspace, relative_path, max_files=max_files)

    python_files: list[dict[str, object]] = []
    used_symbols = 0
    symbols_truncated = False
    for file in files:
        if not file.endswith(".py"):
            continue
        remaining = max_symbols - used_symbols
        if remaining <= 0:
            symbols_truncated = True
            break
        try:
            outline = read_python_symbol_outline(workspace, file, max_symbols=remaining)
            symbols = list(outline["symbols"])
            used_symbols += len(symbols)
            python_files.append(
                {
                    "path": file,
                    "ok": True,
                    "imports": list(outline["imports"]),
                    "symbols": symbols,
                    "message": str(outline["message"]),
                }
            )
            if used_symbols >= max_symbols and len(symbols) == remaining:
                symbols_truncated = True
        except ValueError as error:
            python_files.append(
                {
                    "path": file,
                    "ok": False,
                    "imports": [],
                    "symbols": [],
                    "message": str(error),
                }
            )

    code_files: list[dict[str, object]] = []
    used_code_symbols = 0
    code_symbols_truncated = False
    for file in files:
        if not supports_code_outline_path(file):
            continue
        remaining = max_symbols - used_code_symbols
        if remaining <= 0:
            code_symbols_truncated = True
            break
        try:
            outline = read_code_outline(workspace, file, max_symbols=remaining)
            symbols = list(outline["symbols"])
            used_code_symbols += len(symbols)
            code_files.append(
                {
                    "path": file,
                    "ok": True,
                    "language": str(outline["language"]),
                    "imports": list(outline["imports"]),
                    "symbols": symbols,
                    "message": str(outline["message"]),
                }
            )
            if used_code_symbols >= max_symbols and len(symbols) == remaining:
                code_symbols_truncated = True
        except ValueError as error:
            code_files.append(
                {
                    "path": file,
                    "ok": False,
                    "language": code_language_for_path(Path(file)),
                    "imports": [],
                    "symbols": [],
                    "message": str(error),
                }
            )

    truncated = len(tree_entries) < total_tree_entries or len(files) < total_files or symbols_truncated or code_symbols_truncated
    return {
        "path": path_label,
        "tree": tree_entries,
        "files": files,
        "python_files": python_files,
        "code_files": code_files,
        "total_tree_entries": total_tree_entries,
        "total_files": total_files,
        "truncated": truncated,
        "message": (
            f"Mapped {len(files)}/{total_files} file(s), "
            f"{len(python_files)} Python file(s), and {len(code_files)} source file(s)."
        ),
    }
