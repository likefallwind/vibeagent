from __future__ import annotations

from .types import Observation


def summarize(value: str, max_length: int = 500) -> str:
    compact = " ".join(value.split())
    if len(compact) <= max_length:
        return compact
    return f"{compact[:max_length]}..."

def observation_failed(observation: Observation) -> bool:
    if observation.kind in {"tool_error", "approval_denied"}:
        return True
    if observation.kind == "ask_user":
        return observation.cancelled
    if observation.kind == "delegate_task":
        return not observation.ok
    if observation.kind == "check_write_file":
        return not observation.ok
    if observation.kind == "write_file":
        return not observation.ok
    if observation.kind == "check_write_files":
        return not observation.ok
    if observation.kind == "write_files":
        return not observation.ok
    if observation.kind == "checkpoint_create":
        return not observation.ok
    if observation.kind == "check_edit_file":
        return not observation.ok
    if observation.kind == "edit_file":
        return not observation.ok
    if observation.kind == "check_multi_edit_file":
        return not observation.ok
    if observation.kind == "multi_edit_file":
        return not observation.ok
    if observation.kind == "check_replace_python_definition":
        return not observation.ok
    if observation.kind == "replace_python_definition":
        return not observation.ok
    if observation.kind == "check_replace_lines":
        return not observation.ok
    if observation.kind == "replace_lines":
        return not observation.ok
    if observation.kind == "check_insert_lines":
        return not observation.ok
    if observation.kind == "insert_lines":
        return not observation.ok
    if observation.kind == "check_append_file":
        return not observation.ok
    if observation.kind == "append_file":
        return not observation.ok
    if observation.kind == "regex_replace":
        return not observation.ok
    if observation.kind == "check_regex_replace":
        return not observation.ok
    if observation.kind == "check_json_set":
        return not observation.ok
    if observation.kind == "json_set":
        return not observation.ok
    if observation.kind == "check_json_remove":
        return not observation.ok
    if observation.kind == "json_remove":
        return not observation.ok
    if observation.kind == "check_json_patch":
        return not observation.ok
    if observation.kind == "json_patch":
        return not observation.ok
    if observation.kind == "check_patch":
        return not observation.ok
    if observation.kind == "check_patches":
        return not observation.ok
    if observation.kind == "patch_file":
        return not observation.ok
    if observation.kind == "patch_files":
        return not observation.ok
    if observation.kind == "check_delete_file":
        return not observation.ok
    if observation.kind == "delete_file":
        return not observation.ok
    if observation.kind == "check_delete_files":
        return not observation.ok
    if observation.kind == "delete_files":
        return not observation.ok
    if observation.kind == "check_move_file":
        return not observation.ok
    if observation.kind == "move_file":
        return not observation.ok
    if observation.kind == "check_move_files":
        return not observation.ok
    if observation.kind == "move_files":
        return not observation.ok
    if observation.kind == "check_copy_file":
        return not observation.ok
    if observation.kind == "copy_file":
        return not observation.ok
    if observation.kind == "check_copy_files":
        return not observation.ok
    if observation.kind == "copy_files":
        return not observation.ok
    if observation.kind == "check_move_dir":
        return not observation.ok
    if observation.kind == "move_dir":
        return not observation.ok
    if observation.kind == "check_move_dirs":
        return not observation.ok
    if observation.kind == "move_dirs":
        return not observation.ok
    if observation.kind == "check_copy_dir":
        return not observation.ok
    if observation.kind == "copy_dir":
        return not observation.ok
    if observation.kind == "check_copy_dirs":
        return not observation.ok
    if observation.kind == "copy_dirs":
        return not observation.ok
    if observation.kind == "check_create_dir":
        return not observation.ok
    if observation.kind == "create_dir":
        return not observation.ok
    if observation.kind == "check_create_dirs":
        return not observation.ok
    if observation.kind == "create_dirs":
        return not observation.ok
    if observation.kind == "check_delete_empty_dir":
        return not observation.ok
    if observation.kind == "delete_empty_dir":
        return not observation.ok
    if observation.kind == "check_delete_empty_dirs":
        return not observation.ok
    if observation.kind == "delete_empty_dirs":
        return not observation.ok
    if observation.kind == "check_set_executable":
        return not observation.ok
    if observation.kind == "set_executable":
        return not observation.ok
    if observation.kind == "run_command":
        return observation.result.exit_code != 0 or observation.result.timed_out
    if observation.kind == "run_commands":
        return not observation.ok
    if observation.kind == "run_focused_test_commands":
        return not observation.ok
    if observation.kind == "port_check":
        return not observation.ok
    if observation.kind == "http_check":
        return not observation.ok
    if observation.kind == "http_fetch":
        return not observation.ok
    if observation.kind == "web_fetch":
        return not observation.ok
    if observation.kind in {
        "start_command",
        "read_process",
        "wait_process",
        "check_write_process",
        "write_process",
        "check_stop_all_processes",
        "check_stop_process",
        "stop_all_processes",
        "stop_process",
    }:
        return not observation.ok
    if observation.kind == "list_processes":
        return False
    if observation.kind == "update_plan":
        return False
    if observation.kind == "repo_map":
        return not observation.ok
    if observation.kind == "read_file":
        return not observation.message.startswith("Read ")
    if observation.kind == "read_file_context":
        return not observation.ok
    if observation.kind == "read_file_contexts":
        return any(not item.ok for item in observation.contexts)
    if observation.kind == "output_contexts":
        return any(not item.ok for item in observation.contexts)
    if observation.kind == "output_diagnostics":
        return any(not item.ok for item in observation.contexts)
    if observation.kind == "tail_file":
        return not observation.ok
    if observation.kind == "read_files":
        return any(not item.ok for item in observation.files)
    if observation.kind == "read_file_ranges":
        return any(not item.ok for item in observation.ranges)
    if observation.kind == "file_info":
        return any(not item.ok for item in observation.files)
    if observation.kind == "image_info":
        return any(not item.ok for item in observation.images)
    if observation.kind == "python_symbols":
        return any(not item.ok for item in observation.files)
    if observation.kind == "code_outline":
        return any(not item.ok for item in observation.files)
    if observation.kind == "python_check":
        return not observation.ok
    if observation.kind == "config_check":
        return not observation.ok
    if observation.kind == "python_dependencies":
        return not observation.ok
    if observation.kind == "code_dependencies":
        return not observation.ok
    if observation.kind == "code_references":
        return not observation.ok
    if observation.kind == "code_reference_contexts":
        return not observation.ok
    if observation.kind == "code_definitions":
        return not observation.ok
    if observation.kind == "code_rename_preview":
        return not observation.ok
    if observation.kind == "code_rename":
        return not observation.ok
    if observation.kind == "python_definitions":
        return not observation.ok
    if observation.kind == "python_calls":
        return not observation.ok
    if observation.kind == "python_call_graph":
        return not observation.ok
    if observation.kind == "python_references":
        return not observation.ok
    if observation.kind == "python_reference_contexts":
        return not observation.ok
    if observation.kind == "python_rename_preview":
        return not observation.ok
    if observation.kind == "python_rename":
        return not observation.ok
    if observation.kind == "search":
        return not observation.ok
    if observation.kind == "search_contexts":
        return not observation.ok
    if observation.kind == "find_files":
        return not observation.ok
    if observation.kind == "glob":
        return not observation.ok
    if observation.kind == "list_tree":
        return not observation.ok
    if observation.kind == "list_files":
        return not observation.message.startswith(("Found ", "Already listed "))
    if observation.kind == "git_status":
        return not observation.ok
    if observation.kind == "git_conflicts":
        return not observation.ok
    if observation.kind == "git_diff_contexts":
        return not observation.ok
    if observation.kind == "git_info":
        return not observation.ok
    if observation.kind == "git_changes":
        return not observation.ok
    if observation.kind == "git_branches":
        return not observation.ok
    if observation.kind == "check_git_fetch":
        return not observation.ok
    if observation.kind == "git_fetch":
        return not observation.ok
    if observation.kind == "check_git_pull":
        return not observation.ok
    if observation.kind == "git_pull":
        return not observation.ok
    if observation.kind == "check_git_push":
        return not observation.ok
    if observation.kind == "git_push":
        return not observation.ok
    if observation.kind == "check_git_restore":
        return not observation.ok
    if observation.kind == "git_restore":
        return not observation.ok
    if observation.kind == "git_stashes":
        return not observation.ok
    if observation.kind == "check_git_stash":
        return not observation.ok
    if observation.kind == "git_stash":
        return not observation.ok
    if observation.kind == "check_git_stash_apply":
        return not observation.ok
    if observation.kind == "git_stash_apply":
        return not observation.ok
    if observation.kind == "check_git_stash_drop":
        return not observation.ok
    if observation.kind == "git_stash_drop":
        return not observation.ok
    if observation.kind == "check_git_switch":
        return not observation.ok
    if observation.kind == "git_switch":
        return not observation.ok
    if observation.kind == "check_git_stage":
        return not observation.ok
    if observation.kind == "git_stage":
        return not observation.ok
    if observation.kind == "check_git_unstage":
        return not observation.ok
    if observation.kind == "git_unstage":
        return not observation.ok
    if observation.kind == "check_git_commit":
        return not observation.ok
    if observation.kind == "git_commit":
        return not observation.ok
    if observation.kind == "review_changes":
        return not observation.ok
    if observation.kind == "final_review":
        return not observation.ok
    if observation.kind == "suggest_checks":
        return not observation.ok
    if observation.kind == "check_suggested_checks":
        return not observation.ok
    if observation.kind == "run_suggested_checks":
        return not observation.ok
    if observation.kind == "project_commands":
        return not observation.ok
    if observation.kind == "tool_search":
        return not observation.ok
    if observation.kind == "related_tests":
        return not observation.ok
    if observation.kind == "focused_test_commands":
        return not observation.ok
    if observation.kind == "check_focused_test_commands":
        return not observation.ok
    if observation.kind == "run_focused_test_commands":
        return not observation.ok
    if observation.kind == "project_manifests":
        return not observation.ok
    if observation.kind == "project_instructions":
        return not observation.ok
    if observation.kind == "project_skills":
        return not observation.ok
    if observation.kind == "skill":
        return not observation.ok
    if observation.kind == "project_todos":
        return not observation.ok
    if observation.kind == "project_overview":
        return not observation.ok
    if observation.kind == "command_check":
        return not observation.ok
    if observation.kind == "check_run_commands":
        return not observation.ok
    if observation.kind == "check_start_command":
        return not observation.ok
    if observation.kind == "environment_info":
        return not observation.ok
    if observation.kind == "git_diff":
        return not observation.ok
    if observation.kind == "git_diff_hunks":
        return not observation.ok
    if observation.kind == "git_log":
        return not observation.ok
    if observation.kind == "git_show":
        return not observation.ok
    if observation.kind == "git_blame":
        return not observation.ok
    if observation.kind == "session_summary":
        return not observation.ok
    if observation.kind == "session_plan":
        return not observation.ok
    if observation.kind == "session_transcript":
        return not observation.ok
    if observation.kind == "session_search":
        return not observation.ok
    if observation.kind == "session_commands":
        return not observation.ok
    if observation.kind == "session_output_contexts":
        return not observation.ok
    if observation.kind == "session_output_diagnostics":
        return not observation.ok
    if observation.kind == "process_output_contexts":
        return not observation.ok
    if observation.kind == "process_output_diagnostics":
        return not observation.ok
    if observation.kind == "session_files":
        return not observation.ok
    if observation.kind == "session_failures":
        return not observation.ok
    if observation.kind == "session_verification":
        return not observation.ok
    if observation.kind == "run_session_verification":
        return not observation.ok
    if observation.kind == "session_audit":
        return not observation.ok
    if observation.kind == "session_handoff":
        return not observation.ok
    if observation.kind in {
        "checkpoint_create",
        "checkpoint_list",
        "checkpoint_show",
        "checkpoint_diff",
        "checkpoint_status",
        "check_checkpoint_restore",
        "checkpoint_restore",
        "check_checkpoint_delete",
        "checkpoint_delete",
        "check_checkpoint_prune",
        "checkpoint_prune",
    }:
        return not observation.ok
    return False
