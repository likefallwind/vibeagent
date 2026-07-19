from __future__ import annotations

from typing import Any

from .action_parsing_file_edit_fields import parse_insert, parse_line_range, parse_string_field
from .action_parsing_helpers import ActionParseError
from .types import (
    AppendFileAction,
    CheckAppendFileAction,
    CheckInsertLinesAction,
    CheckReplaceLinesAction,
    InsertLinesAction,
    ReplaceLinesAction,
)


FILE_LINE_ACTION_TYPES = {
    "check_replace_lines",
    "replace_lines",
    "check_insert_lines",
    "insert_lines",
    "check_append_file",
    "append_file",
}


def parse_file_line_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in FILE_LINE_ACTION_TYPES:
        return None

    if action_type == "check_replace_lines":
        path, start_line, end_line, content = parse_line_range(value, raw, "check_replace_lines")
        return CheckReplaceLinesAction(
            type="check_replace_lines",
            path=path,
            start_line=start_line,
            end_line=end_line,
            content=content,
        )

    if action_type == "replace_lines":
        path, start_line, end_line, content = parse_line_range(value, raw, "replace_lines")
        return ReplaceLinesAction(
            type="replace_lines",
            path=path,
            start_line=start_line,
            end_line=end_line,
            content=content,
        )

    if action_type == "check_insert_lines":
        path, line, content = parse_insert(value, raw, "check_insert_lines")
        return CheckInsertLinesAction(type="check_insert_lines", path=path, line=line, content=content)

    if action_type == "insert_lines":
        path, line, content = parse_insert(value, raw, "insert_lines")
        return InsertLinesAction(type="insert_lines", path=path, line=line, content=content)

    if action_type == "check_append_file":
        path = parse_string_field(value.get("path"), raw, "check_append_file action requires a string path.")
        content = value.get("content")
        if not isinstance(content, str) or content == "":
            raise ActionParseError("check_append_file action requires non-empty string content.", raw)
        return CheckAppendFileAction(type="check_append_file", path=path, content=content)

    if action_type == "append_file":
        path = parse_string_field(value.get("path"), raw, "append_file action requires a string path.")
        content = value.get("content")
        if not isinstance(content, str) or content == "":
            raise ActionParseError("append_file action requires non-empty string content.", raw)
        return AppendFileAction(type="append_file", path=path, content=content)

    raise AssertionError(f"Unhandled file line action type: {action_type!r}")
