from __future__ import annotations

import argparse
from collections.abc import Sequence
import os
from pathlib import Path
import shlex

from .agent import run_agent
from .chat import run_chat
from .cli_exit_codes import (
    LOCAL_RESULT_ARG_NAMES,
    has_bad_session_summary_status,
    has_incomplete_top_level_count,
    has_local_diagnostic_error,
    has_positive_top_level_count,
    has_process_status_failure,
    has_session_verification_issue,
    has_top_level_error,
    has_top_level_field,
    has_top_level_ok,
    local_result_arg_selected,
    process_status_value_failed,
)
from .cli_args import has_local_flag, parse_args
from .cli_config import (
    build_provider_env,
    format_save_config_report_text,
    resolve_project_root,
    save_project_config_from_args,
    save_project_config_report_from_args,
)
from .cli_output import (
    build_approval_handler,
    format_error,
    handle_approval_command,
    print_agent_result,
    print_error_result,
    print_interrupted_result,
    prompt_approval,
)
from .cli_checkpoint_local_flags import run_checkpoint_local_flag, run_interactive_checkpoint_command
from .cli_code_intel_local_flags import (
    run_code_intel_local_flag,
    run_interactive_code_intel_command,
    run_python_local_flag,
)
from .cli_command_local_flags import run_command_local_flag, run_interactive_command_execution
from .cli_edit_local_flags import run_interactive_edit_command
from .cli_local_result import emit_local_result
from .cli_git_local_flags import run_git_local_flag, run_interactive_git_command
from .cli_session_local_flags import run_interactive_resume_command, run_interactive_session_command, run_session_local_flag
from .cli_main_args import normalize_task_bound_diff_args
from .cli_runner import (
    build_one_shot_kwargs_from_args,
    build_context_limit_kwargs,
    is_resume_clear_arg,
    normalize_resume_arg,
    resolve_task_text,
    run_one_shot as _run_one_shot,
)
from .cli_review_local_flags import run_interactive_review_command, run_review_local_flag
from .cli_read_local_flags import run_interactive_read_command, run_read_local_flag
from .cli_project_local_flags import run_interactive_project_command, run_interactive_project_state_command, run_project_local_flag
from .cli_session_kwargs import (
    session_audit_kwargs,
    session_commands_kwargs,
    session_failures_kwargs,
    session_files_kwargs,
    session_handoff_kwargs,
    session_output_contexts_kwargs,
    session_output_diagnostics_kwargs,
    session_search_kwargs,
    session_transcript_kwargs,
    session_verification_kwargs,
)
from .cli_runtime_local_flags import run_interactive_runtime_command, run_runtime_local_flag
from .cli_validation import validate_cli_args
from .cli_parsing import (
    build_focused_tests_kwargs,
    build_stash_argument,
    build_switch_argument,
    parse_cli_json_value,
    parse_executable_flag_values,
    parse_interactive_around_argument,
    parse_interactive_around_many_argument,
    parse_interactive_check_run_sequence_argument,
    parse_interactive_commands_argument,
    parse_interactive_cwd_command_argument,
    parse_interactive_diff_argument,
    parse_interactive_diff_contexts_argument,
    parse_interactive_diff_hunks_argument,
    parse_interactive_find_files_argument,
    parse_interactive_glob_argument,
    parse_interactive_http_argument,
    parse_interactive_http_fetch_argument,
    parse_interactive_instructions_argument,
    parse_interactive_manifests_argument,
    parse_interactive_max_bytes_argument,
    parse_interactive_option_limit_argument,
    parse_interactive_output_analysis_argument,
    parse_interactive_overview_argument,
    parse_interactive_port_argument,
    parse_interactive_process_output_argument,
    parse_interactive_python_symbol_argument,
    parse_interactive_read_argument,
    parse_interactive_read_files_argument,
    parse_interactive_read_ranges_argument,
    parse_interactive_repo_map_argument,
    parse_interactive_run_argument,
    parse_interactive_run_focused_tests_argument,
    parse_interactive_run_sequence_argument,
    parse_interactive_run_suggested_checks_argument,
    parse_interactive_search_argument,
    parse_interactive_session_detail_argument,
    parse_interactive_session_search_argument,
    parse_interactive_symbols_argument,
    parse_interactive_tail_argument,
    parse_interactive_test_paths_argument,
    parse_interactive_todos_argument,
    parse_interactive_transcript_argument,
    parse_interactive_tree_argument,
    parse_interactive_wait_process_argument,
    parse_multi_edit_flag_values,
)
from .commands import (
    get_append_file_report,
    get_append_file_text,
    get_help_text,
    format_blame_report_text,
    format_branches_report_text,
    format_git_commit_report_text,
    format_git_fetch_report_text,
    format_git_info_report_text,
    format_git_pull_report_text,
    format_git_push_report_text,
    format_git_restore_report_text,
    format_git_stash_apply_report_text,
    format_git_stash_drop_report_text,
    format_git_stash_report_text,
    format_git_status_report_text,
    format_git_switch_report_text,
    format_git_sync_preview_report_text,
    format_find_files_report_text,
    format_glob_report_text,
    format_file_info_report_text,
    format_image_info_report_text,
    format_json_patch_report_text,
    format_json_pointer_report_text,
    format_log_report_text,
    format_around_report_text,
    format_around_many_report_text,
    format_output_contexts_report_text,
    format_output_diagnostics_report_text,
    format_process_report_text,
    format_process_output_contexts_report_text,
    format_process_output_diagnostics_report_text,
    format_python_traceback_report_text,
    format_regex_replace_report_text,
    format_executable_report_text,
    format_permissions_report_text,
    format_patch_report_text,
    format_patches_report_text,
    format_path_action_report_text,
    format_path_list_report_text,
    format_file_transfer_list_report_text,
    format_file_transfer_report_text,
    format_read_report_text,
    format_read_files_report_text,
    format_read_ranges_report_text,
    format_show_report_text,
    format_stashes_report_text,
    format_symbols_report_text,
    format_tree_report_text,
    format_session_transcript_report_text,
    get_blame_report,
    get_blame_text,
    get_branches_report,
    get_branches_text,
    get_compact_context,
    get_checks_report,
    get_checks_text,
    format_changes_report_text,
    get_changes_report,
    get_changes_text,
    format_check_checkpoint_delete_report_text,
    format_check_checkpoint_prune_report_text,
    format_checkpoint_create_report_text,
    format_checkpoint_delete_report_text,
    format_checkpoint_diff_report_text,
    format_checkpoint_prune_report_text,
    format_check_checkpoint_restore_report_text,
    format_checkpoint_restore_report_text,
    format_checkpoint_show_report_text,
    format_checkpoint_status_report_text,
    format_checkpoints_report_text,
    get_check_checkpoint_delete_text,
    get_check_checkpoint_delete_report,
    get_check_checkpoint_prune_text,
    get_check_checkpoint_prune_report,
    get_check_checkpoint_restore_text,
    get_check_checkpoint_restore_report,
    get_checkpoint_diff_report,
    get_checkpoint_diff_text,
    get_checkpoint_delete_report,
    get_checkpoint_delete_text,
    get_checkpoint_prune_report,
    get_checkpoint_prune_text,
    get_checkpoint_restore_report,
    get_checkpoint_restore_text,
    get_checkpoint_report,
    get_checkpoint_show_report,
    get_checkpoint_show_text,
    get_checkpoint_status_report,
    get_checkpoint_status_text,
    get_checkpoint_text,
    get_checkpoints_report,
    get_checkpoints_text,
    get_check_copy_dir_text,
    get_check_copy_dir_report,
    get_check_copy_dirs_text,
    get_check_copy_dirs_report,
    get_check_copy_file_report,
    get_check_copy_file_text,
    get_check_copy_files_report,
    get_check_copy_files_text,
    get_check_create_dirs_text,
    get_check_create_dirs_report,
    get_check_create_dir_text,
    get_check_create_dir_report,
    get_check_delete_file_report,
    get_check_delete_file_text,
    get_check_delete_files_report,
    get_check_delete_files_text,
    get_check_delete_empty_dirs_text,
    get_check_delete_empty_dirs_report,
    get_check_delete_empty_dir_text,
    get_check_delete_empty_dir_report,
    get_check_edit_file_report,
    get_check_edit_file_text,
    get_check_fetch_report,
    get_check_fetch_text,
    get_check_pull_report,
    get_check_pull_text,
    get_check_push_report,
    get_check_push_text,
    get_check_set_executable_text,
    get_check_set_executable_report,
    get_check_stash_report,
    get_check_stash_text,
    get_check_stash_apply_report,
    get_check_stash_apply_text,
    get_check_stash_drop_report,
    get_check_stash_drop_text,
    get_check_switch_report,
    get_check_switch_text,
    get_check_append_file_report,
    get_check_append_file_text,
    get_check_insert_lines_report,
    get_check_insert_lines_text,
    get_check_move_dir_text,
    get_check_move_dir_report,
    get_check_move_dirs_text,
    get_check_move_dirs_report,
    get_check_move_file_report,
    get_check_move_file_text,
    get_check_move_files_report,
    get_check_move_files_text,
    get_check_multi_edit_file_report,
    get_check_multi_edit_file_text,
    get_check_patch_text,
    get_check_patch_report,
    get_check_patches_text,
    get_check_patches_report,
    get_check_write_file_report,
    get_check_write_file_text,
    get_check_write_files_report,
    get_check_write_files_text,
    format_write_files_report_text,
    format_check_run_sequence_report_text,
    get_check_run_sequence_report,
    get_check_run_sequence_text,
    format_check_start_report_text,
    get_check_start_report,
    get_check_start_text,
    get_check_stop_all_processes_text,
    format_check_stop_all_processes_report_text,
    get_check_stop_all_processes_report,
    format_check_stop_process_report_text,
    get_check_stop_process_report,
    get_check_stop_process_text,
    get_check_commit_report,
    get_check_commit_text,
    get_check_json_patch_text,
    get_check_json_patch_report,
    get_check_regex_replace_text,
    get_check_regex_replace_report,
    get_check_replace_lines_report,
    get_check_replace_lines_text,
    get_check_replace_python_definition_report,
    get_check_replace_python_definition_text,
    format_line_edit_report_text,
    format_replace_python_definition_report_text,
    get_check_restore_report,
    get_check_restore_text,
    format_git_index_report_text,
    get_check_stage_report,
    get_check_unstage_report,
    get_check_stage_text,
    get_check_unstage_text,
    get_check_json_remove_text,
    get_check_json_remove_report,
    get_check_json_set_text,
    get_check_json_set_report,
    format_code_defs_report_text,
    format_code_deps_report_text,
    format_code_ref_contexts_report_text,
    format_code_refs_report_text,
    format_code_rename_report_text,
    get_code_defs_report,
    get_code_defs_text,
    get_code_deps_report,
    get_code_deps_text,
    get_code_ref_contexts_report,
    get_code_ref_contexts_text,
    get_code_rename_preview_report,
    get_code_rename_preview_text,
    get_code_rename_report,
    get_code_rename_text,
    get_code_refs_report,
    get_code_refs_text,
    format_command_check_report_text,
    get_command_check_report,
    get_command_check_text,
    get_commands_text,
    format_checks_report_text,
    format_config_check_report_text,
    get_config_check_report,
    format_config_report_text,
    get_config_report,
    get_config_text,
    format_context_report_text,
    get_context_report,
    get_context_text,
    format_env_report_text,
    get_commit_text,
    get_commit_report,
    get_config_check_text,
    get_copy_dir_text,
    get_copy_dir_report,
    get_copy_dirs_text,
    get_copy_dirs_report,
    get_copy_file_report,
    get_copy_file_text,
    get_copy_files_report,
    get_copy_files_text,
    get_cost_report,
    format_cost_report_text,
    get_cost_text,
    get_create_dirs_text,
    get_create_dirs_report,
    get_create_dir_text,
    get_create_dir_report,
    get_delete_file_report,
    get_delete_file_text,
    get_delete_files_report,
    get_delete_files_text,
    get_delete_empty_dirs_text,
    get_delete_empty_dirs_report,
    get_delete_empty_dir_text,
    get_delete_empty_dir_report,
    format_diff_contexts_report_text,
    format_diff_hunks_report_text,
    format_diff_report_text,
    get_diff_contexts_report,
    get_diff_hunks_text,
    get_diff_hunks_report,
    get_diff_contexts_text,
    get_diff_report,
    get_diff_text,
    get_doctor_report,
    format_doctor_report_text,
    get_doctor_text,
    get_edit_file_report,
    get_edit_file_text,
    get_env_report,
    get_env_text,
    get_fetch_text,
    get_fetch_report,
    get_file_info_report,
    get_file_info_text,
    get_image_info_report,
    get_image_info_text,
    format_git_conflicts_report_text,
    get_git_conflicts_report,
    get_git_info_text,
    get_git_info_report,
    get_git_conflicts_text,
    get_git_status_report,
    get_git_status_text,
    get_find_files_report,
    get_find_files_text,
    get_glob_report,
    get_glob_text,
    format_handoff_report_text,
    get_handoff_report,
    get_handoff_text,
    format_http_fetch_report_text,
    get_http_fetch_report,
    get_http_fetch_text,
    format_http_report_text,
    get_http_report,
    get_http_text,
    get_insert_lines_report,
    get_insert_lines_text,
    format_instructions_report_text,
    get_instructions_report,
    get_instructions_text,
    format_init_report_text,
    get_init_report,
    get_json_patch_text,
    get_json_patch_report,
    get_json_remove_text,
    get_json_remove_report,
    get_json_set_text,
    get_json_set_report,
    get_last_session_report,
    get_last_session_text,
    get_log_report,
    get_log_text,
    format_manifests_report_text,
    get_manifests_report,
    get_manifests_text,
    format_model_report_text,
    get_model_report,
    get_model_text,
    get_move_dir_text,
    get_move_dir_report,
    get_move_dirs_text,
    get_move_dirs_report,
    get_move_file_report,
    get_move_file_text,
    get_move_files_report,
    get_move_files_text,
    get_multi_edit_file_report,
    get_multi_edit_file_text,
    format_overview_report_text,
    get_overview_report,
    get_overview_text,
    get_patch_text,
    get_patch_report,
    get_patches_text,
    get_patches_report,
    get_permissions_report,
    get_permissions_text,
    get_plan_report,
    get_plan_text,
    format_port_report_text,
    get_port_report,
    get_port_text,
    get_pull_text,
    get_pull_report,
    get_push_text,
    get_push_report,
    format_commands_report_text,
    get_commands_report,
    format_check_suggested_checks_report_text,
    get_check_suggested_checks_report,
    get_check_suggested_checks_text,
    get_around_report,
    get_around_many_report,
    get_around_text,
    get_around_many_text,
    get_output_contexts_report,
    get_output_contexts_text,
    get_output_diagnostics_report,
    get_output_diagnostics_text,
    get_process_output_contexts_report,
    get_process_output_contexts_text,
    get_process_output_diagnostics_report,
    get_process_output_diagnostics_text,
    get_process_report,
    get_process_text,
    format_processes_report_text,
    get_processes_report,
    get_processes_text,
    format_check_write_process_report_text,
    get_check_write_process_report,
    get_check_write_process_text,
    get_python_traceback_text,
    get_python_traceback_report,
    format_python_call_graph_report_text,
    get_python_call_graph_report,
    get_python_call_graph_text,
    format_python_calls_report_text,
    get_python_calls_report,
    get_python_calls_text,
    format_python_check_report_text,
    get_python_check_report,
    get_python_check_text,
    format_python_defs_report_text,
    get_python_defs_report,
    get_python_defs_text,
    format_python_deps_report_text,
    get_python_deps_report,
    get_python_deps_text,
    format_python_ref_contexts_report_text,
    get_python_ref_contexts_report,
    get_python_ref_contexts_text,
    format_python_refs_report_text,
    get_python_refs_report,
    get_python_refs_text,
    format_python_rename_report_text,
    get_python_rename_preview_report,
    get_python_rename_preview_text,
    get_python_rename_report,
    get_python_rename_text,
    get_read_report,
    get_read_files_report,
    get_read_ranges_report,
    get_read_files_text,
    get_read_ranges_text,
    get_read_text,
    get_regex_replace_text,
    get_regex_replace_report,
    format_check_focused_test_commands_report_text,
    get_check_focused_test_commands_report,
    get_check_focused_test_commands_text,
    format_focused_test_commands_report_text,
    get_focused_test_commands_report,
    get_focused_test_commands_text,
    format_related_tests_report_text,
    get_related_tests_report,
    get_related_tests_text,
    format_run_focused_test_commands_report_text,
    get_run_focused_test_commands_report,
    get_run_focused_test_commands_text,
    get_replace_lines_report,
    get_replace_lines_text,
    get_replace_python_definition_report,
    get_replace_python_definition_text,
    get_restore_report,
    format_repo_map_report_text,
    get_repo_map_report,
    get_repo_map_text,
    format_review_report_text,
    get_review_report,
    get_review_text,
    get_resume_context,
    get_restore_text,
    format_run_report_text,
    get_run_report,
    format_run_sequence_report_text,
    get_run_sequence_report,
    get_run_sequence_text,
    format_run_suggested_checks_report_text,
    get_run_suggested_checks_report,
    get_run_suggested_checks_text,
    get_run_text,
    get_session_audit_report,
    format_session_audit_report_text,
    get_session_audit_text,
    get_session_commands_report,
    format_session_commands_report_text,
    get_session_commands_text,
    get_session_output_contexts_report,
    format_session_output_contexts_report_text,
    get_session_output_contexts_text,
    get_session_output_diagnostics_report,
    format_session_output_diagnostics_report_text,
    get_session_output_diagnostics_text,
    get_session_failures_report,
    format_session_failures_report_text,
    get_session_failures_text,
    get_session_files_report,
    format_session_files_report_text,
    get_session_files_text,
    get_session_handoff_report,
    format_session_handoff_report_text,
    get_session_handoff_text,
    get_session_report,
    format_session_plan_report_text,
    format_session_search_report_text,
    format_session_summary_report_text,
    format_session_verification_report_text,
    get_session_search_report,
    get_session_text,
    get_session_verification_report,
    get_session_verification_text,
    get_sessions_report,
    format_sessions_report_text,
    get_sessions_text,
    format_search_contexts_report_text,
    format_search_report_text,
    get_search_report,
    get_search_text,
    get_search_contexts_report,
    get_search_contexts_text,
    get_session_search_text,
    get_set_executable_text,
    get_set_executable_report,
    get_show_report,
    get_show_text,
    format_start_report_text,
    get_start_report,
    get_start_text,
    get_stash_apply_report,
    get_stash_apply_text,
    get_stash_drop_report,
    get_stash_drop_text,
    get_stash_report,
    get_stash_text,
    get_stage_report,
    get_stage_text,
    get_stashes_text,
    get_stashes_report,
    format_status_report_text,
    get_status_report,
    get_status_text,
    get_tail_report,
    get_tail_text,
    format_tail_report_text,
    format_todos_report_text,
    get_todos_report,
    get_todos_text,
    get_stop_all_processes_text,
    format_stop_all_processes_report_text,
    get_stop_all_processes_report,
    format_stop_process_report_text,
    get_stop_process_report,
    get_stop_process_text,
    get_switch_text,
    get_switch_report,
    get_symbols_report,
    get_symbols_text,
    format_tool_report_text,
    get_tool_report,
    get_tool_text,
    format_tools_report_text,
    get_tools_report,
    get_tools_text,
    get_tree_report,
    get_tree_text,
    get_transcript_report,
    get_transcript_text,
    get_unstage_text,
    get_unstage_report,
    get_usage_report,
    format_usage_report_text,
    get_usage_text,
    get_wait_process_text,
    get_wait_process_report,
    format_wait_process_report_text,
    get_write_file_report,
    get_write_file_text,
    get_write_files_report,
    get_write_files_text,
    format_write_process_report_text,
    get_write_process_report,
    get_write_process_text,
    init_project_instructions,
    parse_local_command,
)
from .config import resolve_execution_config
from .providers import create_chat_client
from .types import ApprovalPolicy, ChatMessage


def main(argv: Sequence[str] | None = None) -> int:
    if argv is not None:
        args = parse_args(argv)
        validation_error = validate_cli_args(args)
        if validation_error is not None:
            return print_error_result(validation_error, args.json, exit_code=2)
        normalize_task_bound_diff_args(args)
        if has_local_flag(args):
            if args.task:
                return print_error_result("Local command flags cannot be combined with a task.", args.json, exit_code=2)
            return run_local_flag(args)
        if args.task:
            return run_one_shot(**build_one_shot_kwargs_from_args(args))
    if argv is not None:
        try:
            return run_interactive(args.cwd)
        except KeyboardInterrupt:
            return print_interrupted_result(args.json)
        except ValueError as error:
            return print_error_result(str(error), args.json, exit_code=2)
    return run_interactive()




def run_local_flag(args: argparse.Namespace) -> int:
    try:
        project_root = resolve_project_root(args.cwd)
        config_root = project_root or Path.cwd()
        payload_extra: dict[str, object] = {}
        if args.save_config:
            if args.json:
                save_config_report = save_project_config_report_from_args(args, config_root)
                payload_extra["saveConfig"] = save_config_report
                text = format_save_config_report_text(save_config_report)
            else:
                text = save_project_config_from_args(args, config_root)
        else:
            provider_env = build_provider_env(args, config_root)
            if (project_result := run_project_local_flag(args, project_root, config_root, provider_env, globals())) is not None:
                text, payload = project_result
                payload_extra.update(payload)
            elif (command_result := run_command_local_flag(args, project_root, globals())) is not None:
                text, payload = command_result
                payload_extra.update(payload)
            elif (read_result := run_read_local_flag(args, project_root, globals())) is not None:
                text, payload = read_result
                payload_extra.update(payload)
            elif (python_result := run_python_local_flag(args, project_root, globals())) is not None:
                text, payload = python_result
                payload_extra.update(payload)
            elif args.config_check is not None:
                if args.json:
                    config_check_report = get_config_check_report(project_root or ".", args.config_check or None)
                    payload_extra["configCheck"] = config_check_report
                    text = format_config_check_report_text(config_check_report)
                else:
                    text = get_config_check_text(project_root or ".", args.config_check or None)
            elif args.check_json_set is not None:
                json_kwargs = {
                    "path": args.check_json_set[0],
                    "pointer": args.check_json_set[1],
                    "value": parse_cli_json_value(args.check_json_set[2]),
                    "create_missing": args.json_create_missing,
                }
                if args.json:
                    json_report = get_check_json_set_report(project_root or ".", **json_kwargs)
                    payload_extra["checkJsonSet"] = json_report
                    text = format_json_pointer_report_text("Check JSON set:", json_report)
                else:
                    text = get_check_json_set_text(project_root or ".", **json_kwargs)
            elif args.json_set is not None:
                json_kwargs = {
                    "path": args.json_set[0],
                    "pointer": args.json_set[1],
                    "value": parse_cli_json_value(args.json_set[2]),
                    "create_missing": args.json_create_missing,
                }
                if args.json:
                    json_report = get_json_set_report(project_root or ".", **json_kwargs)
                    payload_extra["jsonSet"] = json_report
                    text = format_json_pointer_report_text("JSON set:", json_report)
                else:
                    text = get_json_set_text(project_root or ".", **json_kwargs)
            elif args.check_json_remove is not None:
                json_kwargs = {"path": args.check_json_remove[0], "pointer": args.check_json_remove[1]}
                if args.json:
                    json_report = get_check_json_remove_report(project_root or ".", **json_kwargs)
                    payload_extra["checkJsonRemove"] = json_report
                    text = format_json_pointer_report_text("Check JSON remove:", json_report)
                else:
                    text = get_check_json_remove_text(project_root or ".", **json_kwargs)
            elif args.json_remove is not None:
                json_kwargs = {"path": args.json_remove[0], "pointer": args.json_remove[1]}
                if args.json:
                    json_report = get_json_remove_report(project_root or ".", **json_kwargs)
                    payload_extra["jsonRemove"] = json_report
                    text = format_json_pointer_report_text("JSON remove:", json_report)
                else:
                    text = get_json_remove_text(project_root or ".", **json_kwargs)
            elif args.check_json_patch is not None:
                json_kwargs = {"path": args.check_json_patch[0], "operations": parse_cli_json_value(args.check_json_patch[1])}
                if args.json:
                    json_report = get_check_json_patch_report(project_root or ".", **json_kwargs)
                    payload_extra["checkJsonPatch"] = json_report
                    text = format_json_patch_report_text("Check JSON patch:", json_report)
                else:
                    text = get_check_json_patch_text(project_root or ".", **json_kwargs)
            elif args.json_patch is not None:
                json_kwargs = {"path": args.json_patch[0], "operations": parse_cli_json_value(args.json_patch[1])}
                if args.json:
                    json_report = get_json_patch_report(project_root or ".", **json_kwargs)
                    payload_extra["jsonPatch"] = json_report
                    text = format_json_patch_report_text("JSON patch:", json_report)
                else:
                    text = get_json_patch_text(project_root or ".", **json_kwargs)
            elif args.check_replace_lines is not None:
                line_kwargs = {
                    "path": args.check_replace_lines[0],
                    "start_line": args.check_replace_lines[1],
                    "end_line": args.check_replace_lines[2],
                    "content": args.check_replace_lines[3],
                }
                if args.json:
                    line_report = get_check_replace_lines_report(project_root or ".", **line_kwargs)
                    payload_extra["checkReplaceLines"] = line_report
                    text = format_line_edit_report_text("Check replace lines:", line_report)
                else:
                    text = get_check_replace_lines_text(project_root or ".", **line_kwargs)
            elif args.replace_lines is not None:
                line_kwargs = {
                    "path": args.replace_lines[0],
                    "start_line": args.replace_lines[1],
                    "end_line": args.replace_lines[2],
                    "content": args.replace_lines[3],
                }
                if args.json:
                    line_report = get_replace_lines_report(project_root or ".", **line_kwargs)
                    payload_extra["replaceLines"] = line_report
                    text = format_line_edit_report_text("Replace lines:", line_report)
                else:
                    text = get_replace_lines_text(project_root or ".", **line_kwargs)
            elif args.check_insert_lines is not None:
                line_kwargs = {
                    "path": args.check_insert_lines[0],
                    "line": args.check_insert_lines[1],
                    "content": args.check_insert_lines[2],
                }
                if args.json:
                    line_report = get_check_insert_lines_report(project_root or ".", **line_kwargs)
                    payload_extra["checkInsertLines"] = line_report
                    text = format_line_edit_report_text("Check insert lines:", line_report)
                else:
                    text = get_check_insert_lines_text(project_root or ".", **line_kwargs)
            elif args.insert_lines is not None:
                line_kwargs = {
                    "path": args.insert_lines[0],
                    "line": args.insert_lines[1],
                    "content": args.insert_lines[2],
                }
                if args.json:
                    line_report = get_insert_lines_report(project_root or ".", **line_kwargs)
                    payload_extra["insertLines"] = line_report
                    text = format_line_edit_report_text("Insert lines:", line_report)
                else:
                    text = get_insert_lines_text(project_root or ".", **line_kwargs)
            elif args.check_append is not None:
                append_kwargs = {"path": args.check_append[0], "content": args.check_append[1]}
                if args.json:
                    append_report = get_check_append_file_report(project_root or ".", **append_kwargs)
                    payload_extra["checkAppend"] = append_report
                    text = format_line_edit_report_text("Check append:", append_report)
                else:
                    text = get_check_append_file_text(project_root or ".", **append_kwargs)
            elif args.append is not None:
                append_kwargs = {"path": args.append[0], "content": args.append[1]}
                if args.json:
                    append_report = get_append_file_report(project_root or ".", **append_kwargs)
                    payload_extra["append"] = append_report
                    text = format_line_edit_report_text("Append:", append_report)
                else:
                    text = get_append_file_text(project_root or ".", **append_kwargs)
            elif args.check_write is not None:
                write_kwargs = {"path": args.check_write[0], "content": args.check_write[1]}
                if args.json:
                    write_report = get_check_write_file_report(project_root or ".", **write_kwargs)
                    payload_extra["checkWrite"] = write_report
                    text = format_line_edit_report_text("Check write:", write_report)
                else:
                    text = get_check_write_file_text(project_root or ".", **write_kwargs)
            elif args.write is not None:
                write_kwargs = {"path": args.write[0], "content": args.write[1]}
                if args.json:
                    write_report = get_write_file_report(project_root or ".", **write_kwargs)
                    payload_extra["write"] = write_report
                    text = format_line_edit_report_text("Write:", write_report)
                else:
                    text = get_write_file_text(project_root or ".", **write_kwargs)
            elif args.check_write_files is not None:
                if args.json:
                    write_files_report = get_check_write_files_report(project_root or ".", files=args.check_write_files)
                    payload_extra["checkWriteFiles"] = write_files_report
                    text = format_write_files_report_text("Check write files:", write_files_report)
                else:
                    text = get_check_write_files_text(project_root or ".", files=args.check_write_files)
            elif args.write_files is not None:
                if args.json:
                    write_files_report = get_write_files_report(project_root or ".", files=args.write_files)
                    payload_extra["writeFiles"] = write_files_report
                    text = format_write_files_report_text("Write files:", write_files_report)
                else:
                    text = get_write_files_text(project_root or ".", files=args.write_files)
            elif args.check_edit is not None:
                edit_kwargs = {"path": args.check_edit[0], "old": args.check_edit[1], "new": args.check_edit[2]}
                if args.json:
                    edit_report = get_check_edit_file_report(project_root or ".", **edit_kwargs)
                    payload_extra["checkEdit"] = edit_report
                    text = format_line_edit_report_text("Check edit:", edit_report)
                else:
                    text = get_check_edit_file_text(project_root or ".", **edit_kwargs)
            elif args.edit is not None:
                edit_kwargs = {"path": args.edit[0], "old": args.edit[1], "new": args.edit[2]}
                if args.json:
                    edit_report = get_edit_file_report(project_root or ".", **edit_kwargs)
                    payload_extra["edit"] = edit_report
                    text = format_line_edit_report_text("Edit:", edit_report)
                else:
                    text = get_edit_file_text(project_root or ".", **edit_kwargs)
            elif args.check_multi_edit is not None:
                path, edits = parse_multi_edit_flag_values(args.check_multi_edit, "--check-multi-edit")
                if args.json:
                    edit_report = get_check_multi_edit_file_report(project_root or ".", path=path, edits=edits)
                    payload_extra["checkMultiEdit"] = edit_report
                    text = format_line_edit_report_text("Check multi edit:", edit_report)
                else:
                    text = get_check_multi_edit_file_text(project_root or ".", path=path, edits=edits)
            elif args.multi_edit is not None:
                path, edits = parse_multi_edit_flag_values(args.multi_edit, "--multi-edit")
                if args.json:
                    edit_report = get_multi_edit_file_report(project_root or ".", path=path, edits=edits)
                    payload_extra["multiEdit"] = edit_report
                    text = format_line_edit_report_text("Multi edit:", edit_report)
                else:
                    text = get_multi_edit_file_text(project_root or ".", path=path, edits=edits)
            elif args.check_delete is not None:
                delete_kwargs = {"path": args.check_delete}
                if args.json:
                    delete_report = get_check_delete_file_report(project_root or ".", **delete_kwargs)
                    payload_extra["checkDelete"] = delete_report
                    text = format_line_edit_report_text("Check delete:", delete_report)
                else:
                    text = get_check_delete_file_text(project_root or ".", **delete_kwargs)
            elif args.delete is not None:
                delete_kwargs = {"path": args.delete}
                if args.json:
                    delete_report = get_delete_file_report(project_root or ".", **delete_kwargs)
                    payload_extra["delete"] = delete_report
                    text = format_line_edit_report_text("Delete:", delete_report)
                else:
                    text = get_delete_file_text(project_root or ".", **delete_kwargs)
            elif args.check_delete_files is not None:
                if args.json:
                    delete_report = get_check_delete_files_report(project_root or ".", paths=args.check_delete_files)
                    payload_extra["checkDeleteFiles"] = delete_report
                    text = format_path_list_report_text("Check delete files:", delete_report, include_diff=True)
                else:
                    text = get_check_delete_files_text(project_root or ".", paths=args.check_delete_files)
            elif args.delete_files is not None:
                if args.json:
                    delete_report = get_delete_files_report(project_root or ".", paths=args.delete_files)
                    payload_extra["deleteFiles"] = delete_report
                    text = format_path_list_report_text("Delete files:", delete_report, include_diff=True)
                else:
                    text = get_delete_files_text(project_root or ".", paths=args.delete_files)
            elif args.check_move is not None:
                transfer_kwargs = {"source": args.check_move[0], "destination": args.check_move[1]}
                if args.json:
                    transfer_report = get_check_move_file_report(project_root or ".", **transfer_kwargs)
                    payload_extra["checkMove"] = transfer_report
                    text = format_file_transfer_report_text("Check move:", transfer_report)
                else:
                    text = get_check_move_file_text(project_root or ".", **transfer_kwargs)
            elif args.move is not None:
                transfer_kwargs = {"source": args.move[0], "destination": args.move[1]}
                if args.json:
                    transfer_report = get_move_file_report(project_root or ".", **transfer_kwargs)
                    payload_extra["move"] = transfer_report
                    text = format_file_transfer_report_text("Move:", transfer_report)
                else:
                    text = get_move_file_text(project_root or ".", **transfer_kwargs)
            elif args.check_move_files is not None:
                if args.json:
                    transfer_report = get_check_move_files_report(project_root or ".", transfers=args.check_move_files)
                    payload_extra["checkMoveFiles"] = transfer_report
                    text = format_file_transfer_list_report_text("Check move files:", transfer_report)
                else:
                    text = get_check_move_files_text(project_root or ".", transfers=args.check_move_files)
            elif args.move_files is not None:
                if args.json:
                    transfer_report = get_move_files_report(project_root or ".", transfers=args.move_files)
                    payload_extra["moveFiles"] = transfer_report
                    text = format_file_transfer_list_report_text("Move files:", transfer_report)
                else:
                    text = get_move_files_text(project_root or ".", transfers=args.move_files)
            elif args.check_copy is not None:
                transfer_kwargs = {"source": args.check_copy[0], "destination": args.check_copy[1]}
                if args.json:
                    transfer_report = get_check_copy_file_report(project_root or ".", **transfer_kwargs)
                    payload_extra["checkCopy"] = transfer_report
                    text = format_file_transfer_report_text("Check copy:", transfer_report)
                else:
                    text = get_check_copy_file_text(project_root or ".", **transfer_kwargs)
            elif args.copy is not None:
                transfer_kwargs = {"source": args.copy[0], "destination": args.copy[1]}
                if args.json:
                    transfer_report = get_copy_file_report(project_root or ".", **transfer_kwargs)
                    payload_extra["copy"] = transfer_report
                    text = format_file_transfer_report_text("Copy:", transfer_report)
                else:
                    text = get_copy_file_text(project_root or ".", **transfer_kwargs)
            elif args.check_copy_files is not None:
                if args.json:
                    transfer_report = get_check_copy_files_report(project_root or ".", transfers=args.check_copy_files)
                    payload_extra["checkCopyFiles"] = transfer_report
                    text = format_file_transfer_list_report_text("Check copy files:", transfer_report)
                else:
                    text = get_check_copy_files_text(project_root or ".", transfers=args.check_copy_files)
            elif args.copy_files is not None:
                if args.json:
                    transfer_report = get_copy_files_report(project_root or ".", transfers=args.copy_files)
                    payload_extra["copyFiles"] = transfer_report
                    text = format_file_transfer_list_report_text("Copy files:", transfer_report)
                else:
                    text = get_copy_files_text(project_root or ".", transfers=args.copy_files)
            elif args.check_move_dir is not None:
                transfer_kwargs = {"source": args.check_move_dir[0], "destination": args.check_move_dir[1]}
                if args.json:
                    transfer_report = get_check_move_dir_report(project_root or ".", **transfer_kwargs)
                    payload_extra["checkMoveDir"] = transfer_report
                    text = format_file_transfer_report_text("Check move dir:", transfer_report)
                else:
                    text = get_check_move_dir_text(project_root or ".", **transfer_kwargs)
            elif args.move_dir is not None:
                transfer_kwargs = {"source": args.move_dir[0], "destination": args.move_dir[1]}
                if args.json:
                    transfer_report = get_move_dir_report(project_root or ".", **transfer_kwargs)
                    payload_extra["moveDir"] = transfer_report
                    text = format_file_transfer_report_text("Move dir:", transfer_report)
                else:
                    text = get_move_dir_text(project_root or ".", **transfer_kwargs)
            elif args.check_move_dirs is not None:
                if args.json:
                    transfer_report = get_check_move_dirs_report(project_root or ".", transfers=args.check_move_dirs)
                    payload_extra["checkMoveDirs"] = transfer_report
                    text = format_file_transfer_list_report_text("Check move dirs:", transfer_report)
                else:
                    text = get_check_move_dirs_text(project_root or ".", transfers=args.check_move_dirs)
            elif args.move_dirs is not None:
                if args.json:
                    transfer_report = get_move_dirs_report(project_root or ".", transfers=args.move_dirs)
                    payload_extra["moveDirs"] = transfer_report
                    text = format_file_transfer_list_report_text("Move dirs:", transfer_report)
                else:
                    text = get_move_dirs_text(project_root or ".", transfers=args.move_dirs)
            elif args.check_copy_dir is not None:
                transfer_kwargs = {"source": args.check_copy_dir[0], "destination": args.check_copy_dir[1]}
                if args.json:
                    transfer_report = get_check_copy_dir_report(project_root or ".", **transfer_kwargs)
                    payload_extra["checkCopyDir"] = transfer_report
                    text = format_file_transfer_report_text("Check copy dir:", transfer_report)
                else:
                    text = get_check_copy_dir_text(project_root or ".", **transfer_kwargs)
            elif args.copy_dir is not None:
                transfer_kwargs = {"source": args.copy_dir[0], "destination": args.copy_dir[1]}
                if args.json:
                    transfer_report = get_copy_dir_report(project_root or ".", **transfer_kwargs)
                    payload_extra["copyDir"] = transfer_report
                    text = format_file_transfer_report_text("Copy dir:", transfer_report)
                else:
                    text = get_copy_dir_text(project_root or ".", **transfer_kwargs)
            elif args.check_copy_dirs is not None:
                if args.json:
                    transfer_report = get_check_copy_dirs_report(project_root or ".", transfers=args.check_copy_dirs)
                    payload_extra["checkCopyDirs"] = transfer_report
                    text = format_file_transfer_list_report_text("Check copy dirs:", transfer_report)
                else:
                    text = get_check_copy_dirs_text(project_root or ".", transfers=args.check_copy_dirs)
            elif args.copy_dirs is not None:
                if args.json:
                    transfer_report = get_copy_dirs_report(project_root or ".", transfers=args.copy_dirs)
                    payload_extra["copyDirs"] = transfer_report
                    text = format_file_transfer_list_report_text("Copy dirs:", transfer_report)
                else:
                    text = get_copy_dirs_text(project_root or ".", transfers=args.copy_dirs)
            elif args.check_mkdir is not None:
                if args.json:
                    path_report = get_check_create_dir_report(project_root or ".", path=args.check_mkdir)
                    payload_extra["checkCreateDir"] = path_report
                    text = format_path_action_report_text("Check mkdir:", path_report)
                else:
                    text = get_check_create_dir_text(project_root or ".", path=args.check_mkdir)
            elif args.mkdir is not None:
                if args.json:
                    path_report = get_create_dir_report(project_root or ".", path=args.mkdir)
                    payload_extra["createDir"] = path_report
                    text = format_path_action_report_text("Mkdir:", path_report)
                else:
                    text = get_create_dir_text(project_root or ".", path=args.mkdir)
            elif args.check_mkdirs is not None:
                if args.json:
                    paths_report = get_check_create_dirs_report(project_root or ".", paths=args.check_mkdirs)
                    payload_extra["checkCreateDirs"] = paths_report
                    text = format_path_list_report_text("Check mkdirs:", paths_report)
                else:
                    text = get_check_create_dirs_text(project_root or ".", paths=args.check_mkdirs)
            elif args.mkdirs is not None:
                if args.json:
                    paths_report = get_create_dirs_report(project_root or ".", paths=args.mkdirs)
                    payload_extra["createDirs"] = paths_report
                    text = format_path_list_report_text("Mkdirs:", paths_report)
                else:
                    text = get_create_dirs_text(project_root or ".", paths=args.mkdirs)
            elif args.check_rmdir is not None:
                if args.json:
                    path_report = get_check_delete_empty_dir_report(project_root or ".", path=args.check_rmdir)
                    payload_extra["checkDeleteEmptyDir"] = path_report
                    text = format_path_action_report_text("Check rmdir:", path_report)
                else:
                    text = get_check_delete_empty_dir_text(project_root or ".", path=args.check_rmdir)
            elif args.rmdir is not None:
                if args.json:
                    path_report = get_delete_empty_dir_report(project_root or ".", path=args.rmdir)
                    payload_extra["deleteEmptyDir"] = path_report
                    text = format_path_action_report_text("Rmdir:", path_report)
                else:
                    text = get_delete_empty_dir_text(project_root or ".", path=args.rmdir)
            elif args.check_rmdirs is not None:
                if args.json:
                    paths_report = get_check_delete_empty_dirs_report(project_root or ".", paths=args.check_rmdirs)
                    payload_extra["checkDeleteEmptyDirs"] = paths_report
                    text = format_path_list_report_text("Check rmdirs:", paths_report)
                else:
                    text = get_check_delete_empty_dirs_text(project_root or ".", paths=args.check_rmdirs)
            elif args.rmdirs is not None:
                if args.json:
                    paths_report = get_delete_empty_dirs_report(project_root or ".", paths=args.rmdirs)
                    payload_extra["deleteEmptyDirs"] = paths_report
                    text = format_path_list_report_text("Rmdirs:", paths_report)
                else:
                    text = get_delete_empty_dirs_text(project_root or ".", paths=args.rmdirs)
            elif args.check_executable is not None:
                path, executable = parse_executable_flag_values(args.check_executable, "--check-executable")
                if args.json:
                    executable_report = get_check_set_executable_report(project_root or ".", path=path, executable=executable)
                    payload_extra["checkSetExecutable"] = executable_report
                    text = format_executable_report_text("Check executable:", executable_report)
                else:
                    text = get_check_set_executable_text(project_root or ".", path=path, executable=executable)
            elif args.set_executable is not None:
                path, executable = parse_executable_flag_values(args.set_executable, "--set-executable")
                if args.json:
                    executable_report = get_set_executable_report(project_root or ".", path=path, executable=executable)
                    payload_extra["setExecutable"] = executable_report
                    text = format_executable_report_text("Set executable:", executable_report)
                else:
                    text = get_set_executable_text(project_root or ".", path=path, executable=executable)
            elif args.check_patch is not None:
                patch_kwargs = {"path": args.check_patch[0], "patch": args.check_patch[1]}
                if args.json:
                    patch_report = get_check_patch_report(project_root or ".", **patch_kwargs)
                    payload_extra["checkPatch"] = patch_report
                    text = format_patch_report_text("Check patch:", patch_report)
                else:
                    text = get_check_patch_text(project_root or ".", **patch_kwargs)
            elif args.patch is not None:
                patch_kwargs = {"path": args.patch[0], "patch": args.patch[1]}
                if args.json:
                    patch_report = get_patch_report(project_root or ".", **patch_kwargs)
                    payload_extra["patch"] = patch_report
                    text = format_patch_report_text("Patch:", patch_report)
                else:
                    text = get_patch_text(project_root or ".", **patch_kwargs)
            elif args.check_patches is not None:
                if args.json:
                    patch_report = get_check_patches_report(project_root or ".", patch=args.check_patches)
                    payload_extra["checkPatches"] = patch_report
                    text = format_patches_report_text("Check patches:", patch_report)
                else:
                    text = get_check_patches_text(project_root or ".", patch=args.check_patches)
            elif args.patches is not None:
                if args.json:
                    patch_report = get_patches_report(project_root or ".", patch=args.patches)
                    payload_extra["patches"] = patch_report
                    text = format_patches_report_text("Patches:", patch_report)
                else:
                    text = get_patches_text(project_root or ".", patch=args.patches)
            elif args.check_regex_replace is not None:
                regex_kwargs = {
                    "path": args.check_regex_replace[0],
                    "pattern": args.check_regex_replace[1],
                    "replacement": args.check_regex_replace[2],
                    "count": args.regex_count,
                    "case_sensitive": not args.regex_ignore_case,
                    "multiline": args.regex_multiline,
                    "max_replacements": args.regex_max_replacements,
                }
                if args.json:
                    regex_report = get_check_regex_replace_report(project_root or ".", **regex_kwargs)
                    payload_extra["checkRegexReplace"] = regex_report
                    text = format_regex_replace_report_text("Check regex replace:", regex_report)
                else:
                    text = get_check_regex_replace_text(project_root or ".", **regex_kwargs)
            elif args.regex_replace is not None:
                regex_kwargs = {
                    "path": args.regex_replace[0],
                    "pattern": args.regex_replace[1],
                    "replacement": args.regex_replace[2],
                    "count": args.regex_count,
                    "case_sensitive": not args.regex_ignore_case,
                    "multiline": args.regex_multiline,
                    "max_replacements": args.regex_max_replacements,
                }
                if args.json:
                    regex_report = get_regex_replace_report(project_root or ".", **regex_kwargs)
                    payload_extra["regexReplace"] = regex_report
                    text = format_regex_replace_report_text("Regex replace:", regex_report)
                else:
                    text = get_regex_replace_text(project_root or ".", **regex_kwargs)
            elif (code_intel_result := run_code_intel_local_flag(args, project_root, globals())) is not None:
                text, payload = code_intel_result
                payload_extra.update(payload)
            elif (git_result := run_git_local_flag(args, project_root, globals())) is not None:
                text, payload = git_result
                payload_extra.update(payload)
            elif (runtime_result := run_runtime_local_flag(args, project_root, globals())) is not None:
                text, payload = runtime_result
                payload_extra.update(payload)
            elif (review_result := run_review_local_flag(args, project_root, provider_env, globals())) is not None:
                text, payload = review_result
                payload_extra.update(payload)
            elif (session_result := run_session_local_flag(args, project_root, globals())) is not None:
                text, payload = session_result
                payload_extra.update(payload)
            elif (checkpoint_result := run_checkpoint_local_flag(args, project_root, globals())) is not None:
                text, payload = checkpoint_result
                payload_extra.update(payload)
            else:
                text = ""
        return emit_local_result(args, text, payload_extra)
    except KeyboardInterrupt:
        return print_interrupted_result(args.json)
    except Exception as error:
        return print_error_result(format_error(error), args.json, prefix=True)


def run_interactive(base_dir: str | None = None) -> int:
    project_root = resolve_project_root(base_dir)
    if project_root is None:
        return run_interactive_loop()

    previous_cwd = Path.cwd()
    os.chdir(project_root)
    try:
        return run_interactive_loop()
    finally:
        os.chdir(previous_cwd)


def run_one_shot(*args, **kwargs) -> int:
    kwargs.setdefault("create_chat_client_func", create_chat_client)
    kwargs.setdefault("run_chat_func", run_chat)
    kwargs.setdefault("run_agent_func", run_agent)
    kwargs.setdefault("get_resume_context_func", get_resume_context)
    kwargs.setdefault("get_compact_context_func", get_compact_context)
    return _run_one_shot(*args, **kwargs)


def run_interactive_loop() -> int:
    # Entry loop: parse local commands first, otherwise delegate to the agent.
    print("VibeAgent v0.1")
    print("Type a programming task, or use /chat for daily conversation. Use /help for commands.")

    client = None
    mode = "code"
    approval_policy: ApprovalPolicy = "ask"
    chat_history: list[ChatMessage] = []
    resume_run_id: str | None = None
    resume_context: str | None = None
    while True:
        try:
            task = input("\nvibeagent> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if not task:
            continue

        command = parse_local_command(task)
        if command and command.type == "exit":
            return 0
        if command and (project_text := run_interactive_project_command(command, globals(), approval_policy)) is not None:
            print(project_text)
            continue
        if command and (command_text := run_interactive_command_execution(command, globals())) is not None:
            print(command_text)
            continue
        if command and (read_text := run_interactive_read_command(command, globals())) is not None:
            print(read_text)
            continue
        if command and (code_intel_text := run_interactive_code_intel_command(command, globals())) is not None:
            print(code_intel_text)
            continue
        if command and (edit_text := run_interactive_edit_command(command, globals())) is not None:
            print(edit_text)
            continue
        if command and (git_text := run_interactive_git_command(command, globals())) is not None:
            print(git_text)
            continue
        if command and (runtime_text := run_interactive_runtime_command(command, globals())) is not None:
            print(runtime_text)
            continue
        if command and (
            state_text := run_interactive_project_state_command(
                command,
                globals(),
                mode=mode,
                approval_policy=approval_policy,
                resume_run_id=resume_run_id,
                resume_context=resume_context,
                chat_turns=len(chat_history) // 2,
            )
        ) is not None:
            print(state_text)
            continue
        if command and (review_text := run_interactive_review_command(command, globals())) is not None:
            print(review_text)
            continue
        if command and command.type == "clear":
            chat_history.clear()
            resume_run_id = None
            resume_context = None
            print("Cleared chat history and resume context.")
            continue
        if command and command.type == "approval":
            approval_policy, text = handle_approval_command(command.argument, approval_policy)
            print(text)
            continue
        if command and (session_text := run_interactive_session_command(command, globals())) is not None:
            print(session_text)
            continue
        if command and (checkpoint_text := run_interactive_checkpoint_command(command, globals())) is not None:
            print(checkpoint_text)
            continue
        if command and (resume_result := run_interactive_resume_command(command, globals())) is not None:
            selected, context, text = resume_result
            resume_run_id = selected
            resume_context = context
            print(text)
            continue
        request_mode = mode
        if command and command.type == "chat":
            if not command.argument:
                mode = "chat"
                print("Chat mode. Use /code to switch back to coding mode.")
                continue
            task = command.argument
            request_mode = "chat"
        elif command and command.type == "code":
            if not command.argument:
                mode = "code"
                print("Coding mode. Use /chat to switch to daily conversation mode.")
                continue
            task = command.argument
            request_mode = "code"

        try:
            # Reuse client across turns so auth/model config is loaded once.
            execution_config = resolve_execution_config(Path.cwd())
            client = client or create_chat_client(build_provider_env(None, Path.cwd()))
            if request_mode == "chat":
                response = run_chat(
                    task,
                    client=client,
                    history=chat_history,
                    max_output_tokens=execution_config.max_output_tokens,
                    model_retries=execution_config.model_retries,
                    model_retry_delay_ms=execution_config.model_retry_delay_ms,
                    model_timeout_ms=execution_config.model_timeout_ms,
                )
                chat_history.extend(
                    [
                        ChatMessage(role="user", content=task),
                        ChatMessage(role="assistant", content=response),
                    ]
                )
                print(f"\n{response}")
                continue

            result = run_agent(
                task,
                client=client,
                max_iterations=execution_config.max_iterations,
                command_timeout_ms=execution_config.command_timeout_ms,
                max_output_tokens=execution_config.max_output_tokens,
                model_retries=execution_config.model_retries,
                model_retry_delay_ms=execution_config.model_retry_delay_ms,
                model_timeout_ms=execution_config.model_timeout_ms,
                approval_handler=build_approval_handler(approval_policy),
                prior_context=resume_context,
            )
            print_agent_result(result)
            selected, next_context, _ = get_resume_context(result.run_id)
            if next_context:
                resume_run_id = selected
                resume_context = next_context
        except KeyboardInterrupt:
            print("\nInterrupted.")
        except Exception as error:
            print(f"\nError: {format_error(error)}")
if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
