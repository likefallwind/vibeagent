from __future__ import annotations

from typing import Any


INTERACTIVE_EDIT_COMMANDS: dict[str, str] = {
    "config_check": "get_config_check_text",
    "check_json_set": "get_check_json_set_text",
    "json_set": "get_json_set_text",
    "check_json_remove": "get_check_json_remove_text",
    "json_remove": "get_json_remove_text",
    "check_json_patch": "get_check_json_patch_text",
    "json_patch": "get_json_patch_text",
    "check_replace_lines": "get_check_replace_lines_text",
    "replace_lines": "get_replace_lines_text",
    "check_insert_lines": "get_check_insert_lines_text",
    "insert_lines": "get_insert_lines_text",
    "check_append_file": "get_check_append_file_text",
    "append_file": "get_append_file_text",
    "check_write_file": "get_check_write_file_text",
    "write_file": "get_write_file_text",
    "check_write_files": "get_check_write_files_text",
    "write_files": "get_write_files_text",
    "check_edit_file": "get_check_edit_file_text",
    "edit_file": "get_edit_file_text",
    "check_multi_edit_file": "get_check_multi_edit_file_text",
    "multi_edit_file": "get_multi_edit_file_text",
    "check_delete_file": "get_check_delete_file_text",
    "delete_file": "get_delete_file_text",
    "check_delete_files": "get_check_delete_files_text",
    "delete_files": "get_delete_files_text",
    "check_move_file": "get_check_move_file_text",
    "move_file": "get_move_file_text",
    "check_move_files": "get_check_move_files_text",
    "move_files": "get_move_files_text",
    "check_copy_file": "get_check_copy_file_text",
    "copy_file": "get_copy_file_text",
    "check_copy_files": "get_check_copy_files_text",
    "copy_files": "get_copy_files_text",
    "check_move_dir": "get_check_move_dir_text",
    "move_dir": "get_move_dir_text",
    "check_move_dirs": "get_check_move_dirs_text",
    "move_dirs": "get_move_dirs_text",
    "check_copy_dir": "get_check_copy_dir_text",
    "copy_dir": "get_copy_dir_text",
    "check_copy_dirs": "get_check_copy_dirs_text",
    "copy_dirs": "get_copy_dirs_text",
    "check_create_dir": "get_check_create_dir_text",
    "create_dir": "get_create_dir_text",
    "check_create_dirs": "get_check_create_dirs_text",
    "create_dirs": "get_create_dirs_text",
    "check_delete_empty_dir": "get_check_delete_empty_dir_text",
    "delete_empty_dir": "get_delete_empty_dir_text",
    "check_delete_empty_dirs": "get_check_delete_empty_dirs_text",
    "delete_empty_dirs": "get_delete_empty_dirs_text",
    "check_set_executable": "get_check_set_executable_text",
    "set_executable": "get_set_executable_text",
    "check_patch": "get_check_patch_text",
    "patch_file": "get_patch_text",
    "check_patches": "get_check_patches_text",
    "patch_files": "get_patches_text",
    "check_regex_replace": "get_check_regex_replace_text",
    "regex_replace": "get_regex_replace_text",
}


def run_interactive_edit_command(command: Any, commands: dict[str, Any]) -> str | None:
    getter_name = INTERACTIVE_EDIT_COMMANDS.get(command.type)
    if getter_name is None:
        return None
    return commands[getter_name](argument=command.argument)
