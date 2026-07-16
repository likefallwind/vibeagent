from __future__ import annotations

from pathlib import Path

from .actions import execute_action
from .read_batch_commands import (
    get_read_files_report,
    get_read_files_text,
    get_read_ranges_report,
    get_read_ranges_text,
)
from .read_command_parsing import parse_around_many_argument, parse_around_request, parse_read_request, parse_tail_request, serialize_context_result
from .local_command_workspace import local_command_workspace
from .read_report_helpers import (
    format_around_many_report_text,
    format_around_report_text,
    format_read_files_report_text,
    format_read_ranges_report_text,
    format_read_report_text,
    format_tail_report_text,
    indent_block as _indent_block,
)
from .types import ReadFileAction, ReadFileContextAction, ReadFileContextsAction, TailFileAction

READ_USAGE = "Usage: /read <path> [start[:end]]"
TAIL_USAGE = "Usage: /tail <path> [lines]"
AROUND_USAGE = "Usage: /around <path> <line> [context-lines]"
AROUND_MANY_USAGE = "Usage: /around-many <path:line[:context-lines]...>"


def _read_failure_report(
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


def _usage_error(usage: str, error: object) -> str:
    return f"{usage}\nError: {error}"


def _tail_failure_report(
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


def _around_failure_report(
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


def _around_many_failure_report(
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


def get_read_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    line_range: str | None = None,
    max_bytes: int = 20_000,
    show_line_numbers: bool = False,
) -> str:
    return format_read_report_text(
        get_read_report(
            project_root,
            argument,
            line_range=line_range,
            max_bytes=max_bytes,
            show_line_numbers=show_line_numbers,
        )
    )


def get_read_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    line_range: str | None = None,
    max_bytes: int = 20_000,
    show_line_numbers: bool = False,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    if argument is None or not argument.strip():
        return _read_failure_report(
            root,
            READ_USAGE,
            max_bytes=max_bytes,
            show_line_numbers=show_line_numbers,
        )
    try:
        path, start_line, line_count, range_label = parse_read_request(argument, line_range)
    except ValueError as error:
        return _read_failure_report(
            root,
            _usage_error(READ_USAGE, error),
            max_bytes=max_bytes,
            show_line_numbers=show_line_numbers,
        )

    workspace = local_command_workspace(root, "local-read")
    observation = execute_action(
        workspace,
        ReadFileAction(
            type="read_file",
            path=path,
            start_line=start_line,
            line_count=line_count,
            max_bytes=max_bytes,
            show_line_numbers=show_line_numbers,
        ),
    )
    if observation.kind != "read_file":
        return _read_failure_report(
            root,
            f"Unexpected observation: {observation.kind}",
            path=path,
            range_label=range_label or ".",
            start_line=start_line,
            line_count=line_count,
            max_bytes=max_bytes,
            show_line_numbers=show_line_numbers,
        )
    return {
        "projectRoot": str(root),
        "ok": observation.total_bytes is not None,
        "path": observation.path,
        "range": range_label or ".",
        "startLine": start_line,
        "lineCount": line_count,
        "showLineNumbers": observation.show_line_numbers,
        "read": {
            "content": observation.content,
            "totalBytes": observation.total_bytes,
            "maxBytes": observation.max_bytes,
            "truncated": observation.truncated,
        },
        "message": observation.message,
    }


def get_tail_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    line_count: int | None = None,
    max_bytes: int = 20_000,
) -> str:
    return format_tail_report_text(
        get_tail_report(project_root, argument, line_count=line_count, max_bytes=max_bytes)
    )


def get_tail_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    line_count: int | None = None,
    max_bytes: int = 20_000,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    if max_bytes < 1_000:
        return _tail_failure_report(
            root,
            _usage_error(TAIL_USAGE, "max_bytes must be at least 1000."),
            requested_lines=line_count,
            max_bytes=max_bytes,
        )
    if max_bytes > 200_000:
        return _tail_failure_report(
            root,
            _usage_error(TAIL_USAGE, "max_bytes must be at most 200000."),
            requested_lines=line_count,
            max_bytes=max_bytes,
        )
    try:
        path, requested_lines = parse_tail_request(argument, line_count)
    except ValueError as error:
        return _tail_failure_report(
            root,
            _usage_error(TAIL_USAGE, error),
            requested_lines=line_count,
            max_bytes=max_bytes,
        )
    if path is None:
        return _tail_failure_report(
            root,
            TAIL_USAGE,
            requested_lines=requested_lines,
            max_bytes=max_bytes,
        )

    workspace = local_command_workspace(root, "local-tail")
    observation = execute_action(
        workspace,
        TailFileAction(type="tail_file", path=path, line_count=requested_lines, max_bytes=max_bytes),
    )
    if observation.kind != "tail_file":
        return _tail_failure_report(
            root,
            f"Unexpected observation: {observation.kind}",
            path=path,
            requested_lines=requested_lines,
            max_bytes=max_bytes,
        )
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "path": observation.path,
        "tail": {
            "content": observation.content,
            "totalLines": observation.total_lines,
            "lineCount": observation.line_count,
            "startLine": observation.start_line,
            "requestedLines": observation.requested_line_count,
            "maxBytes": observation.max_bytes,
            "truncated": observation.truncated,
        },
        "message": observation.message,
    }


def get_around_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    context_lines: int | None = None,
    max_bytes: int = 20_000,
) -> str:
    return format_around_report_text(
        get_around_report(project_root, argument, context_lines=context_lines, max_bytes=max_bytes)
    )


def get_around_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    context_lines: int | None = None,
    max_bytes: int = 20_000,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        path, line, selected_context = parse_around_request(argument, context_lines)
    except ValueError as error:
        return _around_failure_report(
            root,
            _usage_error(AROUND_USAGE, error),
            context_lines=context_lines,
            max_bytes=max_bytes,
        )
    if path is None or line is None:
        return _around_failure_report(
            root,
            AROUND_USAGE,
            context_lines=context_lines,
            max_bytes=max_bytes,
        )

    workspace = local_command_workspace(root, "local-around")
    observation = execute_action(
        workspace,
        ReadFileContextAction(
            type="read_file_context",
            path=path,
            line=line,
            context_lines=selected_context,
            max_bytes=max_bytes,
        ),
    )
    if observation.kind != "read_file_context":
        return _around_failure_report(
            root,
            f"Unexpected observation: {observation.kind}",
            path=path,
            line=line,
            context_lines=selected_context,
            max_bytes=max_bytes,
        )
    context = serialize_context_result(observation)
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "path": observation.path,
        "line": observation.line,
        "context": {key: value for key, value in context.items() if key not in {"path", "line", "ok"}},
        "message": observation.message,
    }


def get_around_many_text(
    project_root: str | Path = ".",
    argument: str | list[str] | None = None,
    max_bytes_per_context: int = 20_000,
) -> str:
    return format_around_many_report_text(
        get_around_many_report(project_root, argument, max_bytes_per_context=max_bytes_per_context)
    )


def get_around_many_report(
    project_root: str | Path = ".",
    argument: str | list[str] | None = None,
    max_bytes_per_context: int = 20_000,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    if max_bytes_per_context < 1_000:
        return _around_many_failure_report(
            root,
            _usage_error(AROUND_MANY_USAGE, "max_bytes_per_context must be at least 1000."),
            max_bytes_per_context=max_bytes_per_context,
        )
    if max_bytes_per_context > 200_000:
        return _around_many_failure_report(
            root,
            _usage_error(AROUND_MANY_USAGE, "max_bytes_per_context must be at most 200000."),
            max_bytes_per_context=max_bytes_per_context,
        )
    try:
        contexts = parse_around_many_argument(argument)
    except ValueError as error:
        return _around_many_failure_report(
            root,
            _usage_error(AROUND_MANY_USAGE, error),
            max_bytes_per_context=max_bytes_per_context,
        )
    if not contexts:
        return _around_many_failure_report(
            root,
            AROUND_MANY_USAGE,
            max_bytes_per_context=max_bytes_per_context,
        )

    workspace = local_command_workspace(root, "local-around-many")
    observation = execute_action(
        workspace,
        ReadFileContextsAction(
            type="read_file_contexts",
            contexts=contexts,
            max_bytes_per_context=max_bytes_per_context,
        ),
    )
    if observation.kind != "read_file_contexts":
        return _around_many_failure_report(
            root,
            f"Unexpected observation: {observation.kind}",
            total=len(contexts),
            max_bytes_per_context=max_bytes_per_context,
        )

    items = [serialize_context_result(item) for item in observation.contexts]
    ok_count = sum(1 for item in items if item["ok"])
    return {
        "projectRoot": str(root),
        "ok": ok_count == len(items),
        "contexts": {"ok": ok_count, "total": len(items), "items": items},
        "maxBytesPerContext": max_bytes_per_context,
        "message": observation.message,
    }
