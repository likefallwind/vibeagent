from __future__ import annotations


PROJECT_CHANGE_OBSERVATION_KINDS = {
    "write_file",
    "write_files",
    "edit_file",
    "multi_edit_file",
    "replace_python_definition",
    "code_rename",
    "python_rename",
    "replace_lines",
    "insert_lines",
    "append_file",
    "regex_replace",
    "json_set",
    "json_remove",
    "json_patch",
    "patch_file",
    "patch_files",
    "delete_file",
    "delete_files",
    "move_file",
    "move_files",
    "copy_file",
    "copy_files",
    "move_dir",
    "move_dirs",
    "copy_dir",
    "copy_dirs",
    "create_dir",
    "create_dirs",
    "delete_empty_dir",
    "delete_empty_dirs",
    "set_executable",
    "git_stage",
    "git_unstage",
    "git_commit",
    "git_restore",
    "checkpoint_restore",
}


FINITE_COMMAND_OBSERVATION_KINDS = {
    "run_command",
    "run_commands",
    "run_suggested_checks",
    "run_focused_test_commands",
}


MULTISTEP_CODING_FOLLOWUP_KINDS = {
    *FINITE_COMMAND_OBSERVATION_KINDS,
    "python_check",
    "config_check",
    "command_check",
    "check_run_commands",
    "check_suggested_checks",
    "check_focused_test_commands",
}
