from __future__ import annotations

from typing import Any

from .action_parsing_file_edit_fields import parse_string_field, parse_transfer
from .action_parsing_helpers import ActionParseError, parse_move_file_transfers, parse_path_list
from .types import (
    CheckCopyFileAction,
    CheckCopyFilesAction,
    CheckDeleteFileAction,
    CheckDeleteFilesAction,
    CheckMoveFileAction,
    CheckMoveFilesAction,
    CheckSetExecutableAction,
    CopyFileAction,
    CopyFilesAction,
    DeleteFileAction,
    DeleteFilesAction,
    MoveFileAction,
    MoveFilesAction,
    SetExecutableAction,
)


FILE_PATH_ACTION_TYPES = {
    "check_delete_file",
    "delete_file",
    "check_delete_files",
    "delete_files",
    "check_move_file",
    "move_file",
    "check_move_files",
    "move_files",
    "check_copy_file",
    "copy_file",
    "check_copy_files",
    "copy_files",
    "check_set_executable",
    "set_executable",
}


def parse_file_path_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in FILE_PATH_ACTION_TYPES:
        return None

    if action_type == "check_delete_file":
        path = parse_string_field(value.get("path"), raw, "check_delete_file action requires a string path.")
        return CheckDeleteFileAction(type="check_delete_file", path=path)

    if action_type == "delete_file":
        path = parse_string_field(value.get("path"), raw, "delete_file action requires a string path.")
        return DeleteFileAction(type="delete_file", path=path)

    if action_type == "check_delete_files":
        return CheckDeleteFilesAction(
            type="check_delete_files",
            paths=parse_path_list(value.get("paths"), raw, "check_delete_files", maximum=100),
        )

    if action_type == "delete_files":
        return DeleteFilesAction(
            type="delete_files",
            paths=parse_path_list(value.get("paths"), raw, "delete_files", maximum=100),
        )

    if action_type == "check_move_file":
        source, destination = parse_transfer(value, raw, "check_move_file")
        return CheckMoveFileAction(type="check_move_file", source=source, destination=destination)

    if action_type == "move_file":
        source, destination = parse_transfer(value, raw, "move_file")
        return MoveFileAction(type="move_file", source=source, destination=destination)

    if action_type == "check_move_files":
        return CheckMoveFilesAction(
            type="check_move_files",
            transfers=parse_move_file_transfers(value.get("transfers"), raw, "check_move_files"),
        )

    if action_type == "move_files":
        return MoveFilesAction(
            type="move_files",
            transfers=parse_move_file_transfers(value.get("transfers"), raw, "move_files"),
        )

    if action_type == "check_copy_file":
        source, destination = parse_transfer(value, raw, "check_copy_file")
        return CheckCopyFileAction(type="check_copy_file", source=source, destination=destination)

    if action_type == "copy_file":
        source, destination = parse_transfer(value, raw, "copy_file")
        return CopyFileAction(type="copy_file", source=source, destination=destination)

    if action_type == "check_copy_files":
        return CheckCopyFilesAction(
            type="check_copy_files",
            transfers=parse_move_file_transfers(value.get("transfers"), raw, "check_copy_files"),
        )

    if action_type == "copy_files":
        return CopyFilesAction(
            type="copy_files",
            transfers=parse_move_file_transfers(value.get("transfers"), raw, "copy_files"),
        )

    if action_type == "check_set_executable":
        path = parse_string_field(value.get("path"), raw, "check_set_executable action requires a string path.")
        executable = value.get("executable", True)
        if not isinstance(executable, bool):
            raise ActionParseError("check_set_executable action executable must be a boolean.", raw)
        return CheckSetExecutableAction(type="check_set_executable", path=path, executable=executable)

    if action_type == "set_executable":
        path = parse_string_field(value.get("path"), raw, "set_executable action requires a string path.")
        executable = value.get("executable", True)
        if not isinstance(executable, bool):
            raise ActionParseError("set_executable action executable must be a boolean.", raw)
        return SetExecutableAction(type="set_executable", path=path, executable=executable)

    raise AssertionError(f"Unhandled file path action type: {action_type!r}")
