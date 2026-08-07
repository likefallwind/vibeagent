from __future__ import annotations

from pathlib import Path

from .actions import execute_action
from .read_batch_commands import (
    get_read_files_report,
    get_read_files_text,
    get_read_ranges_report,
    get_read_ranges_text,
)
from .read_command_parsing import parse_read_request, parse_tail_request
from .read_context_commands import get_around_many_report, get_around_report
from .local_command_workspace import local_command_workspace
from .read_command_failures import (
    READ_USAGE,
    TAIL_USAGE,
    read_failure_report,
    tail_failure_report,
    usage_error,
)
from .read_report_helpers import (
    format_around_many_report_text,
    format_around_report_text,
    format_read_files_report_text,
    format_read_ranges_report_text,
    format_read_report_text,
    format_tail_report_text,
    indent_block as _indent_block,
)
from .types import ReadFileAction, TailFileAction


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
        return read_failure_report(
            root,
            READ_USAGE,
            max_bytes=max_bytes,
            show_line_numbers=show_line_numbers,
        )
    try:
        path, start_line, line_count, range_label = parse_read_request(argument, line_range)
    except ValueError as error:
        return read_failure_report(
            root,
            usage_error(READ_USAGE, error),
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
        return read_failure_report(
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
        return tail_failure_report(
            root,
            usage_error(TAIL_USAGE, "max_bytes must be at least 1000."),
            requested_lines=line_count,
            max_bytes=max_bytes,
        )
    if max_bytes > 200_000:
        return tail_failure_report(
            root,
            usage_error(TAIL_USAGE, "max_bytes must be at most 200000."),
            requested_lines=line_count,
            max_bytes=max_bytes,
        )
    try:
        path, requested_lines = parse_tail_request(argument, line_count)
    except ValueError as error:
        return tail_failure_report(
            root,
            usage_error(TAIL_USAGE, error),
            requested_lines=line_count,
            max_bytes=max_bytes,
        )
    if path is None:
        return tail_failure_report(
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
        return tail_failure_report(
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


def get_around_many_text(
    project_root: str | Path = ".",
    argument: str | list[str] | None = None,
    max_bytes_per_context: int = 20_000,
) -> str:
    return format_around_many_report_text(
        get_around_many_report(project_root, argument, max_bytes_per_context=max_bytes_per_context)
    )
