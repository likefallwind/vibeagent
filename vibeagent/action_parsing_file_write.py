from __future__ import annotations

from typing import Any

from .action_parsing_file_edit_fields import parse_string_field
from .action_parsing_helpers import parse_write_file_items
from .types import CheckWriteFileAction, CheckWriteFilesAction, WriteFileAction, WriteFilesAction


FILE_WRITE_ACTION_TYPES = {
    "check_write_file",
    "write_file",
    "check_write_files",
    "write_files",
}


def parse_file_write_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in FILE_WRITE_ACTION_TYPES:
        return None

    if action_type == "check_write_file":
        path = parse_string_field(value.get("path"), raw, "check_write_file action requires a string path.")
        content = parse_string_field(value.get("content"), raw, "check_write_file action requires string content.")
        return CheckWriteFileAction(type="check_write_file", path=path, content=content)

    if action_type == "write_file":
        path = parse_string_field(value.get("path"), raw, "write_file action requires a string path.")
        content = parse_string_field(value.get("content"), raw, "write_file action requires string content.")
        return WriteFileAction(type="write_file", path=path, content=content)

    if action_type == "check_write_files":
        return CheckWriteFilesAction(
            type="check_write_files",
            files=parse_write_file_items(value.get("files"), raw, action_type="check_write_files"),
        )

    if action_type == "write_files":
        return WriteFilesAction(type="write_files", files=parse_write_file_items(value.get("files"), raw))

    raise AssertionError(f"Unhandled file write action type: {action_type!r}")
