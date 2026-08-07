from __future__ import annotations

from pathlib import Path


def path_matches_failure_report(
    root: Path,
    message: str,
    *,
    query: str | None = None,
    pattern: str | None = None,
    path: str | None = None,
    max_matches: int,
    regex: bool | None = None,
    case_sensitive: bool | None = None,
    include_dirs: bool = False,
) -> dict[str, object]:
    report: dict[str, object] = {
        "projectRoot": str(root),
        "ok": False,
        "matches": {"shown": 0, "total": 0, "truncated": False, "files": []},
        "maxMatches": max_matches,
        "includeDirs": include_dirs,
        "message": message,
    }
    if query is not None:
        report.update(
            {
                "query": query,
                "path": path,
                "regex": bool(regex),
                "caseSensitive": bool(case_sensitive),
            }
        )
    if pattern is not None:
        report["pattern"] = pattern
    return report


def tree_failure_report(
    root: Path,
    message: str,
    *,
    path: str = ".",
    max_depth: int = 3,
    max_entries: int = 200,
) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "path": path,
        "entries": {"shown": 0, "total": 0, "truncated": False, "items": []},
        "maxDepth": max_depth,
        "maxEntries": max_entries,
        "message": message,
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
