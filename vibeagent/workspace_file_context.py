from __future__ import annotations

from .workspace_core import RunWorkspace
from .workspace_file_helpers import (
    format_line_excerpt,
    read_utf8_text_file,
    truncate_utf8_text_bytes,
)
from .workspace_resolve import resolve_inside_run


def read_project_file_tail_result(
    workspace: RunWorkspace,
    relative_path: str,
    line_count: int = 80,
    max_bytes: int = 20_000,
) -> dict[str, object]:
    if line_count < 1:
        raise ValueError("line_count must be at least 1.")
    if line_count > 1000:
        raise ValueError("line_count must be at most 1000.")
    if max_bytes < 1000:
        raise ValueError("max_bytes must be at least 1000.")
    if max_bytes > 200_000:
        raise ValueError("max_bytes must be at most 200000.")
    target = resolve_inside_run(workspace, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")

    content = read_utf8_text_file(target, relative_path)
    lines = content.splitlines()
    total_lines = len(lines)
    start_line = max(1, total_lines - line_count + 1) if total_lines else 1
    excerpt = format_line_excerpt(content, start_line, line_count) if total_lines else ""
    truncated_by_lines = total_lines > line_count
    excerpt_bytes = len(excerpt.encode("utf-8"))
    truncated_by_bytes = excerpt_bytes > max_bytes
    if truncated_by_bytes:
        excerpt = f"{truncate_utf8_text_bytes(excerpt, max_bytes)}\n[file tail truncated]"

    returned_lines = 0 if not excerpt else len(excerpt.splitlines())
    return {
        "content": excerpt,
        "start_line": start_line,
        "line_count": returned_lines,
        "requested_line_count": line_count,
        "total_lines": total_lines,
        "truncated": truncated_by_lines or truncated_by_bytes,
        "max_bytes": max_bytes,
    }


def read_project_file_context_result(
    workspace: RunWorkspace,
    relative_path: str,
    line: int,
    context_lines: int = 20,
    max_bytes: int = 20_000,
) -> dict[str, object]:
    if line < 1:
        raise ValueError("line must be at least 1.")
    if context_lines < 0:
        raise ValueError("context_lines must be at least 0.")
    if context_lines > 500:
        raise ValueError("context_lines must be at most 500.")
    if max_bytes < 1000:
        raise ValueError("max_bytes must be at least 1000.")
    if max_bytes > 200_000:
        raise ValueError("max_bytes must be at most 200000.")
    target = resolve_inside_run(workspace, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")

    content = read_utf8_text_file(target, relative_path)
    lines = content.splitlines()
    total_lines = len(lines)
    if total_lines == 0:
        excerpt = ""
        start_line = 1
        returned_lines = 0
        end_line = 0
    else:
        start_line = max(1, line - context_lines)
        end_line = min(total_lines, line + context_lines)
        requested_count = min(1000, max(0, end_line - start_line + 1))
        end_line = start_line + requested_count - 1 if requested_count else start_line - 1
        excerpt = format_line_excerpt(content, start_line, requested_count) if requested_count else ""
        returned_lines = 0 if not excerpt else len(excerpt.splitlines())

    truncated_by_context = total_lines > returned_lines
    truncated_by_bytes = len(excerpt.encode("utf-8")) > max_bytes
    if truncated_by_bytes:
        excerpt = f"{truncate_utf8_text_bytes(excerpt, max_bytes)}\n[file context truncated]"
        returned_lines = len(excerpt.splitlines())

    return {
        "content": excerpt,
        "line": line,
        "context_lines": context_lines,
        "start_line": start_line,
        "end_line": end_line,
        "line_count": returned_lines,
        "total_lines": total_lines,
        "target_line_exists": 1 <= line <= total_lines,
        "truncated": truncated_by_context or truncated_by_bytes,
        "max_bytes": max_bytes,
    }


__all__ = ["read_project_file_context_result", "read_project_file_tail_result"]
