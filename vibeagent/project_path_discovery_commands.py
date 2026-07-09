from __future__ import annotations

from pathlib import Path

from .project_command_utils import commands_attr, execute_action
from .types import FindFilesAction, GlobAction, ListTreeAction
from .workspace_core import RunWorkspace


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
        return {
            "projectRoot": str(root),
            "ok": False,
            "query": "",
            "path": path,
            "matches": {"shown": 0, "total": 0, "truncated": False, "files": []},
            "maxMatches": max_matches,
            "regex": regex,
            "caseSensitive": case_sensitive,
            "includeDirs": include_dirs,
            "message": "Usage: /find-files [--path PATH] [--max-matches N] [--regex] [--case-sensitive] [--include-dirs] -- <query>",
        }
    workspace = RunWorkspace(root=root, run_id="local-find-files", session_dir=root / ".vibeagent" / "sessions" / "local-find-files")
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
        return {
            "projectRoot": str(root),
            "ok": False,
            "query": query.strip(),
            "path": path,
            "matches": {"shown": 0, "total": 0, "truncated": False, "files": []},
            "maxMatches": max_matches,
            "regex": regex,
            "caseSensitive": case_sensitive,
            "includeDirs": include_dirs,
            "message": f"Unexpected observation: {observation.kind}",
        }
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


def format_find_files_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    matches = report.get("matches") if isinstance(report.get("matches"), dict) else {}
    files = matches.get("files") if isinstance(matches, dict) and isinstance(matches.get("files"), list) else []
    lines = [
        "Find Files:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  query: {report.get('query') or ''}",
        f"  path: {report.get('path') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  matches: {matches.get('shown', 0)}/{matches.get('total', 0)}",
        f"  regex: {'yes' if bool(report.get('regex')) else 'no'}",
        f"  caseSensitive: {'yes' if bool(report.get('caseSensitive')) else 'no'}",
        f"  includeDirs: {'yes' if bool(report.get('includeDirs')) else 'no'}",
        f"  truncated: {'yes' if bool(matches.get('truncated')) else 'no'}",
    ]
    if files:
        lines.append("  files:")
        lines.extend(f"    - {path}" for path in files)
    else:
        lines.append("  files: none")
    lines.append(f"  message: {message}")
    return "\n".join(lines)


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
        return {
            "projectRoot": str(root),
            "ok": False,
            "pattern": "",
            "matches": {"shown": 0, "total": 0, "truncated": False, "files": []},
            "maxMatches": max_matches,
            "includeDirs": include_dirs,
            "message": "Usage: /glob [--max-matches N] [--include-dirs] -- <pattern>",
        }
    workspace = RunWorkspace(root=root, run_id="local-glob", session_dir=root / ".vibeagent" / "sessions" / "local-glob")
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
        return {
            "projectRoot": str(root),
            "ok": False,
            "pattern": pattern.strip(),
            "matches": {"shown": 0, "total": 0, "truncated": False, "files": []},
            "maxMatches": max_matches,
            "includeDirs": include_dirs,
            "message": f"Unexpected observation: {observation.kind}",
        }
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


def format_glob_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    matches = report.get("matches") if isinstance(report.get("matches"), dict) else {}
    files = matches.get("files") if isinstance(matches, dict) and isinstance(matches.get("files"), list) else []
    lines = [
        "Glob:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  pattern: {report.get('pattern') or ''}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  matches: {matches.get('shown', 0)}/{matches.get('total', 0)}",
        f"  includeDirs: {'yes' if bool(report.get('includeDirs')) else 'no'}",
        f"  truncated: {'yes' if bool(matches.get('truncated')) else 'no'}",
    ]
    if files:
        lines.append("  files:")
        lines.extend(f"    - {path}" for path in files)
    else:
        lines.append("  files: none")
    lines.append(f"  message: {message}")
    return "\n".join(lines)


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
    workspace = RunWorkspace(root=root, run_id="local-tree", session_dir=root / ".vibeagent" / "sessions" / "local-tree")
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
        return {
            "projectRoot": str(root),
            "ok": False,
            "path": selected_path or ".",
            "entries": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "maxDepth": max_depth,
            "maxEntries": max_entries,
            "message": f"Unexpected observation: {observation.kind}",
        }
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


def format_tree_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    entries = report.get("entries") if isinstance(report.get("entries"), dict) else {}
    items = entries.get("items") if isinstance(entries, dict) and isinstance(entries.get("items"), list) else []
    lines = [
        "Tree:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  path: {report.get('path') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  entries: {entries.get('shown', 0)}/{entries.get('total', 0)}",
        f"  maxDepth: {report.get('maxDepth', 0)}",
        f"  truncated: {'yes' if bool(entries.get('truncated')) else 'no'}",
    ]
    if items:
        lines.append("  tree:")
        lines.extend(f"    - {entry}" for entry in items)
    else:
        lines.append("  tree: none")
    lines.append(f"  message: {message}")
    return "\n".join(lines)


def get_tree_text(
    project_root: str | Path = ".",
    path: str | None = None,
    max_depth: int = 3,
    max_entries: int = 200,
) -> str:
    get_report = commands_attr("get_tree_report", get_tree_report)
    formatter = commands_attr("format_tree_report_text", format_tree_report_text)
    return formatter(get_report(project_root, path, max_depth=max_depth, max_entries=max_entries))
