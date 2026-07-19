from __future__ import annotations

from pathlib import Path


READ_USAGE = "Usage: /read <path> [start[:end]]"
TAIL_USAGE = "Usage: /tail <path> [lines]"
AROUND_USAGE = "Usage: /around <path> <line> [context-lines]"
AROUND_MANY_USAGE = "Usage: /around-many <path:line[:context-lines]...>"


def usage_error(usage: str, error: object) -> str:
    return f"{usage}\nError: {error}"


def read_failure_report(
    root: Path,
    message: str,
    *,
    path: str = "",
    range_label: str = ".",
    start_line: int | None = None,
    line_count: int | None = None,
    max_bytes: int = 20_000,
    show_line_numbers: bool = False,
) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "path": path,
        "range": range_label,
        "startLine": start_line,
        "lineCount": line_count,
        "showLineNumbers": show_line_numbers,
        "read": {"content": "", "totalBytes": None, "maxBytes": max_bytes, "truncated": False},
        "message": message,
    }


def tail_failure_report(
    root: Path,
    message: str,
    *,
    path: str = "",
    requested_lines: int | None = None,
    max_bytes: int = 20_000,
) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "path": path,
        "tail": {
            "content": "",
            "totalLines": None,
            "lineCount": 0,
            "startLine": None,
            "requestedLines": requested_lines,
            "maxBytes": max_bytes,
            "truncated": False,
        },
        "message": message,
    }


def around_failure_report(
    root: Path,
    message: str,
    *,
    path: str = "",
    line: int | None = None,
    context_lines: int | None = None,
    max_bytes: int = 20_000,
) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "path": path,
        "line": line,
        "context": _empty_around_context(context_lines, max_bytes),
        "message": message,
    }


def around_many_failure_report(
    root: Path,
    message: str,
    *,
    total: int = 0,
    max_bytes_per_context: int = 20_000,
) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "contexts": {"ok": 0, "total": total, "items": []},
        "maxBytesPerContext": max_bytes_per_context,
        "message": message,
    }


def _empty_around_context(context_lines: int | None, max_bytes: int) -> dict[str, object]:
    return {
        "content": "",
        "startLine": None,
        "endLine": None,
        "contextLines": context_lines,
        "targetLineExists": False,
        "lineCount": 0,
        "totalLines": None,
        "maxBytes": max_bytes,
        "truncated": False,
    }
