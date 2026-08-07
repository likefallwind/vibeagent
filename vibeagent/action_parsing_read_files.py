from __future__ import annotations

from typing import Any

from .action_parsing_helpers import (
    ActionParseError,
    parse_nonnegative_int,
    parse_optional_positive_int,
    parse_read_file_contexts,
    parse_read_file_paths,
    parse_read_file_ranges,
)
from .action_tool_alias_utils import truthy_alias_bool
from .types import (
    NotebookReadAction,
    ReadFileAction,
    ReadFileContextAction,
    ReadFileContextsAction,
    ReadFileRangesAction,
    ReadFilesAction,
    TailFileAction,
)


READ_FILE_ACTION_TYPES = {
    "read_file",
    "notebook_read",
    "read_file_context",
    "read_file_contexts",
    "tail_file",
    "read_files",
    "read_file_ranges",
}


def parse_read_file_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type == "read_file":
        path = value.get("path")
        if not isinstance(path, str):
            raise ActionParseError("read_file action requires a string path.", raw)
        start_line = parse_optional_positive_int(value.get("start_line"), "start_line", raw, maximum=None)
        line_count = parse_optional_positive_int(value.get("line_count"), "line_count", raw, maximum=1000)
        max_bytes = parse_optional_positive_int(value.get("max_bytes", 20_000), "max_bytes", raw, maximum=200_000) or 20_000
        show_line_numbers = value.get("show_line_numbers", False)
        if not isinstance(show_line_numbers, bool):
            raise ActionParseError("read_file action show_line_numbers must be a boolean when provided.", raw)
        if max_bytes < 1000:
            raise ActionParseError("max_bytes must be at least 1000.", raw)
        if line_count is not None and start_line is None:
            raise ActionParseError("read_file action line_count requires start_line.", raw)
        return ReadFileAction(
            type="read_file",
            path=path,
            start_line=start_line,
            line_count=line_count,
            max_bytes=max_bytes,
            show_line_numbers=show_line_numbers,
        )

    if action_type == "notebook_read":
        path = value.get("path")
        if not isinstance(path, str):
            raise ActionParseError("notebook_read action requires a string path.", raw)
        return NotebookReadAction(
            type="notebook_read",
            path=path,
            start_cell=parse_optional_positive_int(value.get("start_cell"), "start_cell", raw, maximum=10_000) or 1,
            cell_count=parse_optional_positive_int(value.get("cell_count"), "cell_count", raw, maximum=200) or 50,
            include_outputs=truthy_alias_bool(value.get("include_outputs")),
            max_source_chars=parse_optional_positive_int(value.get("max_source_chars"), "max_source_chars", raw, maximum=20_000) or 2_000,
        )

    if action_type == "read_file_context":
        path = value.get("path")
        if not isinstance(path, str):
            raise ActionParseError("read_file_context action requires a string path.", raw)
        line = parse_optional_positive_int(value.get("line"), "line", raw, maximum=None)
        if line is None:
            raise ActionParseError("read_file_context action requires line.", raw)
        context_lines = parse_nonnegative_int(value.get("context_lines", 20), "context_lines", raw, maximum=500)
        max_bytes = parse_optional_positive_int(value.get("max_bytes", 20_000), "max_bytes", raw, maximum=200_000) or 20_000
        if max_bytes < 1000:
            raise ActionParseError("max_bytes must be at least 1000.", raw)
        return ReadFileContextAction(
            type="read_file_context",
            path=path,
            line=line,
            context_lines=context_lines,
            max_bytes=max_bytes,
        )

    if action_type == "read_file_contexts":
        max_bytes_per_context = parse_optional_positive_int(
            value.get("max_bytes_per_context", 20_000),
            "max_bytes_per_context",
            raw,
            maximum=200_000,
        ) or 20_000
        if max_bytes_per_context < 1000:
            raise ActionParseError("max_bytes_per_context must be at least 1000.", raw)
        return ReadFileContextsAction(
            type="read_file_contexts",
            contexts=parse_read_file_contexts(value.get("contexts"), raw),
            max_bytes_per_context=max_bytes_per_context,
        )

    if action_type == "tail_file":
        path = value.get("path")
        if not isinstance(path, str):
            raise ActionParseError("tail_file action requires a string path.", raw)
        line_count = parse_optional_positive_int(value.get("line_count", 80), "line_count", raw, maximum=1000) or 80
        max_bytes = parse_optional_positive_int(value.get("max_bytes", 20_000), "max_bytes", raw, maximum=200_000) or 20_000
        if max_bytes < 1000:
            raise ActionParseError("max_bytes must be at least 1000.", raw)
        return TailFileAction(type="tail_file", path=path, line_count=line_count, max_bytes=max_bytes)

    if action_type == "read_files":
        max_bytes_per_file = parse_optional_positive_int(
            value.get("max_bytes_per_file", 20_000),
            "max_bytes_per_file",
            raw,
            maximum=200_000,
        ) or 20_000
        if max_bytes_per_file < 1000:
            raise ActionParseError("max_bytes_per_file must be at least 1000.", raw)
        show_line_numbers = value.get("show_line_numbers", False)
        if not isinstance(show_line_numbers, bool):
            raise ActionParseError("read_files action show_line_numbers must be a boolean when provided.", raw)
        return ReadFilesAction(
            type="read_files",
            paths=parse_read_file_paths(value.get("paths"), raw),
            max_bytes_per_file=max_bytes_per_file,
            show_line_numbers=show_line_numbers,
        )

    if action_type == "read_file_ranges":
        max_bytes_per_range = parse_optional_positive_int(
            value.get("max_bytes_per_range", 20_000),
            "max_bytes_per_range",
            raw,
            maximum=200_000,
        ) or 20_000
        if max_bytes_per_range < 1000:
            raise ActionParseError("max_bytes_per_range must be at least 1000.", raw)
        return ReadFileRangesAction(
            type="read_file_ranges",
            ranges=parse_read_file_ranges(value.get("ranges"), raw),
            max_bytes_per_range=max_bytes_per_range,
        )

    return None
