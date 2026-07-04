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
    "git_pull",
    "git_stash",
    "git_stash_apply",
    "git_stash_drop",
    "git_switch",
    "checkpoint_restore",
}


VCS_METADATA_OBSERVATION_KINDS = {
    "git_stage",
    "git_unstage",
    "git_commit",
    "git_stash_drop",
}


VERIFICATION_INVALIDATING_OBSERVATION_KINDS = PROJECT_CHANGE_OBSERVATION_KINDS - VCS_METADATA_OBSERVATION_KINDS


AUTO_FINAL_REVIEW_EXCLUDED_OBSERVATION_KINDS = {
    "git_stash_drop",
}


AUTO_FINAL_REVIEW_OBSERVATION_KINDS = PROJECT_CHANGE_OBSERVATION_KINDS - AUTO_FINAL_REVIEW_EXCLUDED_OBSERVATION_KINDS


FINITE_COMMAND_OBSERVATION_KINDS = {
    "run_command",
    "run_commands",
    "run_suggested_checks",
    "run_focused_test_commands",
    "run_session_verification",
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
