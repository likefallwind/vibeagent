from __future__ import annotations

from typing import Any

from .action_parsing_file_edit_fields import parse_string_field, parse_transfer
from .action_parsing_helpers import parse_directory_transfers, parse_path_list
from .types import (
    CheckCopyDirectoryAction,
    CheckCopyDirectoriesAction,
    CheckCreateDirectoryAction,
    CheckCreateDirectoriesAction,
    CheckDeleteEmptyDirectoryAction,
    CheckDeleteEmptyDirectoriesAction,
    CheckMoveDirectoryAction,
    CheckMoveDirectoriesAction,
    CopyDirectoryAction,
    CopyDirectoriesAction,
    CreateDirectoryAction,
    CreateDirectoriesAction,
    DeleteEmptyDirectoryAction,
    DeleteEmptyDirectoriesAction,
    MoveDirectoryAction,
    MoveDirectoriesAction,
)


FILE_DIRECTORY_ACTION_TYPES = {
    "check_move_dir",
    "move_dir",
    "check_move_dirs",
    "move_dirs",
    "check_copy_dir",
    "copy_dir",
    "check_copy_dirs",
    "copy_dirs",
    "check_create_dir",
    "create_dir",
    "check_create_dirs",
    "create_dirs",
    "check_delete_empty_dir",
    "delete_empty_dir",
    "check_delete_empty_dirs",
    "delete_empty_dirs",
}


def parse_file_directory_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in FILE_DIRECTORY_ACTION_TYPES:
        return None

    if action_type == "check_move_dir":
        source, destination = parse_transfer(value, raw, "check_move_dir")
        return CheckMoveDirectoryAction(type="check_move_dir", source=source, destination=destination)

    if action_type == "move_dir":
        source, destination = parse_transfer(value, raw, "move_dir")
        return MoveDirectoryAction(type="move_dir", source=source, destination=destination)

    if action_type == "check_move_dirs":
        return CheckMoveDirectoriesAction(
            type="check_move_dirs",
            transfers=parse_directory_transfers(value.get("transfers"), raw, "check_move_dirs"),
        )

    if action_type == "move_dirs":
        return MoveDirectoriesAction(
            type="move_dirs",
            transfers=parse_directory_transfers(value.get("transfers"), raw, "move_dirs"),
        )

    if action_type == "check_copy_dir":
        source, destination = parse_transfer(value, raw, "check_copy_dir")
        return CheckCopyDirectoryAction(type="check_copy_dir", source=source, destination=destination)

    if action_type == "copy_dir":
        source, destination = parse_transfer(value, raw, "copy_dir")
        return CopyDirectoryAction(type="copy_dir", source=source, destination=destination)

    if action_type == "check_copy_dirs":
        return CheckCopyDirectoriesAction(
            type="check_copy_dirs",
            transfers=parse_directory_transfers(value.get("transfers"), raw, "check_copy_dirs"),
        )

    if action_type == "copy_dirs":
        return CopyDirectoriesAction(
            type="copy_dirs",
            transfers=parse_directory_transfers(value.get("transfers"), raw, "copy_dirs"),
        )

    if action_type == "check_create_dir":
        path = parse_string_field(value.get("path"), raw, "check_create_dir action requires a string path.")
        return CheckCreateDirectoryAction(type="check_create_dir", path=path)

    if action_type == "create_dir":
        path = parse_string_field(value.get("path"), raw, "create_dir action requires a string path.")
        return CreateDirectoryAction(type="create_dir", path=path)

    if action_type == "check_create_dirs":
        return CheckCreateDirectoriesAction(
            type="check_create_dirs",
            paths=parse_path_list(value.get("paths"), raw, "check_create_dirs", maximum=100),
        )

    if action_type == "create_dirs":
        return CreateDirectoriesAction(
            type="create_dirs",
            paths=parse_path_list(value.get("paths"), raw, "create_dirs", maximum=100),
        )

    if action_type == "check_delete_empty_dir":
        path = parse_string_field(value.get("path"), raw, "check_delete_empty_dir action requires a string path.")
        return CheckDeleteEmptyDirectoryAction(type="check_delete_empty_dir", path=path)

    if action_type == "delete_empty_dir":
        path = parse_string_field(value.get("path"), raw, "delete_empty_dir action requires a string path.")
        return DeleteEmptyDirectoryAction(type="delete_empty_dir", path=path)

    if action_type == "check_delete_empty_dirs":
        return CheckDeleteEmptyDirectoriesAction(
            type="check_delete_empty_dirs",
            paths=parse_path_list(value.get("paths"), raw, "check_delete_empty_dirs", maximum=100),
        )

    if action_type == "delete_empty_dirs":
        return DeleteEmptyDirectoriesAction(
            type="delete_empty_dirs",
            paths=parse_path_list(value.get("paths"), raw, "delete_empty_dirs", maximum=100),
        )

    raise AssertionError(f"Unhandled file directory action type: {action_type!r}")
