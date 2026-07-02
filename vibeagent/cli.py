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
    local_result_exit_code,
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
    print_output,
    prompt_approval,
)
from .cli_runner import (
    build_context_limit_kwargs,
    is_resume_clear_arg,
    normalize_resume_arg,
    resolve_task_text,
    run_one_shot as _run_one_shot,
)
from .cli_validation import validate_cli_args
from .cli_parsing import (
    build_diff_argument,
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
        if args.diff_contexts is not None and args.task:
            args.diff_contexts = build_diff_argument(args.diff_contexts, args.diff_staged, args.task)
            args.task = []
        elif args.diff_contexts is not None and args.diff_staged:
            args.diff_contexts = build_diff_argument(args.diff_contexts, args.diff_staged, [])
        elif args.diff_hunks is not None and args.task:
            args.diff_hunks = build_diff_argument(args.diff_hunks, args.diff_staged, args.task)
            args.task = []
        elif args.diff_hunks is not None and args.diff_staged:
            args.diff_hunks = build_diff_argument(args.diff_hunks, args.diff_staged, [])
        elif args.diff is not None and args.task:
            args.diff = build_diff_argument(args.diff, args.diff_staged, args.task)
            args.task = []
        elif args.diff is not None and args.diff_staged:
            args.diff = build_diff_argument(args.diff, args.diff_staged, [])
        if has_local_flag(args):
            if args.task:
                return print_error_result("Local command flags cannot be combined with a task.", args.json, exit_code=2)
            return run_local_flag(args)
        if args.task:
            return run_one_shot(
                resolve_task_text(args.task),
                request_mode="chat" if args.chat else "code",
                approval_policy=args.approval,
                resume_arg=args.resume,
                compact_arg=args.compact,
                resume_max_failures=args.resume_max_failures,
                resume_max_files=args.resume_max_files,
                resume_max_commands=args.resume_max_commands,
                resume_max_checks=args.resume_max_checks,
                resume_max_output_chars=args.resume_max_output_chars,
                resume_max_text=args.resume_max_text,
                compact_max_failures=args.compact_max_failures,
                compact_max_files=args.compact_max_files,
                compact_max_commands=args.compact_max_commands,
                compact_max_checks=args.compact_max_checks,
                compact_max_output_chars=args.compact_max_output_chars,
                compact_max_text=args.compact_max_text,
                base_dir=args.cwd,
                max_iterations=args.max_iterations,
                command_timeout_ms=args.command_timeout_ms,
                max_output_tokens=args.max_output_tokens,
                model_retries=args.model_retries,
                model_retry_delay_ms=args.model_retry_delay_ms,
                model_timeout_ms=args.model_timeout_ms,
                output_json=args.json,
                provider_args=args,
            )
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
            if args.model:
                if args.json:
                    model_report = get_model_report(provider_env)
                    payload_extra["model"] = model_report
                    text = format_model_report_text(model_report)
                else:
                    text = get_model_text(provider_env)
            elif args.config:
                config_kwargs = {
                    "max_iterations": args.max_iterations,
                    "command_timeout_ms": args.command_timeout_ms,
                    "max_output_tokens": args.max_output_tokens,
                    "model_retries": args.model_retries,
                    "model_retry_delay_ms": args.model_retry_delay_ms,
                    "model_timeout_ms": args.model_timeout_ms,
                }
                if args.json:
                    config_report = get_config_report(config_root, provider_env, **config_kwargs)
                    payload_extra["config"] = config_report
                    text = format_config_report_text(config_report)
                else:
                    text = get_config_text(config_root, provider_env, **config_kwargs)
            elif args.tools:
                if args.json:
                    tools_report = get_tools_report()
                    payload_extra["tools"] = tools_report
                    text = format_tools_report_text(tools_report)
                else:
                    text = get_tools_text()
            elif args.tool is not None:
                if args.json:
                    tool_report = get_tool_report(args.tool)
                    payload_extra["tool"] = tool_report
                    text = format_tool_report_text(tool_report)
                else:
                    text = get_tool_text(args.tool)
            elif args.permissions:
                if args.json:
                    permissions_report = get_permissions_report(args.approval)
                    payload_extra["permissions"] = permissions_report
                    text = format_permissions_report_text(permissions_report)
                else:
                    text = get_permissions_text(args.approval)
            elif args.checks:
                if args.json:
                    checks_report = get_checks_report(project_root or ".", max_checks=args.checks_max)
                    payload_extra["checks"] = checks_report
                    text = format_checks_report_text(checks_report)
                else:
                    text = get_checks_text(project_root or ".", max_checks=args.checks_max)
            elif args.check_suggested_checks is not None:
                check_suggested_kwargs = {
                    "argument": args.check_suggested_checks or None,
                    "max_checks": args.check_suggested_checks_max,
                }
                if args.json:
                    check_suggested_report = get_check_suggested_checks_report(project_root or ".", **check_suggested_kwargs)
                    payload_extra["checkSuggestedChecks"] = check_suggested_report
                    text = format_check_suggested_checks_report_text(check_suggested_report)
                else:
                    text = get_check_suggested_checks_text(
                        project_root or ".",
                        check_suggested_kwargs["argument"],
                        max_checks=args.check_suggested_checks_max,
                    )
            elif args.run_suggested_checks is not None:
                run_suggested_kwargs = {
                    "argument": args.run_suggested_checks or None,
                    "max_checks": args.run_suggested_checks_max,
                    "timeout_ms": args.run_timeout_ms,
                    "max_output_chars": args.run_max_chars,
                    "stop_on_failure": not args.run_continue_on_failure,
                    "extract_output_contexts": args.run_output_contexts,
                    "extract_output_diagnostics": args.run_output_diagnostics,
                    "context_lines": args.run_output_context_lines,
                    "max_diagnostics": args.run_output_diagnostic_max,
                    "max_contexts": args.run_output_context_max,
                    "max_bytes_per_context": args.run_output_context_max_bytes,
                }
                if args.json:
                    run_suggested_report = get_run_suggested_checks_report(project_root or ".", **run_suggested_kwargs)
                    payload_extra["runSuggestedChecks"] = run_suggested_report
                    text = format_run_suggested_checks_report_text(run_suggested_report)
                else:
                    text = get_run_suggested_checks_text(
                        project_root or ".",
                        run_suggested_kwargs["argument"],
                        max_checks=args.run_suggested_checks_max,
                        timeout_ms=args.run_timeout_ms,
                        max_output_chars=args.run_max_chars,
                        stop_on_failure=not args.run_continue_on_failure,
                        extract_output_contexts=args.run_output_contexts,
                        extract_output_diagnostics=args.run_output_diagnostics,
                        context_lines=args.run_output_context_lines,
                        max_diagnostics=args.run_output_diagnostic_max,
                        max_contexts=args.run_output_context_max,
                        max_bytes_per_context=args.run_output_context_max_bytes,
                    )
            elif args.commands:
                commands_kwargs = {}
                if args.commands_max_commands is not None:
                    commands_kwargs["max_commands"] = args.commands_max_commands
                if args.commands_max_files is not None:
                    commands_kwargs["max_files"] = args.commands_max_files
                if args.json:
                    commands_report = get_commands_report(project_root or ".", **commands_kwargs)
                    payload_extra["projectCommands"] = commands_report
                    text = format_commands_report_text(commands_report)
                else:
                    text = get_commands_text(project_root or ".", **commands_kwargs)
            elif args.related_tests is not None:
                related_kwargs = {}
                if args.related_tests_max_paths is not None:
                    related_kwargs["max_paths"] = args.related_tests_max_paths
                if args.related_tests_max_candidates is not None:
                    related_kwargs["max_candidates"] = args.related_tests_max_candidates
                related_argument = shlex.join(args.related_tests) if args.related_tests else None
                if args.json:
                    related_report = get_related_tests_report(project_root or ".", argument=related_argument, **related_kwargs)
                    payload_extra["relatedTests"] = related_report
                    text = format_related_tests_report_text(related_report)
                else:
                    text = get_related_tests_text(project_root or ".", related_argument, **related_kwargs)
            elif args.focused_tests is not None:
                focused_kwargs = build_focused_tests_kwargs(args)
                focused_kwargs["argument"] = shlex.join(args.focused_tests) if args.focused_tests else None
                if args.json:
                    focused_report = get_focused_test_commands_report(project_root or ".", **focused_kwargs)
                    payload_extra["focusedTests"] = focused_report
                    text = format_focused_test_commands_report_text(focused_report)
                else:
                    text = get_focused_test_commands_text(project_root or ".", focused_kwargs.pop("argument"), **focused_kwargs)
            elif args.check_focused_tests is not None:
                focused_kwargs = build_focused_tests_kwargs(args)
                focused_kwargs["argument"] = shlex.join(args.check_focused_tests) if args.check_focused_tests else None
                if args.json:
                    check_focused_report = get_check_focused_test_commands_report(project_root or ".", **focused_kwargs)
                    payload_extra["checkFocusedTests"] = check_focused_report
                    text = format_check_focused_test_commands_report_text(check_focused_report)
                else:
                    text = get_check_focused_test_commands_text(project_root or ".", focused_kwargs.pop("argument"), **focused_kwargs)
            elif args.run_focused_tests is not None:
                focused_kwargs = build_focused_tests_kwargs(args)
                focused_kwargs.update(
                    {
                        "argument": shlex.join(args.run_focused_tests) if args.run_focused_tests else None,
                        "timeout_ms": args.run_timeout_ms,
                        "max_output_chars": args.run_max_chars,
                        "stop_on_failure": not args.run_continue_on_failure,
                        "extract_output_contexts": args.run_output_contexts,
                        "extract_output_diagnostics": args.run_output_diagnostics,
                        "context_lines": args.run_output_context_lines,
                        "max_diagnostics": args.run_output_diagnostic_max,
                        "max_contexts": args.run_output_context_max,
                        "max_bytes_per_context": args.run_output_context_max_bytes,
                    }
                )
                if args.json:
                    run_focused_report = get_run_focused_test_commands_report(project_root or ".", **focused_kwargs)
                    payload_extra["runFocusedTests"] = run_focused_report
                    text = format_run_focused_test_commands_report_text(run_focused_report)
                else:
                    focused_argument = focused_kwargs.pop("argument")
                    text = get_run_focused_test_commands_text(project_root or ".", focused_argument, **focused_kwargs)
            elif args.manifests:
                manifests_kwargs = {}
                if args.manifests_max_files is not None:
                    manifests_kwargs["max_files"] = args.manifests_max_files
                if args.manifests_max_items is not None:
                    manifests_kwargs["max_items"] = args.manifests_max_items
                if args.json:
                    manifests_report = get_manifests_report(project_root or ".", **manifests_kwargs)
                    payload_extra["manifests"] = manifests_report
                    text = format_manifests_report_text(manifests_report)
                else:
                    text = get_manifests_text(project_root or ".", **manifests_kwargs)
            elif args.instructions:
                instructions_kwargs = {}
                if args.instructions_max_files is not None:
                    instructions_kwargs["max_files"] = args.instructions_max_files
                if args.instructions_max_bytes is not None:
                    instructions_kwargs["max_bytes"] = args.instructions_max_bytes
                if args.json:
                    instructions_report = get_instructions_report(project_root or ".", **instructions_kwargs)
                    payload_extra["instructions"] = instructions_report
                    text = format_instructions_report_text(instructions_report)
                else:
                    text = get_instructions_text(project_root or ".", **instructions_kwargs)
            elif args.todos is not None:
                todos_kwargs = {}
                if args.todos_max_items is not None:
                    todos_kwargs["max_items"] = args.todos_max_items
                if args.todos_max_files is not None:
                    todos_kwargs["max_files"] = args.todos_max_files
                todos_argument = args.todos or None
                if args.json:
                    todos_report = get_todos_report(project_root or ".", path=todos_argument, **todos_kwargs)
                    payload_extra["todos"] = todos_report
                    text = format_todos_report_text(todos_report)
                else:
                    text = get_todos_text(project_root or ".", todos_argument, **todos_kwargs)
            elif args.command_check is not None:
                if args.json:
                    command_check_report = get_command_check_report(project_root or ".", args.command_check, args.command_cwd)
                    payload_extra["commandCheck"] = command_check_report
                    text = format_command_check_report_text(command_check_report)
                else:
                    text = get_command_check_text(project_root or ".", args.command_check, args.command_cwd)
            elif args.run_command is not None:
                run_kwargs = {
                    "command": args.run_command,
                    "cwd": args.run_cwd,
                    "timeout_ms": args.run_timeout_ms,
                    "max_output_chars": args.run_max_chars,
                    "extract_output_contexts": args.run_output_contexts,
                    "extract_output_diagnostics": args.run_output_diagnostics,
                    "context_lines": args.run_output_context_lines,
                    "max_diagnostics": args.run_output_diagnostic_max,
                    "max_contexts": args.run_output_context_max,
                    "max_bytes_per_context": args.run_output_context_max_bytes,
                }
                if args.json:
                    run_report = get_run_report(project_root or ".", **run_kwargs)
                    payload_extra["run"] = run_report
                    text = format_run_report_text(run_report)
                else:
                    text = get_run_text(project_root or ".", **run_kwargs)
            elif args.check_run_commands is not None:
                check_run_kwargs = {"commands": args.check_run_commands, "cwd": args.run_cwd}
                if args.json:
                    check_run_report = get_check_run_sequence_report(project_root or ".", **check_run_kwargs)
                    payload_extra["checkRunCommands"] = check_run_report
                    text = format_check_run_sequence_report_text(check_run_report)
                else:
                    text = get_check_run_sequence_text(project_root or ".", **check_run_kwargs)
            elif args.run_commands is not None:
                run_sequence_kwargs = {
                    "commands": args.run_commands,
                    "cwd": args.run_cwd,
                    "timeout_ms": args.run_timeout_ms,
                    "max_output_chars": args.run_max_chars,
                    "stop_on_failure": not args.run_continue_on_failure,
                    "extract_output_contexts": args.run_output_contexts,
                    "extract_output_diagnostics": args.run_output_diagnostics,
                    "context_lines": args.run_output_context_lines,
                    "max_diagnostics": args.run_output_diagnostic_max,
                    "max_contexts": args.run_output_context_max,
                    "max_bytes_per_context": args.run_output_context_max_bytes,
                }
                if args.json:
                    run_sequence_report = get_run_sequence_report(project_root or ".", **run_sequence_kwargs)
                    payload_extra["runCommands"] = run_sequence_report
                    text = format_run_sequence_report_text(run_sequence_report)
                else:
                    text = get_run_sequence_text(project_root or ".", **run_sequence_kwargs)
            elif args.check_start_command is not None:
                if args.json:
                    check_start_report = get_check_start_report(project_root or ".", args.check_start_command, cwd=args.start_cwd)
                    payload_extra["checkStartCommand"] = check_start_report
                    text = format_check_start_report_text(check_start_report)
                else:
                    text = get_check_start_text(project_root or ".", args.check_start_command, cwd=args.start_cwd)
            elif args.start_command is not None:
                if args.json:
                    start_report = get_start_report(project_root or ".", args.start_command, cwd=args.start_cwd)
                    payload_extra["startCommand"] = start_report
                    text = format_start_report_text(start_report)
                else:
                    text = get_start_text(project_root or ".", args.start_command, cwd=args.start_cwd)
            elif args.port_check is not None:
                port_kwargs = {"port": args.port_check, "host": args.port_host, "timeout_ms": args.port_timeout_ms}
                if args.json:
                    port_report = get_port_report(project_root or ".", **port_kwargs)
                    payload_extra["port"] = port_report
                    text = format_port_report_text(port_report)
                else:
                    text = get_port_text(project_root or ".", **port_kwargs)
            elif args.http_check is not None:
                http_kwargs = {
                    "url": args.http_check,
                    "contains": args.http_contains,
                    "timeout_ms": args.http_timeout_ms or 2_000,
                    "max_body_chars": args.http_max_body_chars or 2_000,
                    "regex": args.http_regex,
                }
                if args.json:
                    http_report = get_http_report(project_root or ".", **http_kwargs)
                    payload_extra["http"] = http_report
                    text = format_http_report_text(http_report)
                else:
                    text = get_http_text(project_root or ".", **http_kwargs)
            elif args.http_fetch is not None:
                http_fetch_kwargs = {
                    "url": args.http_fetch,
                    "timeout_ms": args.http_timeout_ms or 5_000,
                    "max_body_chars": args.http_max_body_chars or 12_000,
                }
                if args.json:
                    http_fetch_report = get_http_fetch_report(project_root or ".", **http_fetch_kwargs)
                    payload_extra["httpFetch"] = http_fetch_report
                    text = format_http_fetch_report_text(http_fetch_report)
                else:
                    text = get_http_fetch_text(project_root or ".", **http_fetch_kwargs)
            elif args.overview:
                overview_kwargs = {}
                if args.overview_max_files is not None:
                    overview_kwargs["max_files"] = args.overview_max_files
                if args.overview_max_commands is not None:
                    overview_kwargs["max_commands"] = args.overview_max_commands
                if args.overview_max_checks is not None:
                    overview_kwargs["max_checks"] = args.overview_max_checks
                if args.json:
                    overview_report = get_overview_report(project_root or ".", **overview_kwargs)
                    payload_extra["overview"] = overview_report
                    text = format_overview_report_text(overview_report)
                else:
                    text = get_overview_text(project_root or ".", **overview_kwargs)
            elif args.repo_map is not None:
                repo_map_kwargs = {}
                if args.repo_map_max_depth is not None:
                    repo_map_kwargs["max_depth"] = args.repo_map_max_depth
                if args.repo_map_max_files is not None:
                    repo_map_kwargs["max_files"] = args.repo_map_max_files
                if args.repo_map_max_symbols is not None:
                    repo_map_kwargs["max_symbols"] = args.repo_map_max_symbols
                if args.json:
                    repo_map_report = get_repo_map_report(project_root or ".", args.repo_map or None, **repo_map_kwargs)
                    payload_extra["repoMap"] = repo_map_report
                    text = format_repo_map_report_text(repo_map_report)
                else:
                    text = get_repo_map_text(project_root or ".", args.repo_map or None, **repo_map_kwargs)
            elif args.search is not None:
                search_kwargs = {}
                if args.search_max_matches is not None:
                    search_kwargs["max_matches"] = args.search_max_matches
                if args.search_regex:
                    search_kwargs["regex"] = True
                if args.search_ignore_case:
                    search_kwargs["case_sensitive"] = False
                if args.search_context_lines is not None:
                    search_kwargs["context_lines"] = args.search_context_lines
                if args.json:
                    search_report = get_search_report(project_root or ".", args.search, args.search_path, **search_kwargs)
                    payload_extra["search"] = search_report
                    text = format_search_report_text(search_report)
                else:
                    text = get_search_text(project_root or ".", args.search, args.search_path, **search_kwargs)
            elif args.search_contexts is not None:
                search_contexts_kwargs = {}
                if args.search_max_matches is not None:
                    search_contexts_kwargs["max_matches"] = args.search_max_matches
                if args.search_regex:
                    search_contexts_kwargs["regex"] = True
                if args.search_ignore_case:
                    search_contexts_kwargs["case_sensitive"] = False
                if args.search_context_lines is not None:
                    search_contexts_kwargs["context_lines"] = args.search_context_lines
                if args.search_context_max_bytes is not None:
                    search_contexts_kwargs["max_bytes_per_context"] = args.search_context_max_bytes
                if args.json:
                    search_contexts_report = get_search_contexts_report(project_root or ".", args.search_contexts, args.search_path, **search_contexts_kwargs)
                    payload_extra["searchContexts"] = search_contexts_report
                    text = format_search_contexts_report_text(search_contexts_report)
                else:
                    text = get_search_contexts_text(project_root or ".", args.search_contexts, args.search_path, **search_contexts_kwargs)
            elif args.find_files is not None:
                find_files_kwargs = {}
                if args.find_files_path:
                    find_files_kwargs["path"] = args.find_files_path
                if args.find_files_max_matches is not None:
                    find_files_kwargs["max_matches"] = args.find_files_max_matches
                if args.find_files_regex:
                    find_files_kwargs["regex"] = True
                if args.find_files_case_sensitive:
                    find_files_kwargs["case_sensitive"] = True
                if args.find_files_include_dirs:
                    find_files_kwargs["include_dirs"] = True
                if args.json:
                    find_files_report = get_find_files_report(project_root or ".", args.find_files, **find_files_kwargs)
                    payload_extra["findFiles"] = find_files_report
                    text = format_find_files_report_text(find_files_report)
                else:
                    text = get_find_files_text(project_root or ".", args.find_files, **find_files_kwargs)
            elif args.glob is not None:
                glob_kwargs = {}
                if args.glob_max_matches is not None:
                    glob_kwargs["max_matches"] = args.glob_max_matches
                if args.glob_include_dirs:
                    glob_kwargs["include_dirs"] = True
                if args.json:
                    glob_report = get_glob_report(project_root or ".", args.glob, **glob_kwargs)
                    payload_extra["glob"] = glob_report
                    text = format_glob_report_text(glob_report)
                else:
                    text = get_glob_text(project_root or ".", args.glob, **glob_kwargs)
            elif args.tree is not None:
                tree_kwargs = {}
                if args.tree_max_depth is not None:
                    tree_kwargs["max_depth"] = args.tree_max_depth
                if args.tree_max_entries is not None:
                    tree_kwargs["max_entries"] = args.tree_max_entries
                if args.json:
                    tree_report = get_tree_report(project_root or ".", args.tree or None, **tree_kwargs)
                    payload_extra["tree"] = tree_report
                    text = format_tree_report_text(tree_report)
                else:
                    text = get_tree_text(project_root or ".", args.tree or None, **tree_kwargs)
            elif args.symbols is not None:
                symbols_kwargs = {}
                if args.symbols_max is not None:
                    symbols_kwargs["max_symbols"] = args.symbols_max
                if args.json:
                    symbols_report = get_symbols_report(project_root or ".", args.symbols, **symbols_kwargs)
                    payload_extra["symbols"] = symbols_report
                    text = format_symbols_report_text(symbols_report)
                else:
                    text = get_symbols_text(project_root or ".", args.symbols, **symbols_kwargs)
            elif args.file_info is not None:
                if args.json:
                    file_info_report = get_file_info_report(project_root or ".", args.file_info)
                    payload_extra["fileInfo"] = file_info_report
                    text = format_file_info_report_text(file_info_report)
                else:
                    text = get_file_info_text(project_root or ".", args.file_info)
            elif args.image_info is not None:
                if args.json:
                    image_info_report = get_image_info_report(project_root or ".", args.image_info)
                    payload_extra["imageInfo"] = image_info_report
                    text = format_image_info_report_text(image_info_report)
                else:
                    text = get_image_info_text(project_root or ".", args.image_info)
            elif args.read is not None:
                read_kwargs = {}
                if args.read_max_bytes is not None:
                    read_kwargs["max_bytes"] = args.read_max_bytes
                if args.read_line_numbers:
                    read_kwargs["show_line_numbers"] = True
                if args.json:
                    read_report = get_read_report(project_root or ".", args.read, args.read_lines, **read_kwargs)
                    payload_extra["read"] = read_report
                    text = format_read_report_text(read_report)
                else:
                    text = get_read_text(project_root or ".", args.read, args.read_lines, **read_kwargs)
            elif args.around is not None:
                around_kwargs = {}
                if args.around_max_bytes is not None:
                    around_kwargs["max_bytes"] = args.around_max_bytes
                around_argument = f"{args.around[0]} {args.around[1]}"
                if args.json:
                    around_report = get_around_report(project_root or ".", around_argument, args.around_lines, **around_kwargs)
                    payload_extra["around"] = around_report
                    text = format_around_report_text(around_report)
                else:
                    text = get_around_text(project_root or ".", around_argument, args.around_lines, **around_kwargs)
            elif args.around_many is not None:
                around_many_kwargs = {}
                if args.around_many_max_bytes is not None:
                    around_many_kwargs["max_bytes_per_context"] = args.around_many_max_bytes
                if args.json:
                    around_many_report = get_around_many_report(project_root or ".", args.around_many, **around_many_kwargs)
                    payload_extra["aroundMany"] = around_many_report
                    text = format_around_many_report_text(around_many_report)
                else:
                    text = get_around_many_text(project_root or ".", args.around_many, **around_many_kwargs)
            elif args.output_contexts is not None:
                output_context_kwargs = {
                    "context_lines": args.output_context_lines,
                    "max_contexts": args.output_context_max,
                    "max_bytes_per_context": args.output_context_max_bytes,
                }
                if args.json:
                    output_contexts_report = get_output_contexts_report(project_root or ".", args.output_contexts, **output_context_kwargs)
                    payload_extra["outputContexts"] = output_contexts_report
                    text = format_output_contexts_report_text(output_contexts_report)
                else:
                    text = get_output_contexts_text(project_root or ".", args.output_contexts, **output_context_kwargs)
            elif args.output_diagnostics is not None:
                output_diagnostic_kwargs = {
                    "context_lines": args.output_diagnostic_lines,
                    "max_diagnostics": args.output_diagnostic_max,
                    "max_contexts": args.output_diagnostic_context_max,
                    "max_bytes_per_context": args.output_diagnostic_context_max_bytes,
                }
                if args.json:
                    output_diagnostics_report = get_output_diagnostics_report(project_root or ".", args.output_diagnostics, **output_diagnostic_kwargs)
                    payload_extra["outputDiagnostics"] = output_diagnostics_report
                    text = format_output_diagnostics_report_text(output_diagnostics_report)
                else:
                    text = get_output_diagnostics_text(project_root or ".", args.output_diagnostics, **output_diagnostic_kwargs)
            elif args.python_traceback is not None:
                python_traceback_kwargs = {
                    "context_lines": args.output_diagnostic_lines,
                    "max_diagnostics": args.output_diagnostic_max,
                    "max_contexts": args.output_diagnostic_context_max,
                    "max_bytes_per_context": args.output_diagnostic_context_max_bytes,
                }
                if args.json:
                    python_traceback_report = get_python_traceback_report(project_root or ".", args.python_traceback, **python_traceback_kwargs)
                    payload_extra["pythonTraceback"] = python_traceback_report
                    text = format_python_traceback_report_text(python_traceback_report)
                else:
                    text = get_python_traceback_text(project_root or ".", args.python_traceback, **python_traceback_kwargs)
            elif args.tail is not None:
                tail_kwargs = {}
                if args.tail_max_bytes is not None:
                    tail_kwargs["max_bytes"] = args.tail_max_bytes
                if args.json:
                    tail_report = get_tail_report(project_root or ".", args.tail, args.tail_lines, **tail_kwargs)
                    payload_extra["tail"] = tail_report
                    text = format_tail_report_text(tail_report)
                else:
                    text = get_tail_text(project_root or ".", args.tail, args.tail_lines, **tail_kwargs)
            elif args.read_files is not None:
                read_files_kwargs = {}
                if args.read_files_max_bytes is not None:
                    read_files_kwargs["max_bytes_per_file"] = args.read_files_max_bytes
                if args.read_files_line_numbers:
                    read_files_kwargs["show_line_numbers"] = True
                if args.json:
                    read_files_report = get_read_files_report(project_root or ".", args.read_files, **read_files_kwargs)
                    payload_extra["readFiles"] = read_files_report
                    text = format_read_files_report_text(read_files_report)
                else:
                    text = get_read_files_text(project_root or ".", args.read_files, **read_files_kwargs)
            elif args.read_ranges is not None:
                read_ranges_kwargs = {}
                if args.read_ranges_max_bytes is not None:
                    read_ranges_kwargs["max_bytes_per_range"] = args.read_ranges_max_bytes
                if args.json:
                    read_ranges_report = get_read_ranges_report(project_root or ".", args.read_ranges, **read_ranges_kwargs)
                    payload_extra["readRanges"] = read_ranges_report
                    text = format_read_ranges_report_text(read_ranges_report)
                else:
                    text = get_read_ranges_text(project_root or ".", args.read_ranges, **read_ranges_kwargs)
            elif args.python_check is not None:
                if args.json:
                    python_check_report = get_python_check_report(project_root or ".", args.python_check or None)
                    payload_extra["pythonCheck"] = python_check_report
                    text = format_python_check_report_text(python_check_report)
                else:
                    text = get_python_check_text(project_root or ".", args.python_check or None)
            elif args.python_deps is not None:
                if args.json:
                    python_deps_report = get_python_deps_report(project_root or ".", args.python_deps or None)
                    payload_extra["pythonDependencies"] = python_deps_report
                    text = format_python_deps_report_text(python_deps_report)
                else:
                    text = get_python_deps_text(project_root or ".", args.python_deps or None)
            elif args.python_defs is not None:
                python_kwargs = {}
                if args.python_max_matches is not None:
                    python_kwargs["max_matches"] = args.python_max_matches
                if args.python_def_max_lines is not None:
                    python_kwargs["max_lines"] = args.python_def_max_lines
                if args.json:
                    python_defs_report = get_python_defs_report(project_root or ".", symbol=args.python_defs, path=args.python_path, **python_kwargs)
                    payload_extra["pythonDefinitions"] = python_defs_report
                    text = format_python_defs_report_text(python_defs_report)
                else:
                    text = get_python_defs_text(project_root or ".", symbol=args.python_defs, path=args.python_path, **python_kwargs)
            elif args.python_refs is not None:
                python_kwargs = {}
                if args.python_max_matches is not None:
                    python_kwargs["max_matches"] = args.python_max_matches
                if args.json:
                    python_refs_report = get_python_refs_report(project_root or ".", symbol=args.python_refs, path=args.python_path, **python_kwargs)
                    payload_extra["pythonReferences"] = python_refs_report
                    text = format_python_refs_report_text(python_refs_report)
                else:
                    text = get_python_refs_text(project_root or ".", symbol=args.python_refs, path=args.python_path, **python_kwargs)
            elif args.python_ref_contexts is not None:
                python_kwargs = {}
                if args.python_max_matches is not None:
                    python_kwargs["max_matches"] = args.python_max_matches
                if args.python_context_lines is not None:
                    python_kwargs["context_lines"] = args.python_context_lines
                if args.python_context_max_bytes is not None:
                    python_kwargs["max_bytes_per_context"] = args.python_context_max_bytes
                if args.json:
                    python_ref_contexts_report = get_python_ref_contexts_report(project_root or ".", symbol=args.python_ref_contexts, path=args.python_path, **python_kwargs)
                    payload_extra["pythonReferenceContexts"] = python_ref_contexts_report
                    text = format_python_ref_contexts_report_text(python_ref_contexts_report)
                else:
                    text = get_python_ref_contexts_text(project_root or ".", symbol=args.python_ref_contexts, path=args.python_path, **python_kwargs)
            elif args.python_calls is not None:
                python_kwargs = {}
                if args.python_max_matches is not None:
                    python_kwargs["max_matches"] = args.python_max_matches
                if args.json:
                    python_calls_report = get_python_calls_report(project_root or ".", symbol=args.python_calls, path=args.python_path, **python_kwargs)
                    payload_extra["pythonCalls"] = python_calls_report
                    text = format_python_calls_report_text(python_calls_report)
                else:
                    text = get_python_calls_text(project_root or ".", symbol=args.python_calls, path=args.python_path, **python_kwargs)
            elif args.python_call_graph is not None:
                if args.json:
                    python_call_graph_report = get_python_call_graph_report(project_root or ".", args.python_call_graph or None)
                    payload_extra["pythonCallGraph"] = python_call_graph_report
                    text = format_python_call_graph_report_text(python_call_graph_report)
                else:
                    text = get_python_call_graph_text(project_root or ".", args.python_call_graph or None)
            elif args.python_rename_preview is not None:
                python_rename_kwargs = {
                    "symbol": args.python_rename_preview[0],
                    "new_name": args.python_rename_preview[1],
                    "path": args.python_path,
                }
                if args.json:
                    python_rename_report = get_python_rename_preview_report(project_root or ".", **python_rename_kwargs)
                    payload_extra["pythonRenamePreview"] = python_rename_report
                    text = format_python_rename_report_text("Python rename preview:", python_rename_report)
                else:
                    text = get_python_rename_preview_text(project_root or ".", **python_rename_kwargs)
            elif args.python_rename is not None:
                python_rename_kwargs = {
                    "symbol": args.python_rename[0],
                    "new_name": args.python_rename[1],
                    "path": args.python_path,
                }
                if args.json:
                    python_rename_report = get_python_rename_report(project_root or ".", **python_rename_kwargs)
                    payload_extra["pythonRename"] = python_rename_report
                    text = format_python_rename_report_text("Python rename:", python_rename_report)
                else:
                    text = get_python_rename_text(project_root or ".", **python_rename_kwargs)
            elif args.check_replace_python_def is not None:
                replace_definition_kwargs = {
                    "symbol": args.check_replace_python_def[0],
                    "content": args.check_replace_python_def[1],
                    "path": args.python_path,
                }
                if args.json:
                    replace_definition_report = get_check_replace_python_definition_report(project_root or ".", **replace_definition_kwargs)
                    payload_extra["checkReplacePythonDefinition"] = replace_definition_report
                    text = format_replace_python_definition_report_text("Check replace Python definition:", replace_definition_report)
                else:
                    text = get_check_replace_python_definition_text(project_root or ".", **replace_definition_kwargs)
            elif args.replace_python_def is not None:
                replace_definition_kwargs = {
                    "symbol": args.replace_python_def[0],
                    "content": args.replace_python_def[1],
                    "path": args.python_path,
                }
                if args.json:
                    replace_definition_report = get_replace_python_definition_report(project_root or ".", **replace_definition_kwargs)
                    payload_extra["replacePythonDefinition"] = replace_definition_report
                    text = format_replace_python_definition_report_text("Replace Python definition:", replace_definition_report)
                else:
                    text = get_replace_python_definition_text(project_root or ".", **replace_definition_kwargs)
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
            elif args.code_deps is not None:
                if args.json:
                    code_deps_report = get_code_deps_report(project_root or ".", args.code_deps or None)
                    payload_extra["codeDependencies"] = code_deps_report
                    text = format_code_deps_report_text(code_deps_report)
                else:
                    text = get_code_deps_text(project_root or ".", args.code_deps or None)
            elif args.code_refs is not None:
                code_kwargs = {}
                if args.code_max_matches is not None:
                    code_kwargs["max_matches"] = args.code_max_matches
                if args.json:
                    code_refs_report = get_code_refs_report(project_root or ".", symbol=args.code_refs, path=args.code_path, **code_kwargs)
                    payload_extra["codeReferences"] = code_refs_report
                    text = format_code_refs_report_text(code_refs_report)
                else:
                    text = get_code_refs_text(project_root or ".", symbol=args.code_refs, path=args.code_path, **code_kwargs)
            elif args.code_ref_contexts is not None:
                code_kwargs = {}
                if args.code_max_matches is not None:
                    code_kwargs["max_matches"] = args.code_max_matches
                if args.code_context_lines is not None:
                    code_kwargs["context_lines"] = args.code_context_lines
                if args.code_context_max_bytes is not None:
                    code_kwargs["max_bytes_per_context"] = args.code_context_max_bytes
                if args.json:
                    code_ref_contexts_report = get_code_ref_contexts_report(project_root or ".", symbol=args.code_ref_contexts, path=args.code_path, **code_kwargs)
                    payload_extra["codeReferenceContexts"] = code_ref_contexts_report
                    text = format_code_ref_contexts_report_text(code_ref_contexts_report)
                else:
                    text = get_code_ref_contexts_text(project_root or ".", symbol=args.code_ref_contexts, path=args.code_path, **code_kwargs)
            elif args.code_defs is not None:
                code_kwargs = {}
                if args.code_max_matches is not None:
                    code_kwargs["max_matches"] = args.code_max_matches
                if args.code_def_max_lines is not None:
                    code_kwargs["max_lines"] = args.code_def_max_lines
                if args.json:
                    code_defs_report = get_code_defs_report(project_root or ".", symbol=args.code_defs, path=args.code_path, **code_kwargs)
                    payload_extra["codeDefinitions"] = code_defs_report
                    text = format_code_defs_report_text(code_defs_report)
                else:
                    text = get_code_defs_text(project_root or ".", symbol=args.code_defs, path=args.code_path, **code_kwargs)
            elif args.code_rename_preview is not None:
                code_rename_kwargs = {
                    "symbol": args.code_rename_preview[0],
                    "new_name": args.code_rename_preview[1],
                    "path": args.code_path,
                }
                if args.json:
                    code_rename_report = get_code_rename_preview_report(project_root or ".", **code_rename_kwargs)
                    payload_extra["codeRenamePreview"] = code_rename_report
                    text = format_code_rename_report_text("Code rename preview:", code_rename_report)
                else:
                    text = get_code_rename_preview_text(project_root or ".", **code_rename_kwargs)
            elif args.code_rename is not None:
                code_rename_kwargs = {
                    "symbol": args.code_rename[0],
                    "new_name": args.code_rename[1],
                    "path": args.code_path,
                }
                if args.json:
                    code_rename_report = get_code_rename_report(project_root or ".", **code_rename_kwargs)
                    payload_extra["codeRename"] = code_rename_report
                    text = format_code_rename_report_text("Code rename:", code_rename_report)
                else:
                    text = get_code_rename_text(project_root or ".", **code_rename_kwargs)
            elif args.git_status:
                if args.json:
                    git_report = get_git_status_report(project_root or ".")
                    payload_extra["gitStatus"] = git_report
                    text = format_git_status_report_text(git_report)
                else:
                    text = get_git_status_text(project_root or ".")
            elif args.conflicts is not None:
                if args.json:
                    git_report = get_git_conflicts_report(project_root or ".", args.conflicts or None)
                    payload_extra["gitConflicts"] = git_report
                    text = format_git_conflicts_report_text(git_report)
                else:
                    text = get_git_conflicts_text(project_root or ".", args.conflicts or None)
            elif args.git_info:
                if args.json:
                    git_report = get_git_info_report(project_root or ".")
                    payload_extra["gitInfo"] = git_report
                    text = format_git_info_report_text(git_report)
                else:
                    text = get_git_info_text(project_root or ".")
            elif args.branches:
                if args.json:
                    branches_report = get_branches_report(project_root or ".")
                    payload_extra["branches"] = branches_report
                    text = format_branches_report_text(branches_report)
                else:
                    text = get_branches_text(project_root or ".")
            elif args.log is not None:
                if args.json:
                    log_report = get_log_report(project_root or ".", args.log or None, args.log_count)
                    payload_extra["log"] = log_report
                    text = format_log_report_text(log_report)
                else:
                    text = get_log_text(project_root or ".", args.log or None, args.log_count)
            elif args.show is not None:
                if args.json:
                    show_report = get_show_report(
                        project_root or ".",
                        rev=args.show or "HEAD",
                        path=args.show_path,
                        max_output_chars=args.show_max_chars,
                    )
                    payload_extra["show"] = show_report
                    text = format_show_report_text(show_report)
                else:
                    text = get_show_text(project_root or ".", rev=args.show or "HEAD", path=args.show_path, max_output_chars=args.show_max_chars)
            elif args.blame is not None:
                if args.json:
                    blame_report = get_blame_report(project_root or ".", args.blame, args.blame_lines, args.blame_max_chars)
                    payload_extra["blame"] = blame_report
                    text = format_blame_report_text(blame_report)
                else:
                    text = get_blame_text(project_root or ".", args.blame, args.blame_lines, args.blame_max_chars)
            elif args.stashes:
                if args.json:
                    stashes_report = get_stashes_report(project_root or ".", max_entries=args.stash_count)
                    payload_extra["stashes"] = stashes_report
                    text = format_stashes_report_text(stashes_report)
                else:
                    text = get_stashes_text(project_root or ".", max_entries=args.stash_count)
            elif args.check_git_fetch is not None:
                if args.json:
                    git_report = get_check_fetch_report(project_root or ".", args.check_git_fetch)
                    payload_extra["checkGitFetch"] = git_report
                    text = format_git_fetch_report_text("Check fetch", git_report)
                else:
                    text = get_check_fetch_text(project_root or ".", args.check_git_fetch)
            elif args.git_fetch is not None:
                if args.json:
                    git_report = get_fetch_report(project_root or ".", args.git_fetch)
                    payload_extra["gitFetch"] = git_report
                    text = format_git_fetch_report_text("Fetch", git_report)
                else:
                    text = get_fetch_text(project_root or ".", args.git_fetch)
            elif args.check_git_pull:
                if args.json:
                    git_report = get_check_pull_report(project_root or ".")
                    payload_extra["checkGitPull"] = git_report
                    text = format_git_sync_preview_report_text("Check pull", git_report)
                else:
                    text = get_check_pull_text(project_root or ".")
            elif args.git_pull:
                if args.json:
                    git_report = get_pull_report(project_root or ".")
                    payload_extra["gitPull"] = git_report
                    text = format_git_pull_report_text("Pull", git_report)
                else:
                    text = get_pull_text(project_root or ".")
            elif args.check_git_push:
                if args.json:
                    git_report = get_check_push_report(project_root or ".")
                    payload_extra["checkGitPush"] = git_report
                    text = format_git_sync_preview_report_text("Check push", git_report)
                else:
                    text = get_check_push_text(project_root or ".")
            elif args.git_push:
                if args.json:
                    git_report = get_push_report(project_root or ".")
                    payload_extra["gitPush"] = git_report
                    text = format_git_push_report_text("Push", git_report)
                else:
                    text = get_push_text(project_root or ".")
            elif args.check_git_stash is not None:
                stash_arg = build_stash_argument(args.check_git_stash, args.stash_include_untracked)
                if args.json:
                    git_report = get_check_stash_report(project_root or ".", stash_arg)
                    payload_extra["checkGitStash"] = git_report
                    text = format_git_stash_report_text("Check stash", git_report)
                else:
                    text = get_check_stash_text(project_root or ".", stash_arg)
            elif args.git_stash is not None:
                stash_arg = build_stash_argument(args.git_stash, args.stash_include_untracked)
                if args.json:
                    git_report = get_stash_report(project_root or ".", stash_arg)
                    payload_extra["gitStash"] = git_report
                    text = format_git_stash_report_text("Stash", git_report)
                else:
                    text = get_stash_text(project_root or ".", stash_arg)
            elif args.check_git_stash_apply is not None:
                if args.json:
                    git_report = get_check_stash_apply_report(project_root or ".", args.check_git_stash_apply)
                    payload_extra["checkGitStashApply"] = git_report
                    text = format_git_stash_apply_report_text("Check stash apply", git_report)
                else:
                    text = get_check_stash_apply_text(project_root or ".", args.check_git_stash_apply)
            elif args.git_stash_apply is not None:
                if args.json:
                    git_report = get_stash_apply_report(project_root or ".", args.git_stash_apply)
                    payload_extra["gitStashApply"] = git_report
                    text = format_git_stash_apply_report_text("Stash apply", git_report)
                else:
                    text = get_stash_apply_text(project_root or ".", args.git_stash_apply)
            elif args.check_git_stash_drop is not None:
                if args.json:
                    git_report = get_check_stash_drop_report(project_root or ".", args.check_git_stash_drop)
                    payload_extra["checkGitStashDrop"] = git_report
                    text = format_git_stash_drop_report_text("Check stash drop", git_report)
                else:
                    text = get_check_stash_drop_text(project_root or ".", args.check_git_stash_drop)
            elif args.git_stash_drop is not None:
                if args.json:
                    git_report = get_stash_drop_report(project_root or ".", args.git_stash_drop)
                    payload_extra["gitStashDrop"] = git_report
                    text = format_git_stash_drop_report_text("Stash drop", git_report)
                else:
                    text = get_stash_drop_text(project_root or ".", args.git_stash_drop)
            elif args.check_git_stage is not None:
                if args.json:
                    git_report = get_check_stage_report(project_root or ".", args.check_git_stage)
                    payload_extra["checkGitStage"] = git_report
                    text = format_git_index_report_text("Check stage", git_report)
                else:
                    text = get_check_stage_text(project_root or ".", args.check_git_stage)
            elif args.git_stage is not None:
                if args.json:
                    git_report = get_stage_report(project_root or ".", args.git_stage)
                    payload_extra["gitStage"] = git_report
                    text = format_git_index_report_text("Stage", git_report)
                else:
                    text = get_stage_text(project_root or ".", args.git_stage)
            elif args.check_git_unstage is not None:
                if args.json:
                    git_report = get_check_unstage_report(project_root or ".", args.check_git_unstage)
                    payload_extra["checkGitUnstage"] = git_report
                    text = format_git_index_report_text("Check unstage", git_report)
                else:
                    text = get_check_unstage_text(project_root or ".", args.check_git_unstage)
            elif args.git_unstage is not None:
                if args.json:
                    git_report = get_unstage_report(project_root or ".", args.git_unstage)
                    payload_extra["gitUnstage"] = git_report
                    text = format_git_index_report_text("Unstage", git_report)
                else:
                    text = get_unstage_text(project_root or ".", args.git_unstage)
            elif args.check_git_commit is not None:
                if args.json:
                    git_report = get_check_commit_report(project_root or ".", args.check_git_commit)
                    payload_extra["checkGitCommit"] = git_report
                    text = format_git_commit_report_text("Check commit", git_report)
                else:
                    text = get_check_commit_text(project_root or ".", args.check_git_commit)
            elif args.git_commit is not None:
                if args.json:
                    git_report = get_commit_report(project_root or ".", args.git_commit)
                    payload_extra["gitCommit"] = git_report
                    text = format_git_commit_report_text("Commit", git_report)
                else:
                    text = get_commit_text(project_root or ".", args.git_commit)
            elif args.check_git_restore is not None:
                if args.json:
                    git_report = get_check_restore_report(project_root or ".", args.check_git_restore)
                    payload_extra["checkGitRestore"] = git_report
                    text = format_git_restore_report_text("Check restore", git_report)
                else:
                    text = get_check_restore_text(project_root or ".", args.check_git_restore)
            elif args.git_restore is not None:
                if args.json:
                    git_report = get_restore_report(project_root or ".", args.git_restore)
                    payload_extra["gitRestore"] = git_report
                    text = format_git_restore_report_text("Restore", git_report)
                else:
                    text = get_restore_text(project_root or ".", args.git_restore)
            elif args.check_git_switch is not None:
                switch_arg = build_switch_argument(args.check_git_switch, args.git_switch_create)
                if args.json:
                    git_report = get_check_switch_report(project_root or ".", switch_arg)
                    payload_extra["checkGitSwitch"] = git_report
                    text = format_git_switch_report_text("Check switch", git_report)
                else:
                    text = get_check_switch_text(project_root or ".", switch_arg)
            elif args.git_switch is not None:
                switch_arg = build_switch_argument(args.git_switch, args.git_switch_create)
                if args.json:
                    git_report = get_switch_report(project_root or ".", switch_arg)
                    payload_extra["gitSwitch"] = git_report
                    text = format_git_switch_report_text("Switch", git_report)
                else:
                    text = get_switch_text(project_root or ".", switch_arg)
            elif args.env:
                if args.json:
                    env_report = get_env_report(project_root or ".")
                    payload_extra["env"] = env_report
                    text = format_env_report_text(env_report)
                else:
                    text = get_env_text(project_root or ".")
            elif args.processes:
                if args.json:
                    processes_report = get_processes_report(project_root or ".")
                    payload_extra["processes"] = processes_report
                    text = format_processes_report_text(processes_report)
                else:
                    text = get_processes_text(project_root or ".")
            elif args.process_output is not None:
                process_kwargs = {"process_id": args.process_output, "max_output_chars": args.process_max_chars}
                if args.json:
                    process_report = get_process_report(project_root or ".", **process_kwargs)
                    payload_extra["process"] = process_report
                    text = format_process_report_text(process_report)
                else:
                    text = get_process_text(project_root or ".", **process_kwargs)
            elif args.process_output_contexts is not None:
                process_context_kwargs = {
                    "process_id": args.process_output_contexts,
                    "max_output_chars": args.process_max_chars,
                    "context_lines": args.process_output_context_lines,
                    "max_contexts": args.process_output_context_max,
                    "max_bytes_per_context": args.process_output_context_max_bytes,
                }
                if args.json:
                    process_contexts_report = get_process_output_contexts_report(project_root or ".", **process_context_kwargs)
                    payload_extra["processOutputContexts"] = process_contexts_report
                    text = format_process_output_contexts_report_text(process_contexts_report)
                else:
                    text = get_process_output_contexts_text(project_root or ".", **process_context_kwargs)
            elif args.process_output_diagnostics is not None:
                process_diagnostic_kwargs = {
                    "process_id": args.process_output_diagnostics,
                    "max_output_chars": args.process_max_chars,
                    "context_lines": args.process_output_context_lines,
                    "max_diagnostics": args.process_output_diagnostic_max,
                    "max_contexts": args.process_output_context_max,
                    "max_bytes_per_context": args.process_output_context_max_bytes,
                }
                if args.json:
                    process_diagnostics_report = get_process_output_diagnostics_report(project_root or ".", **process_diagnostic_kwargs)
                    payload_extra["processOutputDiagnostics"] = process_diagnostics_report
                    text = format_process_output_diagnostics_report_text(process_diagnostics_report)
                else:
                    text = get_process_output_diagnostics_text(project_root or ".", **process_diagnostic_kwargs)
            elif args.wait_process is not None:
                wait_process_kwargs = {
                    "process_id": args.wait_process,
                    "timeout_ms": args.wait_timeout_ms,
                    "max_output_chars": args.wait_max_chars,
                    "stdout_contains": args.wait_stdout,
                    "stderr_contains": args.wait_stderr,
                    "regex": args.wait_regex,
                }
                if args.json:
                    wait_process_report = get_wait_process_report(project_root or ".", **wait_process_kwargs)
                    payload_extra["waitProcess"] = wait_process_report
                    text = format_wait_process_report_text(wait_process_report)
                else:
                    text = get_wait_process_text(project_root or ".", **wait_process_kwargs)
            elif args.check_write_process is not None:
                write_kwargs = {"process_id": args.check_write_process, "content": args.write_stdin}
                if args.json:
                    check_write_process_report = get_check_write_process_report(project_root or ".", **write_kwargs)
                    payload_extra["checkWriteProcess"] = check_write_process_report
                    text = format_check_write_process_report_text(check_write_process_report)
                else:
                    text = get_check_write_process_text(project_root or ".", **write_kwargs)
            elif args.write_process is not None:
                write_kwargs = {"process_id": args.write_process, "content": args.write_stdin}
                if args.json:
                    write_process_report = get_write_process_report(project_root or ".", **write_kwargs)
                    payload_extra["writeProcess"] = write_process_report
                    text = format_write_process_report_text(write_process_report)
                else:
                    text = get_write_process_text(project_root or ".", **write_kwargs)
            elif args.check_stop_process is not None:
                if args.json:
                    check_stop_process_report = get_check_stop_process_report(project_root or ".", args.check_stop_process)
                    payload_extra["checkStopProcess"] = check_stop_process_report
                    text = format_check_stop_process_report_text(check_stop_process_report)
                else:
                    text = get_check_stop_process_text(project_root or ".", args.check_stop_process)
            elif args.stop_process is not None:
                if args.json:
                    stop_process_report = get_stop_process_report(project_root or ".", args.stop_process)
                    payload_extra["stopProcess"] = stop_process_report
                    text = format_stop_process_report_text(stop_process_report)
                else:
                    text = get_stop_process_text(project_root or ".", args.stop_process)
            elif args.check_stop_all_processes:
                if args.json:
                    check_stop_all_report = get_check_stop_all_processes_report(project_root or ".")
                    payload_extra["checkStopAllProcesses"] = check_stop_all_report
                    text = format_check_stop_all_processes_report_text(check_stop_all_report)
                else:
                    text = get_check_stop_all_processes_text(project_root or ".")
            elif args.stop_all_processes:
                if args.json:
                    stop_all_report = get_stop_all_processes_report(project_root or ".")
                    payload_extra["stopAllProcesses"] = stop_all_report
                    text = format_stop_all_processes_report_text(stop_all_report)
                else:
                    text = get_stop_all_processes_text(project_root or ".")
            elif args.status:
                if args.json:
                    status_report = get_status_report("code", args.approval, None, chat_turns=0)
                    payload_extra["runtimeStatus"] = status_report
                    text = format_status_report_text(status_report)
                else:
                    text = get_status_text("code", args.approval, None, chat_turns=0)
            elif args.context:
                if args.json:
                    context_report = get_context_report(project_root or ".")
                    payload_extra["context"] = context_report
                    text = format_context_report_text(context_report)
                else:
                    text = get_context_text(project_root or ".")
            elif args.init is not None:
                if args.json:
                    init_report = get_init_report(project_root or ".", args.init)
                    payload_extra["init"] = init_report
                    text = format_init_report_text(init_report)
                else:
                    text = init_project_instructions(project_root or ".", args.init)
            elif args.doctor:
                if args.json:
                    doctor_report = get_doctor_report(project_root or ".", provider_env)
                    payload_extra["doctor"] = doctor_report
                    text = format_doctor_report_text(doctor_report)
                else:
                    text = get_doctor_text(project_root or ".", provider_env)
            elif args.review:
                review_report = get_review_report(
                    project_root or ".",
                    max_files=args.review_max_files,
                    max_checks=args.review_max_checks,
                )
                payload_extra["review"] = review_report
                text = format_review_report_text(review_report)
            elif args.handoff:
                handoff_report = get_handoff_report(
                    project_root or ".",
                    max_files=args.handoff_max_files,
                    max_checks=args.handoff_max_checks,
                    max_status_chars=args.handoff_max_status_chars,
                    max_plan_chars=args.handoff_max_plan_chars,
                )
                payload_extra["handoff"] = handoff_report
                text = format_handoff_report_text(handoff_report)
            elif args.changes:
                changes_report = get_changes_report(project_root or ".", max_files=args.changes_max_files)
                payload_extra["changes"] = changes_report
                text = format_changes_report_text(changes_report)
            elif args.diff is not None:
                if args.json:
                    diff_report = get_diff_report(project_root or ".", args.diff or None, max_chars=args.diff_max_chars)
                    payload_extra["diff"] = diff_report
                    text = format_diff_report_text(diff_report)
                else:
                    text = get_diff_text(project_root or ".", args.diff or None, max_chars=args.diff_max_chars)
            elif args.diff_hunks is not None:
                if args.json:
                    diff_report = get_diff_hunks_report(
                        project_root or ".",
                        args.diff_hunks or None,
                        max_hunks=args.diff_hunks_max_hunks,
                        max_lines_per_hunk=args.diff_hunks_max_lines,
                    )
                    payload_extra["diffHunks"] = diff_report
                    text = format_diff_hunks_report_text(diff_report)
                else:
                    text = get_diff_hunks_text(
                        project_root or ".",
                        args.diff_hunks or None,
                        max_hunks=args.diff_hunks_max_hunks,
                        max_lines_per_hunk=args.diff_hunks_max_lines,
                    )
            elif args.diff_contexts is not None:
                if args.json:
                    diff_report = get_diff_contexts_report(
                        project_root or ".",
                        args.diff_contexts or None,
                        context_lines=args.diff_context_lines,
                        max_hunks=args.diff_contexts_max_hunks,
                        max_bytes_per_context=args.diff_contexts_max_bytes,
                    )
                    payload_extra["diffContexts"] = diff_report
                    text = format_diff_contexts_report_text(diff_report)
                else:
                    text = get_diff_contexts_text(
                        project_root or ".",
                        args.diff_contexts or None,
                        context_lines=args.diff_context_lines,
                        max_hunks=args.diff_contexts_max_hunks,
                        max_bytes_per_context=args.diff_contexts_max_bytes,
                    )
            elif args.sessions:
                if args.json:
                    sessions_report = get_sessions_report(project_root or ".")
                    payload_extra["sessions"] = sessions_report
                    text = format_sessions_report_text(sessions_report)
                else:
                    text = get_sessions_text(project_root or ".")
            elif args.last:
                if args.json:
                    session_report = get_last_session_report(project_root or ".")
                    payload_extra["sessionSummary"] = session_report
                    text = format_session_summary_report_text(session_report)
                else:
                    text = get_last_session_text(project_root or ".")
            elif args.session is not None:
                if args.json:
                    session_report = get_session_report(args.session, project_root or ".")
                    payload_extra["sessionSummary"] = session_report
                    text = format_session_summary_report_text(session_report)
                else:
                    text = get_session_text(args.session, project_root or ".")
            elif args.plan is not None:
                if args.json:
                    plan_report = get_plan_report(project_root or ".", args.plan or None)
                    payload_extra["sessionPlan"] = plan_report
                    text = format_session_plan_report_text(plan_report)
                else:
                    text = get_plan_text(project_root or ".", args.plan or None)
            elif args.transcript is not None:
                session_kwargs = {}
                if args.session_transcript_event_max is not None:
                    session_kwargs["max_events"] = args.session_transcript_event_max
                if args.session_max_text is not None:
                    session_kwargs["max_text"] = args.session_max_text
                if args.json:
                    transcript_report = get_transcript_report(project_root or ".", args.transcript or None, **session_kwargs)
                    payload_extra["sessionTranscript"] = transcript_report
                    text = format_session_transcript_report_text(transcript_report)
                else:
                    text = get_transcript_text(project_root or ".", args.transcript or None, **session_kwargs)
            elif args.session_search is not None:
                session_kwargs = {}
                if args.session_search_match_max is not None:
                    session_kwargs["max_matches"] = args.session_search_match_max
                if args.session_max_text is not None:
                    session_kwargs["max_text"] = args.session_max_text
                if args.session_search_case_sensitive:
                    session_kwargs["case_sensitive"] = True
                if args.json:
                    session_search_report = get_session_search_report(project_root or ".", args.session_search, args.session_search_run, **session_kwargs)
                    payload_extra["sessionSearch"] = session_search_report
                    text = format_session_search_report_text(session_search_report)
                else:
                    text = get_session_search_text(project_root or ".", args.session_search, args.session_search_run, **session_kwargs)
            elif args.session_commands is not None:
                session_kwargs = {}
                if args.session_max_commands is not None:
                    session_kwargs["max_commands"] = args.session_max_commands
                if args.session_max_output_chars is not None:
                    session_kwargs["max_output_chars"] = args.session_max_output_chars
                if args.json:
                    session_commands_report = get_session_commands_report(project_root or ".", args.session_commands or None, **session_kwargs)
                    payload_extra["sessionCommands"] = session_commands_report
                    text = format_session_commands_report_text(session_commands_report)
                else:
                    text = get_session_commands_text(project_root or ".", args.session_commands or None, **session_kwargs)
            elif args.session_output_contexts is not None:
                session_kwargs = {
                    "max_commands": args.session_output_command_max,
                    "max_output_chars": args.session_output_max_chars,
                    "context_lines": args.session_output_context_lines,
                    "max_contexts": args.session_output_context_max,
                    "max_bytes_per_context": args.session_output_context_max_bytes,
                }
                if args.json:
                    session_output_contexts_report = get_session_output_contexts_report(project_root or ".", args.session_output_contexts or None, **session_kwargs)
                    payload_extra["sessionOutputContexts"] = session_output_contexts_report
                    text = format_session_output_contexts_report_text(session_output_contexts_report)
                else:
                    text = get_session_output_contexts_text(project_root or ".", args.session_output_contexts or None, **session_kwargs)
            elif args.session_output_diagnostics is not None:
                session_kwargs = {
                    "max_commands": args.session_output_command_max,
                    "max_output_chars": args.session_output_max_chars,
                    "context_lines": args.session_output_context_lines,
                    "max_diagnostics": args.session_output_diagnostic_max,
                    "max_contexts": args.session_output_context_max,
                    "max_bytes_per_context": args.session_output_context_max_bytes,
                }
                if args.json:
                    session_output_diagnostics_report = get_session_output_diagnostics_report(
                        project_root or ".",
                        args.session_output_diagnostics or None,
                        **session_kwargs,
                    )
                    payload_extra["sessionOutputDiagnostics"] = session_output_diagnostics_report
                    text = format_session_output_diagnostics_report_text(session_output_diagnostics_report)
                else:
                    text = get_session_output_diagnostics_text(project_root or ".", args.session_output_diagnostics or None, **session_kwargs)
            elif args.session_files is not None:
                session_kwargs = {}
                if args.session_max_files is not None:
                    session_kwargs["max_files"] = args.session_max_files
                if args.json:
                    session_files_report = get_session_files_report(project_root or ".", args.session_files or None, **session_kwargs)
                    payload_extra["sessionFiles"] = session_files_report
                    text = format_session_files_report_text(session_files_report)
                else:
                    text = get_session_files_text(project_root or ".", args.session_files or None, **session_kwargs)
            elif args.session_failures is not None:
                session_kwargs = {}
                if args.session_max_failures is not None:
                    session_kwargs["max_failures"] = args.session_max_failures
                if args.session_max_text is not None:
                    session_kwargs["max_text"] = args.session_max_text
                if args.json:
                    session_failures_report = get_session_failures_report(project_root or ".", args.session_failures or None, **session_kwargs)
                    payload_extra["sessionFailures"] = session_failures_report
                    text = format_session_failures_report_text(session_failures_report)
                else:
                    text = get_session_failures_text(project_root or ".", args.session_failures or None, **session_kwargs)
            elif args.session_verification is not None:
                session_kwargs = {}
                if args.session_max_checks is not None:
                    session_kwargs["max_checks"] = args.session_max_checks
                if args.json:
                    session_verification_report = get_session_verification_report(project_root or ".", args.session_verification or None, **session_kwargs)
                    payload_extra["sessionVerification"] = session_verification_report
                    text = format_session_verification_report_text(session_verification_report)
                else:
                    text = get_session_verification_text(project_root or ".", args.session_verification or None, **session_kwargs)
            elif args.session_audit is not None:
                session_kwargs = {}
                if args.session_max_failures is not None:
                    session_kwargs["max_failures"] = args.session_max_failures
                if args.session_max_files is not None:
                    session_kwargs["max_files"] = args.session_max_files
                if args.session_max_commands is not None:
                    session_kwargs["max_commands"] = args.session_max_commands
                if args.session_max_checks is not None:
                    session_kwargs["max_checks"] = args.session_max_checks
                if args.session_max_text is not None:
                    session_kwargs["max_text"] = args.session_max_text
                if args.json:
                    session_audit_report = get_session_audit_report(project_root or ".", args.session_audit or None, **session_kwargs)
                    payload_extra["sessionAudit"] = session_audit_report
                    text = format_session_audit_report_text(session_audit_report)
                else:
                    text = get_session_audit_text(project_root or ".", args.session_audit or None, **session_kwargs)
            elif args.session_handoff is not None:
                session_kwargs = {}
                if args.session_max_failures is not None:
                    session_kwargs["max_failures"] = args.session_max_failures
                if args.session_max_files is not None:
                    session_kwargs["max_files"] = args.session_max_files
                if args.session_max_commands is not None:
                    session_kwargs["max_commands"] = args.session_max_commands
                if args.session_max_checks is not None:
                    session_kwargs["max_checks"] = args.session_max_checks
                if args.session_max_output_chars is not None:
                    session_kwargs["max_output_chars"] = args.session_max_output_chars
                if args.session_max_text is not None:
                    session_kwargs["max_text"] = args.session_max_text
                if args.json:
                    session_handoff_report = get_session_handoff_report(project_root or ".", args.session_handoff or None, **session_kwargs)
                    payload_extra["sessionHandoff"] = session_handoff_report
                    text = format_session_handoff_report_text(session_handoff_report)
                else:
                    text = get_session_handoff_text(project_root or ".", args.session_handoff or None, **session_kwargs)
            elif args.checkpoint is not None:
                if args.json:
                    checkpoint_report = get_checkpoint_report(project_root or ".", args.checkpoint or None)
                    payload_extra["checkpoint"] = checkpoint_report
                    text = format_checkpoint_create_report_text(checkpoint_report)
                else:
                    text = get_checkpoint_text(project_root or ".", args.checkpoint or None)
            elif args.checkpoints:
                if args.json:
                    checkpoints_report = get_checkpoints_report(project_root or ".")
                    payload_extra["checkpoints"] = checkpoints_report
                    text = format_checkpoints_report_text(checkpoints_report)
                else:
                    text = get_checkpoints_text(project_root or ".")
            elif args.checkpoint_show is not None:
                if args.json:
                    checkpoint_report = get_checkpoint_show_report(args.checkpoint_show, project_root or ".")
                    payload_extra["checkpointShow"] = checkpoint_report
                    text = format_checkpoint_show_report_text(checkpoint_report)
                else:
                    text = get_checkpoint_show_text(args.checkpoint_show, project_root or ".")
            elif args.checkpoint_diff is not None:
                if args.json:
                    checkpoint_report = get_checkpoint_diff_report(args.checkpoint_diff, project_root or ".")
                    payload_extra["checkpointDiff"] = checkpoint_report
                    text = format_checkpoint_diff_report_text(checkpoint_report)
                else:
                    text = get_checkpoint_diff_text(args.checkpoint_diff, project_root or ".")
            elif args.checkpoint_status is not None:
                if args.json:
                    checkpoint_report = get_checkpoint_status_report(args.checkpoint_status, project_root or ".")
                    payload_extra["checkpointStatus"] = checkpoint_report
                    text = format_checkpoint_status_report_text(checkpoint_report)
                else:
                    text = get_checkpoint_status_text(args.checkpoint_status, project_root or ".")
            elif args.check_checkpoint_restore is not None:
                if args.json:
                    checkpoint_report = get_check_checkpoint_restore_report(args.check_checkpoint_restore, project_root or ".")
                    payload_extra["checkCheckpointRestore"] = checkpoint_report
                    text = format_check_checkpoint_restore_report_text(checkpoint_report)
                else:
                    text = get_check_checkpoint_restore_text(args.check_checkpoint_restore, project_root or ".")
            elif args.checkpoint_restore is not None:
                if args.json:
                    checkpoint_report = get_checkpoint_restore_report(args.checkpoint_restore, project_root or ".")
                    payload_extra["checkpointRestore"] = checkpoint_report
                    text = format_checkpoint_restore_report_text(checkpoint_report)
                else:
                    text = get_checkpoint_restore_text(args.checkpoint_restore, project_root or ".")
            elif args.check_checkpoint_delete is not None:
                if args.json:
                    checkpoint_report = get_check_checkpoint_delete_report(args.check_checkpoint_delete, project_root or ".")
                    payload_extra["checkCheckpointDelete"] = checkpoint_report
                    text = format_check_checkpoint_delete_report_text(checkpoint_report)
                else:
                    text = get_check_checkpoint_delete_text(args.check_checkpoint_delete, project_root or ".")
            elif args.checkpoint_delete is not None:
                if args.json:
                    checkpoint_report = get_checkpoint_delete_report(args.checkpoint_delete, project_root or ".")
                    payload_extra["checkpointDelete"] = checkpoint_report
                    text = format_checkpoint_delete_report_text(checkpoint_report)
                else:
                    text = get_checkpoint_delete_text(args.checkpoint_delete, project_root or ".")
            elif args.check_checkpoint_prune is not None:
                if args.json:
                    checkpoint_report = get_check_checkpoint_prune_report(args.check_checkpoint_prune, project_root or ".")
                    payload_extra["checkCheckpointPrune"] = checkpoint_report
                    text = format_check_checkpoint_prune_report_text(checkpoint_report)
                else:
                    text = get_check_checkpoint_prune_text(args.check_checkpoint_prune, project_root or ".")
            elif args.checkpoint_prune is not None:
                if args.json:
                    checkpoint_report = get_checkpoint_prune_report(args.checkpoint_prune, project_root or ".")
                    payload_extra["checkpointPrune"] = checkpoint_report
                    text = format_checkpoint_prune_report_text(checkpoint_report)
                else:
                    text = get_checkpoint_prune_text(args.checkpoint_prune, project_root or ".")
            elif args.usage:
                if args.json:
                    usage_report = get_usage_report(project_root or ".")
                    payload_extra["usage"] = usage_report
                    text = format_usage_report_text(usage_report)
                else:
                    text = get_usage_text(project_root or ".")
            elif args.cost:
                if args.json:
                    cost_report = get_cost_report(project_root or ".")
                    payload_extra["cost"] = cost_report
                    text = format_cost_report_text(cost_report)
                else:
                    text = get_cost_text(project_root or ".")
            else:
                text = ""
        exit_code = local_result_exit_code(args, text)
        payload = {"kind": "local", "success": exit_code == 0, "text": text}
        payload.update(payload_extra)
        if exit_code != 0:
            payload["status"] = "failed"
        print_output(payload, args.json)
        return exit_code
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
        if command and command.type == "help":
            print(get_help_text())
            continue
        if command and command.type == "model":
            print(get_model_text())
            continue
        if command and command.type == "config":
            print(get_config_text())
            continue
        if command and command.type == "tools":
            print(get_tools_text())
            continue
        if command and command.type == "tool":
            print(get_tool_text(command.argument))
            continue
        if command and command.type == "permissions":
            print(get_permissions_text(approval_policy))
            continue
        if command and command.type == "checks":
            kwargs, error, uses_named_options = parse_interactive_option_limit_argument(
                command.argument,
                "Usage: /checks [--max-checks N]",
                {"--max-checks": "max_checks"},
            )
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_checks_text(**kwargs))
            else:
                print(get_checks_text())
            continue
        if command and command.type == "check_suggested_checks":
            if command.argument and command.argument.strip().startswith("--"):
                kwargs, error, uses_named_options = parse_interactive_option_limit_argument(
                    command.argument,
                    "Usage: /check-suggested-checks [--max-checks N]",
                    {"--max-checks": "max_checks"},
                )
                if error:
                    print(error)
                    continue
                if uses_named_options:
                    print(get_check_suggested_checks_text(**kwargs))
                    continue
            print(get_check_suggested_checks_text(argument=command.argument))
            continue
        if command and command.type == "run_suggested_checks":
            suggested_argument, kwargs, error, uses_named_options = parse_interactive_run_suggested_checks_argument(command.argument)
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_run_suggested_checks_text(argument=suggested_argument, **kwargs))
            else:
                print(get_run_suggested_checks_text(argument=command.argument))
            continue
        if command and command.type == "commands":
            kwargs, error, uses_named_options = parse_interactive_commands_argument(command.argument)
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_commands_text(**kwargs))
            else:
                print(get_commands_text())
            continue
        if command and command.type == "related_tests":
            related_argument, kwargs, error, uses_named_options = parse_interactive_test_paths_argument(
                command.argument,
                "Usage: /related-tests [--max-paths N] [--max-candidates N] -- [path...]",
            )
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_related_tests_text(argument=related_argument, **kwargs))
            else:
                print(get_related_tests_text(argument=command.argument))
            continue
        if command and command.type == "focused_test_commands":
            focused_argument, kwargs, error, uses_named_options = parse_interactive_test_paths_argument(
                command.argument,
                "Usage: /focused-tests [--max-paths N] [--max-candidates N] [--max-commands N] -- [path...]",
                include_max_commands=True,
            )
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_focused_test_commands_text(argument=focused_argument, **kwargs))
            else:
                print(get_focused_test_commands_text(argument=command.argument))
            continue
        if command and command.type == "check_focused_test_commands":
            focused_argument, kwargs, error, uses_named_options = parse_interactive_test_paths_argument(
                command.argument,
                "Usage: /check-focused-tests [--max-paths N] [--max-candidates N] [--max-commands N] -- [path...]",
                include_max_commands=True,
            )
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_check_focused_test_commands_text(argument=focused_argument, **kwargs))
            else:
                print(get_check_focused_test_commands_text(argument=command.argument))
            continue
        if command and command.type == "run_focused_test_commands":
            focused_argument, kwargs, error, uses_named_options = parse_interactive_run_focused_tests_argument(command.argument)
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_run_focused_test_commands_text(argument=focused_argument, **kwargs))
            else:
                print(
                    get_run_focused_test_commands_text(
                        argument=command.argument,
                        timeout_ms=30_000,
                        max_output_chars=12_000,
                    )
                )
            continue
        if command and command.type == "manifests":
            kwargs, error, uses_named_options = parse_interactive_manifests_argument(command.argument)
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_manifests_text(**kwargs))
            else:
                print(get_manifests_text())
            continue
        if command and command.type == "instructions":
            kwargs, error, uses_named_options = parse_interactive_instructions_argument(command.argument)
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_instructions_text(**kwargs))
            else:
                print(get_instructions_text())
            continue
        if command and command.type == "todos":
            path, kwargs, error, uses_named_options = parse_interactive_todos_argument(command.argument)
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_todos_text(path=path, **kwargs))
            else:
                print(get_todos_text(path=command.argument))
            continue
        if command and command.type == "command":
            checked_command, cwd, error, uses_named_options = parse_interactive_cwd_command_argument(
                command.argument,
                "Usage: /command [--cwd PATH] -- <cmd>",
            )
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_command_check_text(command=checked_command, cwd=cwd))
            else:
                print(get_command_check_text(command=command.argument))
            continue
        if command and command.type == "run":
            run_command, kwargs, error, uses_named_options = parse_interactive_run_argument(command.argument)
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_run_text(command=run_command, **kwargs))
            else:
                print(get_run_text(command=command.argument))
            continue
        if command and command.type == "run_sequence":
            run_commands, kwargs, error, uses_named_options = parse_interactive_run_sequence_argument(command.argument)
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_run_sequence_text(commands=run_commands, **kwargs))
            else:
                print(get_run_sequence_text(argument=command.argument))
            continue
        if command and command.type == "check_run_sequence":
            run_commands, cwd, error, uses_named_options = parse_interactive_check_run_sequence_argument(command.argument)
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_check_run_sequence_text(commands=run_commands, cwd=cwd))
            else:
                print(get_check_run_sequence_text(argument=command.argument))
            continue
        if command and command.type == "check_start":
            checked_command, cwd, error, uses_named_options = parse_interactive_cwd_command_argument(
                command.argument,
                "Usage: /check-start [--cwd PATH] -- <cmd>",
            )
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_check_start_text(command=checked_command, cwd=cwd))
            else:
                print(get_check_start_text(command=command.argument))
            continue
        if command and command.type == "start":
            start_command, cwd, error, uses_named_options = parse_interactive_cwd_command_argument(
                command.argument,
                "Usage: /start [--cwd PATH] -- <cmd>",
            )
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_start_text(command=start_command, cwd=cwd))
            else:
                print(get_start_text(command=command.argument))
            continue
        if command and command.type == "port":
            port, kwargs, error, uses_named_options = parse_interactive_port_argument(command.argument)
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_port_text(port=port, **kwargs))
            else:
                print(get_port_text(argument=command.argument))
            continue
        if command and command.type == "http":
            http_url, kwargs, error, uses_named_options = parse_interactive_http_argument(command.argument)
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_http_text(url=http_url, **kwargs))
            else:
                print(get_http_text(argument=command.argument))
            continue
        if command and command.type == "http_fetch":
            http_url, kwargs, error, uses_named_options = parse_interactive_http_fetch_argument(command.argument)
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_http_fetch_text(url=http_url, **kwargs))
            else:
                print(get_http_fetch_text(argument=command.argument))
            continue
        if command and command.type == "overview":
            kwargs, error, uses_named_options = parse_interactive_overview_argument(command.argument)
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_overview_text(**kwargs))
            else:
                print(get_overview_text())
            continue
        if command and command.type == "repo_map":
            repo_map_path, kwargs, error, uses_named_options = parse_interactive_repo_map_argument(command.argument)
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_repo_map_text(path=repo_map_path, **kwargs))
            else:
                print(get_repo_map_text(path=command.argument))
            continue
        if command and command.type == "search":
            search_query, kwargs, error, uses_named_options = parse_interactive_search_argument(
                command.argument,
                include_max_bytes=False,
            )
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_search_text(query=search_query, **kwargs))
            else:
                print(get_search_text(query=command.argument))
            continue
        if command and command.type == "search_contexts":
            search_query, kwargs, error, uses_named_options = parse_interactive_search_argument(
                command.argument,
                include_max_bytes=True,
            )
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_search_contexts_text(query=search_query, **kwargs))
            else:
                print(get_search_contexts_text(query=command.argument))
            continue
        if command and command.type == "find_files":
            file_query, kwargs, error, uses_named_options = parse_interactive_find_files_argument(command.argument)
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_find_files_text(query=file_query, **kwargs))
            else:
                print(get_find_files_text(query=command.argument))
            continue
        if command and command.type == "glob":
            glob_pattern, kwargs, error, uses_named_options = parse_interactive_glob_argument(command.argument)
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_glob_text(pattern=glob_pattern, **kwargs))
            else:
                print(get_glob_text(pattern=command.argument))
            continue
        if command and command.type == "tree":
            tree_path, kwargs, error, uses_named_options = parse_interactive_tree_argument(command.argument)
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_tree_text(path=tree_path, **kwargs))
            else:
                print(get_tree_text(path=command.argument))
            continue
        if command and command.type == "symbols":
            symbol_paths, kwargs, error, uses_named_options = parse_interactive_symbols_argument(command.argument)
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_symbols_text(argument=symbol_paths, **kwargs))
            else:
                print(get_symbols_text(argument=command.argument))
            continue
        if command and command.type == "file_info":
            print(get_file_info_text(argument=command.argument))
            continue
        if command and command.type == "image_info":
            print(get_image_info_text(argument=command.argument))
            continue
        if command and command.type == "read":
            read_argument, kwargs, error, uses_named_options = parse_interactive_read_argument(command.argument)
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_read_text(argument=read_argument, **kwargs))
            else:
                print(get_read_text(argument=command.argument))
            continue
        if command and command.type == "around":
            around_argument, kwargs, error, uses_named_options = parse_interactive_around_argument(command.argument)
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_around_text(argument=around_argument, **kwargs))
            else:
                print(get_around_text(argument=command.argument))
            continue
        if command and command.type == "around_many":
            around_many_argument, kwargs, error, uses_named_options = parse_interactive_around_many_argument(command.argument)
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_around_many_text(argument=around_many_argument, **kwargs))
            else:
                print(get_around_many_text(argument=command.argument))
            continue
        if command and command.type == "output_contexts":
            output_text, kwargs, error, uses_named_options = parse_interactive_output_analysis_argument(
                command.argument,
                "Usage: /output-contexts [--context-lines N] [--max-contexts N] [--max-bytes N] -- <text>",
            )
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_output_contexts_text(text=output_text, **kwargs))
            else:
                print(get_output_contexts_text(text=command.argument))
            continue
        if command and command.type == "output_diagnostics":
            output_text, kwargs, error, uses_named_options = parse_interactive_output_analysis_argument(
                command.argument,
                "Usage: /output-diagnostics [--context-lines N] [--max-diagnostics N] [--max-contexts N] [--max-bytes N] -- <text>",
                include_max_diagnostics=True,
            )
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_output_diagnostics_text(text=output_text, **kwargs))
            else:
                print(get_output_diagnostics_text(text=command.argument))
            continue
        if command and command.type == "python_traceback":
            output_text, kwargs, error, uses_named_options = parse_interactive_output_analysis_argument(
                command.argument,
                "Usage: /python-traceback [--context-lines N] [--max-diagnostics N] [--max-contexts N] [--max-bytes N] -- <text>",
                include_max_diagnostics=True,
            )
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_python_traceback_text(text=output_text, **kwargs))
            else:
                print(get_python_traceback_text(text=command.argument))
            continue
        if command and command.type == "tail":
            tail_argument, kwargs, error, uses_named_options = parse_interactive_tail_argument(command.argument)
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_tail_text(argument=tail_argument, **kwargs))
            else:
                print(get_tail_text(argument=command.argument))
            continue
        if command and command.type == "read_files":
            paths, kwargs, error, uses_named_options = parse_interactive_read_files_argument(command.argument)
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_read_files_text(argument=paths, **kwargs))
            else:
                print(get_read_files_text(argument=command.argument))
            continue
        if command and command.type == "read_ranges":
            ranges_argument, kwargs, error, uses_named_options = parse_interactive_read_ranges_argument(command.argument)
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_read_ranges_text(argument=ranges_argument, **kwargs))
            else:
                print(get_read_ranges_text(argument=command.argument))
            continue
        if command and command.type == "python_check":
            print(get_python_check_text(argument=command.argument))
            continue
        if command and command.type == "python_deps":
            print(get_python_deps_text(argument=command.argument))
            continue
        if command and command.type == "python_defs":
            symbol, path, kwargs, error, uses_named_options = parse_interactive_python_symbol_argument(
                command.argument,
                command_name="python-defs",
                include_max_lines=True,
            )
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_python_defs_text(symbol=symbol, path=path, **kwargs))
            else:
                print(get_python_defs_text(argument=command.argument))
            continue
        if command and command.type == "python_refs":
            symbol, path, kwargs, error, uses_named_options = parse_interactive_python_symbol_argument(
                command.argument,
                command_name="python-refs",
            )
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_python_refs_text(symbol=symbol, path=path, **kwargs))
            else:
                print(get_python_refs_text(argument=command.argument))
            continue
        if command and command.type == "python_ref_contexts":
            symbol, path, kwargs, error, uses_named_options = parse_interactive_python_symbol_argument(
                command.argument,
                command_name="python-ref-contexts",
                include_context=True,
            )
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_python_ref_contexts_text(symbol=symbol, path=path, **kwargs))
            else:
                print(get_python_ref_contexts_text(argument=command.argument))
            continue
        if command and command.type == "python_calls":
            symbol, path, kwargs, error, uses_named_options = parse_interactive_python_symbol_argument(
                command.argument,
                command_name="python-calls",
            )
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_python_calls_text(symbol=symbol, path=path, **kwargs))
            else:
                print(get_python_calls_text(argument=command.argument))
            continue
        if command and command.type == "python_call_graph":
            print(get_python_call_graph_text(argument=command.argument))
            continue
        if command and command.type == "python_rename_preview":
            print(get_python_rename_preview_text(argument=command.argument))
            continue
        if command and command.type == "python_rename":
            print(get_python_rename_text(argument=command.argument))
            continue
        if command and command.type == "check_replace_python_definition":
            print(get_check_replace_python_definition_text(argument=command.argument))
            continue
        if command and command.type == "replace_python_definition":
            print(get_replace_python_definition_text(argument=command.argument))
            continue
        if command and command.type == "config_check":
            print(get_config_check_text(argument=command.argument))
            continue
        if command and command.type == "check_json_set":
            print(get_check_json_set_text(argument=command.argument))
            continue
        if command and command.type == "json_set":
            print(get_json_set_text(argument=command.argument))
            continue
        if command and command.type == "check_json_remove":
            print(get_check_json_remove_text(argument=command.argument))
            continue
        if command and command.type == "json_remove":
            print(get_json_remove_text(argument=command.argument))
            continue
        if command and command.type == "check_json_patch":
            print(get_check_json_patch_text(argument=command.argument))
            continue
        if command and command.type == "json_patch":
            print(get_json_patch_text(argument=command.argument))
            continue
        if command and command.type == "check_replace_lines":
            print(get_check_replace_lines_text(argument=command.argument))
            continue
        if command and command.type == "replace_lines":
            print(get_replace_lines_text(argument=command.argument))
            continue
        if command and command.type == "check_insert_lines":
            print(get_check_insert_lines_text(argument=command.argument))
            continue
        if command and command.type == "insert_lines":
            print(get_insert_lines_text(argument=command.argument))
            continue
        if command and command.type == "check_append_file":
            print(get_check_append_file_text(argument=command.argument))
            continue
        if command and command.type == "append_file":
            print(get_append_file_text(argument=command.argument))
            continue
        if command and command.type == "check_write_file":
            print(get_check_write_file_text(argument=command.argument))
            continue
        if command and command.type == "write_file":
            print(get_write_file_text(argument=command.argument))
            continue
        if command and command.type == "check_write_files":
            print(get_check_write_files_text(argument=command.argument))
            continue
        if command and command.type == "write_files":
            print(get_write_files_text(argument=command.argument))
            continue
        if command and command.type == "check_edit_file":
            print(get_check_edit_file_text(argument=command.argument))
            continue
        if command and command.type == "edit_file":
            print(get_edit_file_text(argument=command.argument))
            continue
        if command and command.type == "check_multi_edit_file":
            print(get_check_multi_edit_file_text(argument=command.argument))
            continue
        if command and command.type == "multi_edit_file":
            print(get_multi_edit_file_text(argument=command.argument))
            continue
        if command and command.type == "check_delete_file":
            print(get_check_delete_file_text(argument=command.argument))
            continue
        if command and command.type == "delete_file":
            print(get_delete_file_text(argument=command.argument))
            continue
        if command and command.type == "check_delete_files":
            print(get_check_delete_files_text(argument=command.argument))
            continue
        if command and command.type == "delete_files":
            print(get_delete_files_text(argument=command.argument))
            continue
        if command and command.type == "check_move_file":
            print(get_check_move_file_text(argument=command.argument))
            continue
        if command and command.type == "move_file":
            print(get_move_file_text(argument=command.argument))
            continue
        if command and command.type == "check_move_files":
            print(get_check_move_files_text(argument=command.argument))
            continue
        if command and command.type == "move_files":
            print(get_move_files_text(argument=command.argument))
            continue
        if command and command.type == "check_copy_file":
            print(get_check_copy_file_text(argument=command.argument))
            continue
        if command and command.type == "copy_file":
            print(get_copy_file_text(argument=command.argument))
            continue
        if command and command.type == "check_copy_files":
            print(get_check_copy_files_text(argument=command.argument))
            continue
        if command and command.type == "copy_files":
            print(get_copy_files_text(argument=command.argument))
            continue
        if command and command.type == "check_move_dir":
            print(get_check_move_dir_text(argument=command.argument))
            continue
        if command and command.type == "move_dir":
            print(get_move_dir_text(argument=command.argument))
            continue
        if command and command.type == "check_move_dirs":
            print(get_check_move_dirs_text(argument=command.argument))
            continue
        if command and command.type == "move_dirs":
            print(get_move_dirs_text(argument=command.argument))
            continue
        if command and command.type == "check_copy_dir":
            print(get_check_copy_dir_text(argument=command.argument))
            continue
        if command and command.type == "copy_dir":
            print(get_copy_dir_text(argument=command.argument))
            continue
        if command and command.type == "check_copy_dirs":
            print(get_check_copy_dirs_text(argument=command.argument))
            continue
        if command and command.type == "copy_dirs":
            print(get_copy_dirs_text(argument=command.argument))
            continue
        if command and command.type == "check_create_dir":
            print(get_check_create_dir_text(argument=command.argument))
            continue
        if command and command.type == "create_dir":
            print(get_create_dir_text(argument=command.argument))
            continue
        if command and command.type == "check_create_dirs":
            print(get_check_create_dirs_text(argument=command.argument))
            continue
        if command and command.type == "create_dirs":
            print(get_create_dirs_text(argument=command.argument))
            continue
        if command and command.type == "check_delete_empty_dir":
            print(get_check_delete_empty_dir_text(argument=command.argument))
            continue
        if command and command.type == "delete_empty_dir":
            print(get_delete_empty_dir_text(argument=command.argument))
            continue
        if command and command.type == "check_delete_empty_dirs":
            print(get_check_delete_empty_dirs_text(argument=command.argument))
            continue
        if command and command.type == "delete_empty_dirs":
            print(get_delete_empty_dirs_text(argument=command.argument))
            continue
        if command and command.type == "check_set_executable":
            print(get_check_set_executable_text(argument=command.argument))
            continue
        if command and command.type == "set_executable":
            print(get_set_executable_text(argument=command.argument))
            continue
        if command and command.type == "check_patch":
            print(get_check_patch_text(argument=command.argument))
            continue
        if command and command.type == "patch_file":
            print(get_patch_text(argument=command.argument))
            continue
        if command and command.type == "check_patches":
            print(get_check_patches_text(argument=command.argument))
            continue
        if command and command.type == "patch_files":
            print(get_patches_text(argument=command.argument))
            continue
        if command and command.type == "check_regex_replace":
            print(get_check_regex_replace_text(argument=command.argument))
            continue
        if command and command.type == "regex_replace":
            print(get_regex_replace_text(argument=command.argument))
            continue
        if command and command.type == "code_deps":
            print(get_code_deps_text(argument=command.argument))
            continue
        if command and command.type == "code_refs":
            symbol, path, kwargs, error, uses_named_options = parse_interactive_python_symbol_argument(
                command.argument,
                command_name="code-refs",
            )
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_code_refs_text(symbol=symbol, path=path, **kwargs))
            else:
                print(get_code_refs_text(argument=command.argument))
            continue
        if command and command.type == "code_ref_contexts":
            symbol, path, kwargs, error, uses_named_options = parse_interactive_python_symbol_argument(
                command.argument,
                command_name="code-ref-contexts",
                include_context=True,
            )
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_code_ref_contexts_text(symbol=symbol, path=path, **kwargs))
            else:
                print(get_code_ref_contexts_text(argument=command.argument))
            continue
        if command and command.type == "code_defs":
            symbol, path, kwargs, error, uses_named_options = parse_interactive_python_symbol_argument(
                command.argument,
                command_name="code-defs",
                include_max_lines=True,
            )
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_code_defs_text(symbol=symbol, path=path, **kwargs))
            else:
                print(get_code_defs_text(argument=command.argument))
            continue
        if command and command.type == "code_rename_preview":
            print(get_code_rename_preview_text(argument=command.argument))
            continue
        if command and command.type == "code_rename":
            print(get_code_rename_text(argument=command.argument))
            continue
        if command and command.type == "git_status":
            print(get_git_status_text())
            continue
        if command and command.type == "git_conflicts":
            print(get_git_conflicts_text(argument=command.argument))
            continue
        if command and command.type == "git_info":
            print(get_git_info_text())
            continue
        if command and command.type == "branches":
            print(get_branches_text())
            continue
        if command and command.type == "log":
            print(get_log_text(argument=command.argument))
            continue
        if command and command.type == "show":
            print(get_show_text(argument=command.argument))
            continue
        if command and command.type == "blame":
            print(get_blame_text(argument=command.argument))
            continue
        if command and command.type == "stashes":
            print(get_stashes_text(argument=command.argument))
            continue
        if command and command.type == "check_fetch":
            print(get_check_fetch_text(argument=command.argument))
            continue
        if command and command.type == "fetch":
            print(get_fetch_text(argument=command.argument))
            continue
        if command and command.type == "check_pull":
            print(get_check_pull_text())
            continue
        if command and command.type == "pull":
            print(get_pull_text())
            continue
        if command and command.type == "check_push":
            print(get_check_push_text())
            continue
        if command and command.type == "push":
            print(get_push_text())
            continue
        if command and command.type == "check_stash":
            print(get_check_stash_text(argument=command.argument))
            continue
        if command and command.type == "stash":
            print(get_stash_text(argument=command.argument))
            continue
        if command and command.type == "check_stash_apply":
            print(get_check_stash_apply_text(argument=command.argument))
            continue
        if command and command.type == "stash_apply":
            print(get_stash_apply_text(argument=command.argument))
            continue
        if command and command.type == "check_stash_drop":
            print(get_check_stash_drop_text(argument=command.argument))
            continue
        if command and command.type == "stash_drop":
            print(get_stash_drop_text(argument=command.argument))
            continue
        if command and command.type == "check_stage":
            print(get_check_stage_text(argument=command.argument))
            continue
        if command and command.type == "stage":
            print(get_stage_text(argument=command.argument))
            continue
        if command and command.type == "check_unstage":
            print(get_check_unstage_text(argument=command.argument))
            continue
        if command and command.type == "unstage":
            print(get_unstage_text(argument=command.argument))
            continue
        if command and command.type == "check_commit":
            print(get_check_commit_text(argument=command.argument))
            continue
        if command and command.type == "commit":
            print(get_commit_text(argument=command.argument))
            continue
        if command and command.type == "check_restore":
            print(get_check_restore_text(argument=command.argument))
            continue
        if command and command.type == "restore":
            print(get_restore_text(argument=command.argument))
            continue
        if command and command.type == "check_switch":
            print(get_check_switch_text(argument=command.argument))
            continue
        if command and command.type == "switch":
            print(get_switch_text(argument=command.argument))
            continue
        if command and command.type == "env":
            print(get_env_text())
            continue
        if command and command.type == "processes":
            print(get_processes_text())
            continue
        if command and command.type == "process":
            print(get_process_text(argument=command.argument))
            continue
        if command and command.type == "process_output_contexts":
            if command.argument and "--" in command.argument:
                process_id, kwargs, error = parse_interactive_process_output_argument(
                    command.argument,
                    "Usage: /process-output-contexts <id> [chars] [--max-chars N] [--context-lines N] [--max-contexts N] [--max-bytes N]",
                    {
                        "--max-chars": ("max_output_chars", False),
                        "--context-lines": ("context_lines", True),
                        "--max-contexts": ("max_contexts", False),
                        "--max-bytes": ("max_bytes_per_context", False),
                    },
                )
                if error:
                    print(error)
                    continue
                print(get_process_output_contexts_text(process_id=process_id, **kwargs))
                continue
            print(get_process_output_contexts_text(argument=command.argument))
            continue
        if command and command.type == "process_output_diagnostics":
            if command.argument and "--" in command.argument:
                process_id, kwargs, error = parse_interactive_process_output_argument(
                    command.argument,
                    "Usage: /process-output-diagnostics <id> [chars] [--max-chars N] [--context-lines N] [--max-diagnostics N] [--max-contexts N] [--max-bytes N]",
                    {
                        "--max-chars": ("max_output_chars", False),
                        "--context-lines": ("context_lines", True),
                        "--max-diagnostics": ("max_diagnostics", False),
                        "--max-contexts": ("max_contexts", False),
                        "--max-bytes": ("max_bytes_per_context", False),
                    },
                )
                if error:
                    print(error)
                    continue
                print(get_process_output_diagnostics_text(process_id=process_id, **kwargs))
                continue
            print(get_process_output_diagnostics_text(argument=command.argument))
            continue
        if command and command.type == "wait_process":
            process_id, kwargs, error, uses_named_options = parse_interactive_wait_process_argument(command.argument)
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_wait_process_text(process_id=process_id, **kwargs))
            else:
                print(get_wait_process_text(argument=command.argument))
            continue
        if command and command.type == "check_write_process":
            print(get_check_write_process_text(argument=command.argument))
            continue
        if command and command.type == "write_process":
            print(get_write_process_text(argument=command.argument))
            continue
        if command and command.type == "check_stop_process":
            print(get_check_stop_process_text(process_id=command.argument))
            continue
        if command and command.type == "stop_process":
            print(get_stop_process_text(process_id=command.argument))
            continue
        if command and command.type == "check_stop_all_processes":
            print(get_check_stop_all_processes_text())
            continue
        if command and command.type == "stop_all_processes":
            print(get_stop_all_processes_text())
            continue
        if command and command.type == "status":
            print(get_status_text(mode, approval_policy, resume_run_id, chat_turns=len(chat_history) // 2))
            continue
        if command and command.type == "context":
            print(get_context_text(resume_run_id=resume_run_id, resume_context=resume_context))
            continue
        if command and command.type == "init":
            print(init_project_instructions(file_name=command.argument))
            continue
        if command and command.type == "doctor":
            print(get_doctor_text())
            continue
        if command and command.type == "review":
            kwargs, error, uses_named_options = parse_interactive_option_limit_argument(
                command.argument,
                "Usage: /review [--max-files N] [--max-checks N]",
                {"--max-files": "max_files", "--max-checks": "max_checks"},
            )
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_review_text(**kwargs))
            else:
                print(get_review_text())
            continue
        if command and command.type == "handoff":
            kwargs, error, uses_named_options = parse_interactive_option_limit_argument(
                command.argument,
                "Usage: /handoff [--max-files N] [--max-checks N] [--max-status-chars N] [--max-plan-chars N]",
                {
                    "--max-files": "max_files",
                    "--max-checks": "max_checks",
                    "--max-status-chars": "max_status_chars",
                    "--max-plan-chars": "max_plan_chars",
                },
            )
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_handoff_text(**kwargs))
            else:
                print(get_handoff_text())
            continue
        if command and command.type == "changes":
            kwargs, error, uses_named_options = parse_interactive_option_limit_argument(
                command.argument,
                "Usage: /changes [--max-files N]",
                {"--max-files": "max_files"},
            )
            if error:
                print(error)
                continue
            if uses_named_options:
                print(get_changes_text(**kwargs))
            else:
                print(get_changes_text())
            continue
        if command and command.type == "diff":
            diff_argument, max_chars, error = parse_interactive_diff_argument(command.argument)
            if error:
                print(error)
                continue
            try:
                print(get_diff_text(argument=diff_argument, max_chars=max_chars))
            except ValueError as error:
                print(f"Usage: /diff [--staged|--cached] [--max-chars N] [path]\n  error: {error}")
            continue
        if command and command.type == "diff_hunks":
            diff_argument, kwargs, error = parse_interactive_diff_hunks_argument(command.argument)
            if error:
                print(error)
                continue
            print(get_diff_hunks_text(argument=diff_argument, **kwargs))
            continue
        if command and command.type == "diff_contexts":
            diff_argument, kwargs, error = parse_interactive_diff_contexts_argument(command.argument)
            if error:
                print(error)
                continue
            print(get_diff_contexts_text(argument=diff_argument, **kwargs))
            continue
        if command and command.type == "clear":
            chat_history.clear()
            resume_run_id = None
            resume_context = None
            print("Cleared chat history and resume context.")
            continue
        if command and command.type == "usage":
            print(get_usage_text())
            continue
        if command and command.type == "cost":
            print(get_cost_text())
            continue
        if command and command.type == "approval":
            approval_policy, text = handle_approval_command(command.argument, approval_policy)
            print(text)
            continue
        if command and command.type == "sessions":
            print(get_sessions_text())
            continue
        if command and command.type == "session":
            print(get_session_text(command.argument))
            continue
        if command and command.type == "last":
            print(get_last_session_text())
            continue
        if command and command.type == "plan":
            print(get_plan_text(run_id=command.argument))
            continue
        if command and command.type == "transcript":
            run_id, kwargs, error = parse_interactive_transcript_argument(command.argument)
            print(error if error else get_transcript_text(run_id=run_id, **kwargs))
            continue
        if command and command.type == "session_search":
            query, run_id, kwargs, error = parse_interactive_session_search_argument(command.argument)
            print(error if error else get_session_search_text(argument=query, run_id=run_id, **kwargs))
            continue
        if command and command.type == "session_commands":
            usage = "Usage: /session-commands [run-id] [--max-commands N] [--max-output-chars N]"
            run_id, kwargs, error = parse_interactive_session_detail_argument(
                command.argument,
                usage,
                {
                    "--max-commands": ("max_commands", False),
                    "--max-output-chars": ("max_output_chars", True),
                },
            )
            print(error if error else get_session_commands_text(run_id=run_id, **kwargs))
            continue
        if command and command.type == "session_output_contexts":
            usage = (
                "Usage: /session-output-contexts [run-id] [--max-commands N] "
                "[--max-output-chars N] [--context-lines N] [--max-contexts N] [--max-bytes N]"
            )
            run_id, kwargs, error = parse_interactive_session_detail_argument(
                command.argument,
                usage,
                {
                    "--max-commands": ("max_commands", False),
                    "--max-output-chars": ("max_output_chars", False),
                    "--context-lines": ("context_lines", True),
                    "--max-contexts": ("max_contexts", False),
                    "--max-bytes": ("max_bytes_per_context", False),
                },
            )
            print(error if error else get_session_output_contexts_text(run_id=run_id, **kwargs))
            continue
        if command and command.type == "session_output_diagnostics":
            usage = (
                "Usage: /session-output-diagnostics [run-id] [--max-commands N] "
                "[--max-output-chars N] [--context-lines N] [--max-diagnostics N] "
                "[--max-contexts N] [--max-bytes N]"
            )
            run_id, kwargs, error = parse_interactive_session_detail_argument(
                command.argument,
                usage,
                {
                    "--max-commands": ("max_commands", False),
                    "--max-output-chars": ("max_output_chars", False),
                    "--context-lines": ("context_lines", True),
                    "--max-diagnostics": ("max_diagnostics", False),
                    "--max-contexts": ("max_contexts", False),
                    "--max-bytes": ("max_bytes_per_context", False),
                },
            )
            print(error if error else get_session_output_diagnostics_text(run_id=run_id, **kwargs))
            continue
        if command and command.type == "session_files":
            usage = "Usage: /session-files [run-id] [--max-files N]"
            run_id, kwargs, error = parse_interactive_session_detail_argument(
                command.argument,
                usage,
                {"--max-files": ("max_files", False)},
            )
            print(error if error else get_session_files_text(run_id=run_id, **kwargs))
            continue
        if command and command.type == "session_failures":
            usage = "Usage: /session-failures [run-id] [--max-failures N] [--max-text N]"
            run_id, kwargs, error = parse_interactive_session_detail_argument(
                command.argument,
                usage,
                {
                    "--max-failures": ("max_failures", False),
                    "--max-text": ("max_text", False),
                },
            )
            print(error if error else get_session_failures_text(run_id=run_id, **kwargs))
            continue
        if command and command.type == "session_verification":
            usage = "Usage: /session-verification [run-id] [--max-checks N]"
            run_id, kwargs, error = parse_interactive_session_detail_argument(
                command.argument,
                usage,
                {"--max-checks": ("max_checks", False)},
            )
            print(error if error else get_session_verification_text(run_id=run_id, **kwargs))
            continue
        if command and command.type == "session_audit":
            usage = "Usage: /session-audit [run-id] [--max-failures N] [--max-files N] [--max-commands N] [--max-checks N] [--max-text N]"
            run_id, kwargs, error = parse_interactive_session_detail_argument(
                command.argument,
                usage,
                {
                    "--max-failures": ("max_failures", False),
                    "--max-files": ("max_files", False),
                    "--max-commands": ("max_commands", False),
                    "--max-checks": ("max_checks", False),
                    "--max-text": ("max_text", False),
                },
            )
            print(error if error else get_session_audit_text(run_id=run_id, **kwargs))
            continue
        if command and command.type == "session_handoff":
            usage = (
                "Usage: /session-handoff [run-id] [--max-failures N] [--max-files N] "
                "[--max-commands N] [--max-checks N] [--max-output-chars N] [--max-text N]"
            )
            run_id, kwargs, error = parse_interactive_session_detail_argument(
                command.argument,
                usage,
                {
                    "--max-failures": ("max_failures", False),
                    "--max-files": ("max_files", False),
                    "--max-commands": ("max_commands", False),
                    "--max-checks": ("max_checks", False),
                    "--max-output-chars": ("max_output_chars", True),
                    "--max-text": ("max_text", False),
                },
            )
            print(error if error else get_session_handoff_text(run_id=run_id, **kwargs))
            continue
        if command and command.type == "checkpoint":
            print(get_checkpoint_text(label=command.argument))
            continue
        if command and command.type == "checkpoints":
            print(get_checkpoints_text())
            continue
        if command and command.type == "checkpoint_show":
            print(get_checkpoint_show_text(command.argument))
            continue
        if command and command.type == "checkpoint_diff":
            print(get_checkpoint_diff_text(command.argument))
            continue
        if command and command.type == "checkpoint_status":
            print(get_checkpoint_status_text(command.argument))
            continue
        if command and command.type == "check_checkpoint_restore":
            print(get_check_checkpoint_restore_text(command.argument))
            continue
        if command and command.type == "checkpoint_restore":
            print(get_checkpoint_restore_text(command.argument))
            continue
        if command and command.type == "check_checkpoint_delete":
            print(get_check_checkpoint_delete_text(command.argument))
            continue
        if command and command.type == "checkpoint_delete":
            print(get_checkpoint_delete_text(command.argument))
            continue
        if command and command.type == "check_checkpoint_prune":
            print(get_check_checkpoint_prune_text(command.argument))
            continue
        if command and command.type == "checkpoint_prune":
            print(get_checkpoint_prune_text(command.argument))
            continue
        if command and command.type == "resume":
            usage = (
                "Usage: /resume [run-id|off] [--max-failures N] [--max-files N] "
                "[--max-commands N] [--max-checks N] [--max-output-chars N] [--max-text N]"
            )
            run_id, kwargs, error = parse_interactive_session_detail_argument(
                command.argument,
                usage,
                {
                    "--max-failures": ("max_failures", False),
                    "--max-files": ("max_files", False),
                    "--max-commands": ("max_commands", False),
                    "--max-checks": ("max_checks", False),
                    "--max-output-chars": ("max_output_chars", True),
                    "--max-text": ("max_text", False),
                },
            )
            if error:
                print(error)
                continue
            selected, context, text = get_resume_context(run_id, **kwargs)
            resume_run_id = selected
            resume_context = context
            print(text)
            continue
        if command and command.type == "compact":
            usage = (
                "Usage: /compact [run-id] [--max-failures N] [--max-files N] "
                "[--max-commands N] [--max-checks N] [--max-output-chars N] [--max-text N]"
            )
            run_id, kwargs, error = parse_interactive_session_detail_argument(
                command.argument,
                usage,
                {
                    "--max-failures": ("max_failures", False),
                    "--max-files": ("max_files", False),
                    "--max-commands": ("max_commands", False),
                    "--max-checks": ("max_checks", False),
                    "--max-output-chars": ("max_output_chars", True),
                    "--max-text": ("max_text", False),
                },
            )
            if error:
                print(error)
                continue
            selected, context, text = get_compact_context(run_id, **kwargs)
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
