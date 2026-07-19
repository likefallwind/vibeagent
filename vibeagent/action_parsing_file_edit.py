from __future__ import annotations

from typing import Any

from .action_parsing_file_directories import parse_file_directory_action
from .action_parsing_file_exact import parse_file_exact_action
from .action_parsing_file_line import parse_file_line_action
from .action_parsing_file_notebook import parse_file_notebook_action
from .action_parsing_file_patch import parse_file_patch_action
from .action_parsing_file_paths import parse_file_path_action
from .action_parsing_file_write import parse_file_write_action


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

    path_action = parse_file_path_action(action_type, value, raw)
    if path_action is not None:
        return path_action

    directory_action = parse_file_directory_action(action_type, value, raw)
    if directory_action is not None:
        return directory_action

    notebook_action = parse_file_notebook_action(action_type, value, raw)
    if notebook_action is not None:
        return notebook_action

    raise AssertionError(f"Unhandled file edit action type: {action_type!r}")
