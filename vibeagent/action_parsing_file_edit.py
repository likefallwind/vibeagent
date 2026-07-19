from __future__ import annotations

from typing import Any

from .action_parsing_helpers import (
    ActionParseError,
    parse_directory_transfers,
    parse_move_file_transfers,
    parse_optional_positive_int,
    parse_path_list,
)
from .action_parsing_file_exact import parse_file_exact_action
from .action_parsing_file_edit_fields import (
    parse_string_field,
    parse_transfer,
)
from .action_parsing_file_line import parse_file_line_action
from .action_parsing_file_patch import parse_file_patch_action
from .action_parsing_file_write import parse_file_write_action
from .types import (
    CheckCopyFileAction,
    CheckCopyFilesAction,
    CheckCopyDirectoryAction,
    CheckCopyDirectoriesAction,
    CheckCreateDirectoryAction,
    CheckCreateDirectoriesAction,
    CheckDeleteFileAction,
    CheckDeleteFilesAction,
    CheckDeleteEmptyDirectoryAction,
    CheckDeleteEmptyDirectoriesAction,
    CheckMoveFileAction,
    CheckMoveFilesAction,
    CheckMoveDirectoryAction,
    CheckMoveDirectoriesAction,
    CheckNotebookEditAction,
    CheckSetExecutableAction,
    CopyFileAction,
    CopyFilesAction,
    CopyDirectoryAction,
    CopyDirectoriesAction,
    CreateDirectoryAction,
    CreateDirectoriesAction,
    DeleteFileAction,
    DeleteFilesAction,
    DeleteEmptyDirectoryAction,
    DeleteEmptyDirectoriesAction,
    MoveFileAction,
    MoveFilesAction,
    MoveDirectoryAction,
    MoveDirectoriesAction,
    NotebookEditAction,
    SetExecutableAction,
)


FILE_EDIT_ACTION_TYPES = {
    "check_edit_file",
    "edit_file",
    "check_notebook_edit",
    "notebook_edit",
    "check_multi_edit_file",
    "multi_edit_file",
    "check_replace_lines",
    "replace_lines",
    "check_insert_lines",
    "insert_lines",
    "check_append_file",
    "append_file",
    "check_regex_replace",
    "regex_replace",
    "check_patch",
    "check_patches",
    "patch_file",
    "patch_files",
    "check_write_file",
    "write_file",
    "check_write_files",
    "write_files",
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
    "check_set_executable",
    "set_executable",
}


def parse_file_edit_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in FILE_EDIT_ACTION_TYPES:
        return None

    write_action = parse_file_write_action(action_type, value, raw)
    if write_action is not None:
        return write_action

    exact_action = parse_file_exact_action(action_type, value, raw)
    if exact_action is not None:
        return exact_action

    line_action = parse_file_line_action(action_type, value, raw)
    if line_action is not None:
        return line_action

    patch_action = parse_file_patch_action(action_type, value, raw)
    if patch_action is not None:
        return patch_action

    if action_type in {"check_notebook_edit", "notebook_edit"}:
        path = parse_string_field(value.get("path"), raw, f"{action_type} action requires a string path.")
        new_source = parse_string_field(value.get("new_source"), raw, f"{action_type} action requires string new_source.")
        cell_id = value.get("cell_id")
        cell_number = value.get("cell_number")
        cell_type = value.get("cell_type")
        if cell_id is not None and not isinstance(cell_id, str):
            raise ActionParseError(f"{action_type} action cell_id must be a string when provided.", raw)
        parsed_cell_number = parse_optional_positive_int(cell_number, "cell_number", raw, maximum=1_000_000)
        if cell_id is None and parsed_cell_number is None:
            raise ActionParseError(f"{action_type} action requires cell_id or cell_number.", raw)
        if cell_type is not None and not isinstance(cell_type, str):
            raise ActionParseError(f"{action_type} action cell_type must be a string when provided.", raw)
        action_cls = CheckNotebookEditAction if action_type == "check_notebook_edit" else NotebookEditAction
        return action_cls(
            type=action_type,
            path=path,
            new_source=new_source,
            cell_id=cell_id,
            cell_number=parsed_cell_number,
            cell_type=cell_type,
        )

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

    raise AssertionError(f"Unhandled file edit action type: {action_type!r}")
