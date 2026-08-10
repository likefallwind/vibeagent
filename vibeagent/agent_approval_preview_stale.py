from __future__ import annotations


GIT_PREVIEW_KINDS = {
    "check_git_fetch",
    "check_git_pull",
    "check_git_push",
    "check_git_restore",
    "check_git_switch",
    "check_git_stage",
    "check_git_unstage",
    "check_git_stash",
    "check_git_stash_apply",
    "check_git_stash_drop",
    "check_git_commit",
}

GIT_MUTATION_OBSERVATION_KINDS = {
    "git_fetch",
    "git_pull",
    "git_push",
    "git_restore",
    "git_switch",
    "git_stage",
    "git_unstage",
    "git_stash",
    "git_stash_apply",
    "git_stash_drop",
    "git_commit",
}

CHECKPOINT_RESTORE_PREVIEW_KINDS = {
    "check_checkpoint_restore",
}

CHECKPOINT_RESTORE_MUTATION_OBSERVATION_KINDS = {
    "checkpoint_restore",
}

COMMAND_PREVIEW_KINDS = {
    "command_check",
    "check_run_commands",
    "check_suggested_checks",
    "check_focused_test_commands",
    "session_verification",
    "check_start_command",
}

COMMAND_MUTATION_OBSERVATION_KINDS = {
    "run_command",
    "run_commands",
    "run_focused_test_commands",
    "run_session_verification",
    "run_suggested_checks",
    "start_command",
    "write_process",
}

PROCESS_PREVIEW_KINDS = {
    "check_write_process",
    "check_stop_process",
    "check_stop_all_processes",
}

PROCESS_STATE_OBSERVATION_KINDS = {
    "start_command",
    "read_process",
    "process_output_contexts",
    "process_output_diagnostics",
    "wait_process",
    "write_process",
    "list_processes",
    "stop_process",
    "stop_all_processes",
}

FILE_PREVIEW_KINDS = {
    "check_memory_write",
    "check_write_file",
    "check_write_files",
    "check_edit_file",
    "check_notebook_edit",
    "check_multi_edit_file",
    "check_replace_python_definition",
    "check_replace_lines",
    "check_insert_lines",
    "check_append_file",
    "check_regex_replace",
    "check_json_set",
    "check_json_remove",
    "check_json_patch",
    "check_patch",
    "check_patches",
    "code_rename_preview",
    "python_rename_preview",
    "check_delete_file",
    "check_delete_files",
    "check_move_file",
    "check_move_files",
    "check_copy_file",
    "check_copy_files",
    "check_move_dir",
    "check_move_dirs",
    "check_copy_dir",
    "check_copy_dirs",
    "check_create_dir",
    "check_create_dirs",
    "check_delete_empty_dir",
    "check_delete_empty_dirs",
    "check_set_executable",
}

FILE_MUTATION_OBSERVATION_KINDS = {
    "memory_write",
    "write_file",
    "write_files",
    "edit_file",
    "notebook_edit",
    "multi_edit_file",
    "replace_python_definition",
    "replace_lines",
    "insert_lines",
    "append_file",
    "regex_replace",
    "json_set",
    "json_remove",
    "json_patch",
    "patch_file",
    "patch_files",
    "code_rename",
    "python_rename",
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
}

WORKSPACE_PREVIEW_KINDS = FILE_PREVIEW_KINDS | GIT_PREVIEW_KINDS | CHECKPOINT_RESTORE_PREVIEW_KINDS
WORKSPACE_MUTATION_OBSERVATION_KINDS = (
    FILE_MUTATION_OBSERVATION_KINDS
    | GIT_MUTATION_OBSERVATION_KINDS
    | CHECKPOINT_RESTORE_MUTATION_OBSERVATION_KINDS
    | COMMAND_MUTATION_OBSERVATION_KINDS
)


def preview_invalidated_by_workspace_restore(expected_kind: str, observation_kind: object) -> bool:
    return (
        expected_kind in WORKSPACE_PREVIEW_KINDS
        and observation_kind in CHECKPOINT_RESTORE_MUTATION_OBSERVATION_KINDS
    )


def checkpoint_restore_preview_invalidated_by_workspace_mutation(
    expected_kind: str,
    observation_kind: object,
) -> bool:
    return (
        expected_kind in CHECKPOINT_RESTORE_PREVIEW_KINDS
        and observation_kind in WORKSPACE_MUTATION_OBSERVATION_KINDS
    )


def command_preview_invalidated_by_workspace_mutation(expected_kind: str, observation_kind: object) -> bool:
    return expected_kind in COMMAND_PREVIEW_KINDS and observation_kind in WORKSPACE_MUTATION_OBSERVATION_KINDS


def process_preview_invalidated_by_process_state(expected_kind: str, observation_kind: object) -> bool:
    return expected_kind in PROCESS_PREVIEW_KINDS and observation_kind in PROCESS_STATE_OBSERVATION_KINDS


def git_preview_invalidated_by_workspace_mutation(expected_kind: str, observation_kind: object) -> bool:
    if expected_kind not in GIT_PREVIEW_KINDS:
        return False
    return (
        observation_kind in GIT_MUTATION_OBSERVATION_KINDS
        or observation_kind in FILE_MUTATION_OBSERVATION_KINDS
        or observation_kind in COMMAND_MUTATION_OBSERVATION_KINDS
    )


def file_preview_invalidated_by_broad_workspace_mutation(expected_kind: str, observation_kind: object) -> bool:
    if expected_kind not in FILE_PREVIEW_KINDS:
        return False
    return observation_kind in GIT_MUTATION_OBSERVATION_KINDS or observation_kind in COMMAND_MUTATION_OBSERVATION_KINDS
