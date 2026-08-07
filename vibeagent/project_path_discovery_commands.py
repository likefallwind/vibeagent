from __future__ import annotations

from pathlib import Path

from .local_command_workspace import local_command_workspace
from .project_command_utils import commands_attr, execute_action
from .project_path_discovery_formatting import (
    format_find_files_report_text,
    format_glob_report_text,
    format_tree_report_text,
    path_matches_failure_report as _path_matches_failure_report,
    tree_failure_report as _tree_failure_report,
)
from .types import FindFilesAction, GlobAction, ListTreeAction

FIND_FILES_USAGE = "Usage: /find-files [--path PATH] [--max-matches N] [--regex] [--case-sensitive] [--include-dirs] -- <query>"
GLOB_USAGE = "Usage: /glob [--max-matches N] [--include-dirs] -- <pattern>"


def get_find_files_report(
    project_root: str | Path = ".",
    query: str | None = None,
    path: str | None = None,
    max_matches: int = 100,
    regex: bool = False,
    case_sensitive: bool = False,
    include_dirs: bool = False,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    if query is None or not query.strip():
        return _path_matches_failure_report(
            root,
            FIND_FILES_USAGE,
            query="",
            path=path,
            max_matches=max_matches,
            regex=regex,
            case_sensitive=case_sensitive,
            include_dirs=include_dirs,
        )
    workspace = local_command_workspace(root, "local-find-files")
    observation = execute_action(
        workspace,
        FindFilesAction(
            type="find_files",
            query=query.strip(),
            path=path,
            max_matches=max_matches,
            regex=regex,
            case_sensitive=case_sensitive,
            include_dirs=include_dirs,
        ),
    )
    if observation.kind != "find_files":
        return _path_matches_failure_report(
            root,
            f"Unexpected observation: {observation.kind}",
            query=query.strip(),
            path=path,
            max_matches=max_matches,
            regex=regex,
            case_sensitive=case_sensitive,
            include_dirs=include_dirs,
        )
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "query": observation.query,
        "path": observation.path,
        "matches": {
            "shown": len(observation.matches),
            "total": observation.total,
            "truncated": observation.truncated,
            "files": list(observation.matches),
        },
        "maxMatches": max_matches,
        "regex": observation.regex,
        "caseSensitive": observation.case_sensitive,
        "includeDirs": observation.include_dirs,
        "message": observation.message,
    }


def get_find_files_text(
    project_root: str | Path = ".",
    query: str | None = None,
    path: str | None = None,
    max_matches: int = 100,
    regex: bool = False,
    case_sensitive: bool = False,
    include_dirs: bool = False,
) -> str:
    get_report = commands_attr("get_find_files_report", get_find_files_report)
    formatter = commands_attr("format_find_files_report_text", format_find_files_report_text)
    return formatter(
        get_report(
            project_root,
            query,
            path=path,
            max_matches=max_matches,
            regex=regex,
            case_sensitive=case_sensitive,
            include_dirs=include_dirs,
        )
    )


def get_glob_report(
    project_root: str | Path = ".",
    pattern: str | None = None,
    max_matches: int = 200,
    include_dirs: bool = False,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    if pattern is None or not pattern.strip():
        return _path_matches_failure_report(
            root,
            GLOB_USAGE,
            pattern="",
            max_matches=max_matches,
            include_dirs=include_dirs,
        )
    workspace = local_command_workspace(root, "local-glob")
    observation = execute_action(
        workspace,
        GlobAction(
            type="glob",
            pattern=pattern.strip(),
            max_matches=max_matches,
            include_dirs=include_dirs,
        ),
    )
    if observation.kind != "glob":
        return _path_matches_failure_report(
            root,
            f"Unexpected observation: {observation.kind}",
            pattern=pattern.strip(),
            max_matches=max_matches,
            include_dirs=include_dirs,
        )
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "pattern": observation.pattern,
        "matches": {
            "shown": len(observation.matches),
            "total": observation.total,
            "truncated": observation.truncated,
            "files": list(observation.matches),
        },
        "maxMatches": max_matches,
        "includeDirs": include_dirs,
        "message": observation.message,
    }


def get_glob_text(
    project_root: str | Path = ".",
    pattern: str | None = None,
    max_matches: int = 200,
    include_dirs: bool = False,
) -> str:
    get_report = commands_attr("get_glob_report", get_glob_report)
    formatter = commands_attr("format_glob_report_text", format_glob_report_text)
    return formatter(get_report(project_root, pattern, max_matches=max_matches, include_dirs=include_dirs))


def get_tree_report(
    project_root: str | Path = ".",
    path: str | None = None,
    max_depth: int = 3,
    max_entries: int = 200,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    selected_path = path.strip() if path else None
    workspace = local_command_workspace(root, "local-tree")
    observation = execute_action(
        workspace,
        ListTreeAction(
            type="list_tree",
            path=selected_path,
            max_depth=max_depth,
            max_entries=max_entries,
        ),
    )
    if observation.kind != "list_tree":
        return _tree_failure_report(
            root,
            f"Unexpected observation: {observation.kind}",
            path=selected_path or ".",
            max_depth=max_depth,
            max_entries=max_entries,
        )
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "path": observation.path,
        "entries": {
            "shown": len(observation.entries),
            "total": observation.total,
            "truncated": observation.truncated,
            "items": list(observation.entries),
        },
        "maxDepth": observation.max_depth,
        "maxEntries": max_entries,
        "message": observation.message,
    }


def get_tree_text(
    project_root: str | Path = ".",
    path: str | None = None,
    max_depth: int = 3,
    max_entries: int = 200,
) -> str:
    get_report = commands_attr("get_tree_report", get_tree_report)
    formatter = commands_attr("format_tree_report_text", format_tree_report_text)
    return formatter(get_report(project_root, path, max_depth=max_depth, max_entries=max_entries))
