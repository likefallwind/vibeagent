from __future__ import annotations

import fnmatch
import re
from pathlib import Path

from .workspace_core import RunWorkspace
from .workspace_file_read import read_project_file_context_result
from .workspace_path_discovery import (
    build_repo_map,
    find_project_files_result,
    glob_project_files,
    list_project_files,
    list_project_tree,
    list_tree_entry_matches_ignore,
    normalize_list_tree_ignore,
    validate_glob_pattern,
)
from .workspace_search_files import list_search_files
from .workspace_resolve import resolve_inside_run


def search_project(
    workspace: RunWorkspace,
    query: str,
    max_matches: int = 80,
    relative_path: str | None = None,
    file_glob: str | None = None,
    output_mode: str = "lines",
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
            output_mode=output_mode,
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
    output_mode: str = "lines",
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
    if output_mode not in {"lines", "content", "files_with_matches", "count"}:
        raise ValueError("output_mode must be lines, content, files_with_matches, or count.")
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
        path = resolve_inside_run(workspace, relative)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        if output_mode == "files_with_matches":
            if search_file_has_match(lines, pattern, needle, case_sensitive):
                total += 1
                if len(matches) < max_matches:
                    matches.append(relative)
            continue
        file_matches = search_file_line_matches(lines, pattern, needle, case_sensitive)
        if output_mode == "count":
            if file_matches:
                total += 1
                if len(matches) < max_matches:
                    matches.append(f"{relative}: {len(file_matches)}")
            continue
        for line_number, line in file_matches:
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


def search_file_line_matches(
    lines: list[str],
    pattern: re.Pattern[str] | None,
    needle: str,
    case_sensitive: bool,
) -> list[tuple[int, str]]:
    matches: list[tuple[int, str]] = []
    for line_number, line in enumerate(lines, start=1):
        if search_line_matches(line, pattern, needle, case_sensitive):
            matches.append((line_number, line))
    return matches


def search_file_has_match(
    lines: list[str],
    pattern: re.Pattern[str] | None,
    needle: str,
    case_sensitive: bool,
) -> bool:
    for line in lines:
        if search_line_matches(line, pattern, needle, case_sensitive):
            return True
    return False


def search_line_matches(
    line: str,
    pattern: re.Pattern[str] | None,
    needle: str,
    case_sensitive: bool,
) -> bool:
    if pattern is not None:
        return bool(pattern.search(line))
    haystack = line if case_sensitive else line.lower()
    return needle in haystack


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
        path = resolve_inside_run(workspace, relative)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(lines, start=1):
            if not search_line_matches(line, pattern, needle, case_sensitive):
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


def format_search_context(relative_path: str, lines: list[str], line_number: int, context_lines: int) -> str:
    start = max(1, line_number - context_lines)
    end = min(len(lines), line_number + context_lines)
    parts = []
    for current in range(start, end + 1):
        marker = ">" if current == line_number else " "
        parts.append(f"{relative_path}:{current}:{marker} {lines[current - 1]}")
    return "\n".join(parts)
