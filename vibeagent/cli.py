from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
import os
from pathlib import Path
import shlex
import sys

from .agent import AgentResult, run_agent
from .chat import run_chat
from .commands import (
    get_append_file_text,
    get_help_text,
    get_blame_text,
    get_branches_text,
    get_compact_context,
    get_checks_report,
    get_checks_text,
    get_changes_text,
    get_check_checkpoint_delete_text,
    get_check_checkpoint_prune_text,
    get_check_checkpoint_restore_text,
    get_checkpoint_diff_text,
    get_checkpoint_delete_text,
    get_checkpoint_prune_text,
    get_checkpoint_restore_text,
    get_checkpoint_show_text,
    get_checkpoint_status_text,
    get_checkpoint_text,
    get_checkpoints_text,
    get_check_copy_dir_text,
    get_check_copy_dirs_text,
    get_check_copy_file_text,
    get_check_copy_files_text,
    get_check_create_dirs_text,
    get_check_create_dir_text,
    get_check_delete_file_text,
    get_check_delete_files_text,
    get_check_delete_empty_dirs_text,
    get_check_delete_empty_dir_text,
    get_check_edit_file_text,
    get_check_fetch_text,
    get_check_pull_text,
    get_check_push_text,
    get_check_set_executable_text,
    get_check_stash_text,
    get_check_stash_apply_text,
    get_check_stash_drop_text,
    get_check_switch_text,
    get_check_append_file_text,
    get_check_insert_lines_text,
    get_check_move_dir_text,
    get_check_move_dirs_text,
    get_check_move_file_text,
    get_check_move_files_text,
    get_check_multi_edit_file_text,
    get_check_patch_text,
    get_check_patches_text,
    get_check_write_file_text,
    get_check_write_files_text,
    get_check_run_sequence_text,
    get_check_start_text,
    get_check_stop_all_processes_text,
    get_check_stop_process_text,
    get_check_commit_text,
    get_check_json_patch_text,
    get_check_regex_replace_text,
    get_check_replace_lines_text,
    get_check_replace_python_definition_text,
    get_check_restore_text,
    get_check_stage_text,
    get_check_unstage_text,
    get_check_json_remove_text,
    get_check_json_set_text,
    get_code_defs_text,
    get_code_ref_contexts_text,
    get_code_rename_preview_text,
    get_code_rename_text,
    get_command_check_text,
    get_commands_text,
    get_code_deps_text,
    get_code_refs_text,
    get_config_text,
    get_context_text,
    get_commit_text,
    get_config_check_text,
    get_copy_dir_text,
    get_copy_dirs_text,
    get_copy_file_text,
    get_copy_files_text,
    get_cost_text,
    get_create_dirs_text,
    get_create_dir_text,
    get_delete_file_text,
    get_delete_files_text,
    get_delete_empty_dirs_text,
    get_delete_empty_dir_text,
    get_diff_hunks_text,
    get_diff_contexts_text,
    get_diff_text,
    get_doctor_report,
    get_doctor_text,
    get_edit_file_text,
    get_env_text,
    get_fetch_text,
    get_file_info_text,
    get_image_info_text,
    get_git_info_text,
    get_git_conflicts_text,
    get_git_status_text,
    get_glob_text,
    get_handoff_text,
    get_http_fetch_text,
    get_http_text,
    get_insert_lines_text,
    get_instructions_text,
    get_json_patch_text,
    get_json_remove_text,
    get_json_set_text,
    get_last_session_text,
    get_log_text,
    get_manifests_text,
    get_model_text,
    get_move_dir_text,
    get_move_dirs_text,
    get_move_file_text,
    get_move_files_text,
    get_multi_edit_file_text,
    get_overview_text,
    get_patch_text,
    get_patches_text,
    get_permissions_report,
    get_permissions_text,
    get_plan_text,
    get_port_text,
    get_pull_text,
    get_push_text,
    get_check_suggested_checks_text,
    get_around_text,
    get_around_many_text,
    get_output_contexts_text,
    get_output_diagnostics_text,
    get_process_output_contexts_text,
    get_process_output_diagnostics_text,
    get_process_text,
    get_processes_text,
    get_check_write_process_text,
    get_python_traceback_text,
    get_python_call_graph_text,
    get_python_calls_text,
    get_python_check_text,
    get_python_defs_text,
    get_python_deps_text,
    get_python_ref_contexts_text,
    get_python_refs_text,
    get_python_rename_preview_text,
    get_python_rename_text,
    get_read_files_text,
    get_read_ranges_text,
    get_read_text,
    get_regex_replace_text,
    get_check_focused_test_commands_text,
    get_focused_test_commands_text,
    get_related_tests_text,
    get_run_focused_test_commands_text,
    get_replace_lines_text,
    get_replace_python_definition_text,
    get_repo_map_text,
    get_review_text,
    get_resume_context,
    get_restore_text,
    get_run_sequence_text,
    get_run_suggested_checks_text,
    get_run_text,
    get_session_audit_text,
    get_session_commands_text,
    get_session_output_contexts_text,
    get_session_output_diagnostics_text,
    get_session_failures_text,
    get_session_files_text,
    get_session_handoff_text,
    get_session_text,
    get_session_verification_text,
    get_sessions_text,
    get_search_text,
    get_search_contexts_text,
    get_session_search_text,
    get_set_executable_text,
    get_show_text,
    get_start_text,
    get_stash_apply_text,
    get_stash_drop_text,
    get_stash_text,
    get_stage_text,
    get_stashes_text,
    get_status_text,
    get_tail_text,
    get_todos_text,
    get_stop_all_processes_text,
    get_stop_process_text,
    get_switch_text,
    get_symbols_text,
    get_tool_text,
    get_tools_text,
    get_tree_text,
    get_transcript_text,
    get_unstage_text,
    get_usage_text,
    get_wait_process_text,
    get_write_file_text,
    get_write_files_text,
    get_write_process_text,
    init_project_instructions,
    parse_local_command,
)
from .config import load_project_config_env, resolve_execution_config, save_project_config
from .providers import create_chat_client, get_provider_name
from .types import ApprovalDecision, ApprovalHandler, ApprovalPolicy, ApprovalRequest, ChatMessage


LOCAL_RESULT_ARG_NAMES = frozenset(
    {
        "model",
        "tool",
        "config",
        "tools",
        "permissions",
        "checks",
        "command_check",
        "run_command",
        "check_run_commands",
        "run_commands",
        "check_suggested_checks",
        "run_suggested_checks",
        "commands",
        "related_tests",
        "focused_tests",
        "check_focused_tests",
        "run_focused_tests",
        "manifests",
        "instructions",
        "todos",
        "check_start_command",
        "start_command",
        "port_check",
        "http_check",
        "http_fetch",
        "overview",
        "repo_map",
        "search",
        "search_contexts",
        "glob",
        "tree",
        "file_info",
        "image_info",
        "read",
        "around",
        "around_many",
        "output_contexts",
        "output_diagnostics",
        "python_traceback",
        "tail",
        "read_files",
        "read_ranges",
        "symbols",
        "python_check",
        "python_deps",
        "python_defs",
        "python_refs",
        "python_ref_contexts",
        "python_calls",
        "python_call_graph",
        "python_rename_preview",
        "python_rename",
        "code_deps",
        "code_refs",
        "code_ref_contexts",
        "code_defs",
        "code_rename_preview",
        "check_replace_python_def",
        "replace_python_def",
        "config_check",
        "check_json_set",
        "json_set",
        "check_json_remove",
        "json_remove",
        "check_json_patch",
        "json_patch",
        "check_replace_lines",
        "replace_lines",
        "check_insert_lines",
        "insert_lines",
        "check_append",
        "append",
        "check_write",
        "write",
        "check_write_files",
        "write_files",
        "check_edit",
        "edit",
        "check_multi_edit",
        "multi_edit",
        "check_delete",
        "delete",
        "check_delete_files",
        "delete_files",
        "check_move",
        "move",
        "check_move_files",
        "move_files",
        "check_copy",
        "copy",
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
        "check_mkdir",
        "mkdir",
        "check_mkdirs",
        "mkdirs",
        "check_rmdir",
        "rmdir",
        "check_rmdirs",
        "rmdirs",
        "check_executable",
        "set_executable",
        "check_patch",
        "patch",
        "check_patches",
        "patches",
        "check_regex_replace",
        "regex_replace",
        "code_rename",
        "git_status",
        "conflicts",
        "git_info",
        "branches",
        "log",
        "show",
        "blame",
        "stashes",
        "review",
        "handoff",
        "changes",
        "diff",
        "diff_hunks",
        "diff_contexts",
        "process_output",
        "process_output_contexts",
        "process_output_diagnostics",
        "wait_process",
        "check_write_process",
        "write_process",
        "check_stop_process",
        "stop_process",
        "check_stop_all_processes",
        "stop_all_processes",
        "env",
        "processes",
        "status",
        "context",
        "init",
        "doctor",
        "check_git_fetch",
        "git_fetch",
        "check_git_pull",
        "git_pull",
        "check_git_push",
        "git_push",
        "check_git_stash",
        "git_stash",
        "check_git_stash_apply",
        "git_stash_apply",
        "check_git_stash_drop",
        "git_stash_drop",
        "check_git_stage",
        "git_stage",
        "check_git_unstage",
        "git_unstage",
        "check_git_commit",
        "git_commit",
        "check_git_restore",
        "git_restore",
        "check_git_switch",
        "git_switch",
        "sessions",
        "last",
        "session",
        "plan",
        "transcript",
        "session_search",
        "session_commands",
        "session_output_contexts",
        "session_output_diagnostics",
        "session_files",
        "session_failures",
        "session_verification",
        "session_audit",
        "session_handoff",
        "checkpoint",
        "checkpoints",
        "checkpoint_show",
        "checkpoint_diff",
        "checkpoint_status",
        "check_checkpoint_restore",
        "checkpoint_restore",
        "check_checkpoint_delete",
        "checkpoint_delete",
        "check_checkpoint_prune",
        "checkpoint_prune",
        "cost",
        "save_config",
    }
)


def main(argv: Sequence[str] | None = None) -> int:
    if argv is not None:
        args = parse_args(argv)
        if args.diff_staged and args.diff is None and args.diff_hunks is None and args.diff_contexts is None:
            return print_error_result("--staged can only be used with --diff, --diff-hunks, or --diff-contexts.", args.json, exit_code=2)
        if args.command_cwd and not args.command_check:
            return print_error_result("--command-cwd can only be used with --command-check.", args.json, exit_code=2)
        if args.run_cwd and args.run_command is None and args.run_commands is None and args.check_run_commands is None:
            return print_error_result("--run-cwd can only be used with --run-command, --run-commands, or --check-run-commands.", args.json, exit_code=2)
        if args.start_cwd and args.start_command is None and args.check_start_command is None:
            return print_error_result("--start-cwd can only be used with --check-start-command or --start-command.", args.json, exit_code=2)
        if args.port_host != "127.0.0.1" and args.port_check is None:
            return print_error_result("--port-host can only be used with --port-check.", args.json, exit_code=2)
        if args.port_timeout_ms != 1000 and args.port_check is None:
            return print_error_result("--port-timeout-ms can only be used with --port-check.", args.json, exit_code=2)
        if args.http_timeout_ms is not None and args.http_check is None and args.http_fetch is None:
            return print_error_result("--http-timeout-ms can only be used with --http-check or --http-fetch.", args.json, exit_code=2)
        if args.http_max_body_chars is not None and args.http_check is None and args.http_fetch is None:
            return print_error_result("--http-max-body-chars can only be used with --http-check or --http-fetch.", args.json, exit_code=2)
        if args.http_contains is not None and args.http_check is None:
            return print_error_result("--http-contains can only be used with --http-check.", args.json, exit_code=2)
        if args.http_regex and args.http_check is None:
            return print_error_result("--http-regex can only be used with --http-check.", args.json, exit_code=2)
        search_selected = args.search is not None or args.search_contexts is not None
        if args.search_path and not search_selected:
            return print_error_result("--search-path can only be used with --search or --search-contexts.", args.json, exit_code=2)
        if args.search_max_matches is not None and not search_selected:
            return print_error_result("--search-max-matches can only be used with --search or --search-contexts.", args.json, exit_code=2)
        if args.search_regex and not search_selected:
            return print_error_result("--search-regex can only be used with --search or --search-contexts.", args.json, exit_code=2)
        if args.search_ignore_case and not search_selected:
            return print_error_result("--search-ignore-case can only be used with --search or --search-contexts.", args.json, exit_code=2)
        if args.search_context_lines is not None and not search_selected:
            return print_error_result("--search-context-lines can only be used with --search or --search-contexts.", args.json, exit_code=2)
        if args.search_context_max_bytes is not None and args.search_contexts is None:
            return print_error_result("--search-context-max-bytes can only be used with --search-contexts.", args.json, exit_code=2)
        if args.related_tests_max_paths is not None and args.related_tests is None:
            return print_error_result("--related-tests-max-paths can only be used with --related-tests.", args.json, exit_code=2)
        if args.related_tests_max_candidates is not None and args.related_tests is None:
            return print_error_result("--related-tests-max-candidates can only be used with --related-tests.", args.json, exit_code=2)
        focused_tests_selected = args.focused_tests is not None or args.check_focused_tests is not None or args.run_focused_tests is not None
        if args.focused_tests_max_paths is not None and not focused_tests_selected:
            return print_error_result("--focused-tests-max-paths can only be used with --focused-tests, --check-focused-tests, or --run-focused-tests.", args.json, exit_code=2)
        if args.focused_tests_max_candidates is not None and not focused_tests_selected:
            return print_error_result("--focused-tests-max-candidates can only be used with --focused-tests, --check-focused-tests, or --run-focused-tests.", args.json, exit_code=2)
        if args.focused_tests_max_commands is not None and not focused_tests_selected:
            return print_error_result("--focused-tests-max-commands can only be used with --focused-tests, --check-focused-tests, or --run-focused-tests.", args.json, exit_code=2)
        if args.commands_max_commands is not None and not args.commands:
            return print_error_result("--commands-max-commands can only be used with --commands.", args.json, exit_code=2)
        if args.commands_max_files is not None and not args.commands:
            return print_error_result("--commands-max-files can only be used with --commands.", args.json, exit_code=2)
        if args.manifests_max_files is not None and not args.manifests:
            return print_error_result("--manifests-max-files can only be used with --manifests.", args.json, exit_code=2)
        if args.manifests_max_items is not None and not args.manifests:
            return print_error_result("--manifests-max-items can only be used with --manifests.", args.json, exit_code=2)
        if args.todos_max_items is not None and args.todos is None:
            return print_error_result("--todos-max-items can only be used with --todos.", args.json, exit_code=2)
        if args.todos_max_files is not None and args.todos is None:
            return print_error_result("--todos-max-files can only be used with --todos.", args.json, exit_code=2)
        if args.instructions_max_files is not None and not args.instructions:
            return print_error_result("--instructions-max-files can only be used with --instructions.", args.json, exit_code=2)
        if args.instructions_max_bytes is not None and not args.instructions:
            return print_error_result("--instructions-max-bytes can only be used with --instructions.", args.json, exit_code=2)
        if args.overview_max_files is not None and not args.overview:
            return print_error_result("--overview-max-files can only be used with --overview.", args.json, exit_code=2)
        if args.overview_max_commands is not None and not args.overview:
            return print_error_result("--overview-max-commands can only be used with --overview.", args.json, exit_code=2)
        if args.overview_max_checks is not None and not args.overview:
            return print_error_result("--overview-max-checks can only be used with --overview.", args.json, exit_code=2)
        if args.repo_map_max_depth is not None and args.repo_map is None:
            return print_error_result("--repo-map-max-depth can only be used with --repo-map.", args.json, exit_code=2)
        if args.repo_map_max_files is not None and args.repo_map is None:
            return print_error_result("--repo-map-max-files can only be used with --repo-map.", args.json, exit_code=2)
        if args.repo_map_max_symbols is not None and args.repo_map is None:
            return print_error_result("--repo-map-max-symbols can only be used with --repo-map.", args.json, exit_code=2)
        if args.glob_max_matches is not None and args.glob is None:
            return print_error_result("--glob-max-matches can only be used with --glob.", args.json, exit_code=2)
        if args.tree_max_depth is not None and args.tree is None:
            return print_error_result("--tree-max-depth can only be used with --tree.", args.json, exit_code=2)
        if args.tree_max_entries is not None and args.tree is None:
            return print_error_result("--tree-max-entries can only be used with --tree.", args.json, exit_code=2)
        if args.symbols_max is not None and args.symbols is None:
            return print_error_result("--symbols-max can only be used with --symbols.", args.json, exit_code=2)
        python_symbol_lookup_selected = (
            args.python_defs is not None
            or args.python_refs is not None
            or args.python_ref_contexts is not None
            or args.python_calls is not None
        )
        if args.python_max_matches is not None and not python_symbol_lookup_selected:
            return print_error_result("--python-max-matches can only be used with --python-defs, --python-refs, --python-ref-contexts, or --python-calls.", args.json, exit_code=2)
        if args.python_def_max_lines is not None and args.python_defs is None:
            return print_error_result("--python-def-max-lines can only be used with --python-defs.", args.json, exit_code=2)
        if args.python_context_lines is not None and args.python_ref_contexts is None:
            return print_error_result("--python-context-lines can only be used with --python-ref-contexts.", args.json, exit_code=2)
        if args.python_context_max_bytes is not None and args.python_ref_contexts is None:
            return print_error_result("--python-context-max-bytes can only be used with --python-ref-contexts.", args.json, exit_code=2)
        code_symbol_lookup_selected = (
            args.code_refs is not None
            or args.code_ref_contexts is not None
            or args.code_defs is not None
        )
        if args.code_max_matches is not None and not code_symbol_lookup_selected:
            return print_error_result("--code-max-matches can only be used with --code-refs, --code-ref-contexts, or --code-defs.", args.json, exit_code=2)
        if args.code_def_max_lines is not None and args.code_defs is None:
            return print_error_result("--code-def-max-lines can only be used with --code-defs.", args.json, exit_code=2)
        if args.code_context_lines is not None and args.code_ref_contexts is None:
            return print_error_result("--code-context-lines can only be used with --code-ref-contexts.", args.json, exit_code=2)
        if args.code_context_max_bytes is not None and args.code_ref_contexts is None:
            return print_error_result("--code-context-max-bytes can only be used with --code-ref-contexts.", args.json, exit_code=2)
        if args.read_lines and args.read is None:
            return print_error_result("--read-lines can only be used with --read.", args.json, exit_code=2)
        if args.read_max_bytes is not None and args.read is None:
            return print_error_result("--read-max-bytes can only be used with --read.", args.json, exit_code=2)
        if args.read_files_max_bytes is not None and args.read_files is None:
            return print_error_result("--read-files-max-bytes can only be used with --read-files.", args.json, exit_code=2)
        if args.read_ranges_max_bytes is not None and args.read_ranges is None:
            return print_error_result("--read-ranges-max-bytes can only be used with --read-ranges.", args.json, exit_code=2)
        if args.around_lines != 20 and args.around is None:
            return print_error_result("--around-lines can only be used with --around.", args.json, exit_code=2)
        if args.around_max_bytes is not None and args.around is None:
            return print_error_result("--around-max-bytes can only be used with --around.", args.json, exit_code=2)
        if args.around_many_max_bytes is not None and args.around_many is None:
            return print_error_result("--around-many-max-bytes can only be used with --around-many.", args.json, exit_code=2)
        if args.output_context_lines != 5 and args.output_contexts is None:
            return print_error_result("--output-context-lines can only be used with --output-contexts.", args.json, exit_code=2)
        if args.output_context_max != 20 and args.output_contexts is None:
            return print_error_result("--output-context-max can only be used with --output-contexts.", args.json, exit_code=2)
        if args.output_context_max_bytes != 20_000 and args.output_contexts is None:
            return print_error_result("--output-context-max-bytes can only be used with --output-contexts.", args.json, exit_code=2)
        output_diagnostic_analysis = args.output_diagnostics is not None or args.python_traceback is not None
        if args.output_diagnostic_lines != 2 and not output_diagnostic_analysis:
            return print_error_result("--output-diagnostic-lines can only be used with --output-diagnostics or --python-traceback.", args.json, exit_code=2)
        if args.output_diagnostic_max != 50 and not output_diagnostic_analysis:
            return print_error_result("--output-diagnostic-max can only be used with --output-diagnostics or --python-traceback.", args.json, exit_code=2)
        if args.output_diagnostic_context_max != 20 and not output_diagnostic_analysis:
            return print_error_result("--output-diagnostic-context-max can only be used with --output-diagnostics or --python-traceback.", args.json, exit_code=2)
        if args.output_diagnostic_context_max_bytes != 20_000 and not output_diagnostic_analysis:
            return print_error_result("--output-diagnostic-context-max-bytes can only be used with --output-diagnostics or --python-traceback.", args.json, exit_code=2)
        session_output_analysis = args.session_output_contexts is not None or args.session_output_diagnostics is not None
        if args.session_output_command_max != 20 and not session_output_analysis:
            return print_error_result("--session-output-command-max can only be used with --session-output-contexts or --session-output-diagnostics.", args.json, exit_code=2)
        if args.session_output_max_chars != 20_000 and not session_output_analysis:
            return print_error_result("--session-output-max-chars can only be used with --session-output-contexts or --session-output-diagnostics.", args.json, exit_code=2)
        if args.session_output_context_lines != 5 and not session_output_analysis:
            return print_error_result("--session-output-context-lines can only be used with --session-output-contexts or --session-output-diagnostics.", args.json, exit_code=2)
        if args.session_output_context_max != 20 and not session_output_analysis:
            return print_error_result("--session-output-context-max can only be used with --session-output-contexts or --session-output-diagnostics.", args.json, exit_code=2)
        if args.session_output_context_max_bytes != 20_000 and not session_output_analysis:
            return print_error_result("--session-output-context-max-bytes can only be used with --session-output-contexts or --session-output-diagnostics.", args.json, exit_code=2)
        if args.session_output_diagnostic_max != 50 and args.session_output_diagnostics is None:
            return print_error_result("--session-output-diagnostic-max can only be used with --session-output-diagnostics.", args.json, exit_code=2)
        if args.checks_max != 20 and not args.checks:
            return print_error_result("--checks-max can only be used with --checks.", args.json, exit_code=2)
        if args.check_suggested_checks_max != 10 and args.check_suggested_checks is None:
            return print_error_result("--check-suggested-checks-max can only be used with --check-suggested-checks.", args.json, exit_code=2)
        if args.run_suggested_checks_max != 10 and args.run_suggested_checks is None:
            return print_error_result("--run-suggested-checks-max can only be used with --run-suggested-checks.", args.json, exit_code=2)
        session_transcript_view = args.transcript is not None
        session_search_view = args.session_search is not None
        session_command_view = args.session_commands is not None or args.session_audit is not None or args.session_handoff is not None
        session_file_view = args.session_files is not None or args.session_audit is not None or args.session_handoff is not None
        session_failure_view = args.session_failures is not None or args.session_audit is not None or args.session_handoff is not None
        session_text_view = session_transcript_view or session_search_view or args.session_failures is not None or args.session_audit is not None or args.session_handoff is not None
        if args.session_transcript_event_max is not None and not session_transcript_view:
            return print_error_result("--session-transcript-event-max can only be used with --transcript.", args.json, exit_code=2)
        if args.session_search_match_max is not None and not session_search_view:
            return print_error_result("--session-search-match-max can only be used with --session-search.", args.json, exit_code=2)
        if args.session_search_case_sensitive and not session_search_view:
            return print_error_result("--session-search-case-sensitive can only be used with --session-search.", args.json, exit_code=2)
        if args.session_max_checks is not None and args.session_verification is None and args.session_audit is None and args.session_handoff is None:
            return print_error_result("--session-max-checks can only be used with --session-verification, --session-audit, or --session-handoff.", args.json, exit_code=2)
        if args.session_max_commands is not None and not session_command_view:
            return print_error_result("--session-max-commands can only be used with --session-commands, --session-audit, or --session-handoff.", args.json, exit_code=2)
        if args.session_max_output_chars is not None and args.session_commands is None and args.session_handoff is None:
            return print_error_result("--session-max-output-chars can only be used with --session-commands or --session-handoff.", args.json, exit_code=2)
        if args.session_max_files is not None and not session_file_view:
            return print_error_result("--session-max-files can only be used with --session-files, --session-audit, or --session-handoff.", args.json, exit_code=2)
        if args.session_max_failures is not None and not session_failure_view:
            return print_error_result("--session-max-failures can only be used with --session-failures, --session-audit, or --session-handoff.", args.json, exit_code=2)
        if args.session_max_text is not None and not session_text_view:
            return print_error_result("--session-max-text can only be used with --transcript, --session-search, --session-failures, --session-audit, or --session-handoff.", args.json, exit_code=2)
        if args.tail_lines != 80 and args.tail is None:
            return print_error_result("--tail-lines can only be used with --tail.", args.json, exit_code=2)
        if args.tail_max_bytes is not None and args.tail is None:
            return print_error_result("--tail-max-bytes can only be used with --tail.", args.json, exit_code=2)
        if args.log_count != 5 and args.log is None:
            return print_error_result("--log-count can only be used with --log.", args.json, exit_code=2)
        if args.show_path and args.show is None:
            return print_error_result("--show-path can only be used with --show.", args.json, exit_code=2)
        if args.show_max_chars != 12000 and args.show is None:
            return print_error_result("--show-max-chars can only be used with --show.", args.json, exit_code=2)
        if args.blame_lines and args.blame is None:
            return print_error_result("--blame-lines can only be used with --blame.", args.json, exit_code=2)
        if args.blame_max_chars != 12000 and args.blame is None:
            return print_error_result("--blame-max-chars can only be used with --blame.", args.json, exit_code=2)
        if args.review_max_files != 200 and not args.review:
            return print_error_result("--review-max-files can only be used with --review.", args.json, exit_code=2)
        if args.review_max_checks != 5 and not args.review:
            return print_error_result("--review-max-checks can only be used with --review.", args.json, exit_code=2)
        if args.handoff_max_files != 200 and not args.handoff:
            return print_error_result("--handoff-max-files can only be used with --handoff.", args.json, exit_code=2)
        if args.handoff_max_checks != 10 and not args.handoff:
            return print_error_result("--handoff-max-checks can only be used with --handoff.", args.json, exit_code=2)
        if args.handoff_max_status_chars != 4_000 and not args.handoff:
            return print_error_result("--handoff-max-status-chars can only be used with --handoff.", args.json, exit_code=2)
        if args.handoff_max_plan_chars != 4_000 and not args.handoff:
            return print_error_result("--handoff-max-plan-chars can only be used with --handoff.", args.json, exit_code=2)
        if args.changes_max_files != 200 and not args.changes:
            return print_error_result("--changes-max-files can only be used with --changes.", args.json, exit_code=2)
        if args.stash_count != 20 and not args.stashes:
            return print_error_result("--stash-count can only be used with --stashes.", args.json, exit_code=2)
        if args.stash_include_untracked and args.check_git_stash is None and args.git_stash is None:
            return print_error_result("--stash-include-untracked can only be used with --check-git-stash or --git-stash.", args.json, exit_code=2)
        if args.diff_max_chars != 12_000 and args.diff is None:
            return print_error_result("--diff-max-chars can only be used with --diff.", args.json, exit_code=2)
        if args.diff_hunks_max_hunks != 80 and args.diff_hunks is None:
            return print_error_result("--diff-hunks-max-hunks can only be used with --diff-hunks.", args.json, exit_code=2)
        if args.diff_hunks_max_lines != 80 and args.diff_hunks is None:
            return print_error_result("--diff-hunks-max-lines can only be used with --diff-hunks.", args.json, exit_code=2)
        if args.diff_context_lines != 5 and args.diff_contexts is None:
            return print_error_result("--diff-context-lines can only be used with --diff-contexts.", args.json, exit_code=2)
        if args.diff_contexts_max_hunks != 80 and args.diff_contexts is None:
            return print_error_result("--diff-contexts-max-hunks can only be used with --diff-contexts.", args.json, exit_code=2)
        if args.diff_contexts_max_bytes != 20_000 and args.diff_contexts is None:
            return print_error_result("--diff-contexts-max-bytes can only be used with --diff-contexts.", args.json, exit_code=2)
        if args.git_switch_create and args.check_git_switch is None and args.git_switch is None:
            return print_error_result("--git-switch-create can only be used with --check-git-switch or --git-switch.", args.json, exit_code=2)
        process_output_analysis = args.process_output_contexts is not None or args.process_output_diagnostics is not None
        if args.process_max_chars != 4000 and args.process_output is None and not process_output_analysis:
            return print_error_result("--process-max-chars can only be used with --process-output, --process-output-contexts, or --process-output-diagnostics.", args.json, exit_code=2)
        if args.process_output_context_lines != 5 and not process_output_analysis:
            return print_error_result("--process-output-context-lines can only be used with --process-output-contexts or --process-output-diagnostics.", args.json, exit_code=2)
        if args.process_output_context_max != 20 and not process_output_analysis:
            return print_error_result("--process-output-context-max can only be used with --process-output-contexts or --process-output-diagnostics.", args.json, exit_code=2)
        if args.process_output_context_max_bytes != 20000 and not process_output_analysis:
            return print_error_result("--process-output-context-max-bytes can only be used with --process-output-contexts or --process-output-diagnostics.", args.json, exit_code=2)
        if args.process_output_diagnostic_max != 50 and args.process_output_diagnostics is None:
            return print_error_result("--process-output-diagnostic-max can only be used with --process-output-diagnostics.", args.json, exit_code=2)
        if args.wait_timeout_ms != 5000 and args.wait_process is None:
            return print_error_result("--wait-timeout-ms can only be used with --wait-process.", args.json, exit_code=2)
        if args.wait_max_chars != 4000 and args.wait_process is None:
            return print_error_result("--wait-max-chars can only be used with --wait-process.", args.json, exit_code=2)
        if args.wait_stdout and args.wait_process is None:
            return print_error_result("--wait-stdout can only be used with --wait-process.", args.json, exit_code=2)
        if args.wait_stderr and args.wait_process is None:
            return print_error_result("--wait-stderr can only be used with --wait-process.", args.json, exit_code=2)
        if args.wait_regex and args.wait_process is None:
            return print_error_result("--wait-regex can only be used with --wait-process.", args.json, exit_code=2)
        write_stdin_target = args.check_write_process is not None or args.write_process is not None
        if args.write_stdin is not None and not write_stdin_target:
            return print_error_result("--write-stdin can only be used with --check-write-process or --write-process.", args.json, exit_code=2)
        if args.check_write_process is not None and args.write_stdin is None:
            return print_error_result("--check-write-process requires --write-stdin.", args.json, exit_code=2)
        if args.write_process is not None and args.write_stdin is None:
            return print_error_result("--write-process requires --write-stdin.", args.json, exit_code=2)
        run_target = args.run_command is not None or args.run_commands is not None or args.run_suggested_checks is not None or args.run_focused_tests is not None
        if args.run_timeout_ms != 30000 and not run_target:
            return print_error_result("--run-timeout-ms can only be used with --run-command, --run-commands, --run-suggested-checks, or --run-focused-tests.", args.json, exit_code=2)
        if args.run_max_chars != 12000 and not run_target:
            return print_error_result("--run-max-chars can only be used with --run-command, --run-commands, --run-suggested-checks, or --run-focused-tests.", args.json, exit_code=2)
        if args.run_continue_on_failure and args.run_commands is None and args.run_suggested_checks is None and args.run_focused_tests is None:
            return print_error_result("--run-continue-on-failure can only be used with --run-commands, --run-suggested-checks, or --run-focused-tests.", args.json, exit_code=2)
        run_output_context_target = run_target
        if args.run_output_contexts and not run_output_context_target:
            return print_error_result("--run-output-contexts can only be used with --run-command, --run-commands, --run-suggested-checks, or --run-focused-tests.", args.json, exit_code=2)
        if args.run_output_diagnostics and not run_output_context_target:
            return print_error_result("--run-output-diagnostics can only be used with --run-command, --run-commands, --run-suggested-checks, or --run-focused-tests.", args.json, exit_code=2)
        if args.run_output_context_lines != 5 and not run_target:
            return print_error_result("--run-output-context-lines can only be used with --run-command, --run-commands, --run-suggested-checks, or --run-focused-tests.", args.json, exit_code=2)
        if args.run_output_context_max != 20 and not run_target:
            return print_error_result("--run-output-context-max can only be used with --run-command, --run-commands, --run-suggested-checks, or --run-focused-tests.", args.json, exit_code=2)
        if args.run_output_context_max_bytes != 20000 and not run_target:
            return print_error_result("--run-output-context-max-bytes can only be used with --run-command, --run-commands, --run-suggested-checks, or --run-focused-tests.", args.json, exit_code=2)
        if args.run_output_diagnostic_max != 50 and not run_target:
            return print_error_result("--run-output-diagnostic-max can only be used with --run-command, --run-commands, --run-suggested-checks, or --run-focused-tests.", args.json, exit_code=2)
        if args.resume is not None and args.compact is not None:
            return print_error_result("--resume and --compact cannot be used together.", args.json, exit_code=2)
        resume_limit_options = {
            "--resume-max-failures": args.resume_max_failures,
            "--resume-max-files": args.resume_max_files,
            "--resume-max-commands": args.resume_max_commands,
            "--resume-max-checks": args.resume_max_checks,
            "--resume-max-output-chars": args.resume_max_output_chars,
            "--resume-max-text": args.resume_max_text,
        }
        compact_limit_options = {
            "--compact-max-failures": args.compact_max_failures,
            "--compact-max-files": args.compact_max_files,
            "--compact-max-commands": args.compact_max_commands,
            "--compact-max-checks": args.compact_max_checks,
            "--compact-max-output-chars": args.compact_max_output_chars,
            "--compact-max-text": args.compact_max_text,
        }
        for option, value in resume_limit_options.items():
            if value is not None and args.resume is None:
                return print_error_result(f"{option} can only be used with --resume.", args.json, exit_code=2)
        for option, value in compact_limit_options.items():
            if value is not None and args.compact is None:
                return print_error_result(f"{option} can only be used with --compact.", args.json, exit_code=2)
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


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="vibeagent", description="Run VibeAgent interactively or execute one task.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--chat", action="store_true", help="Run the one-shot task in daily conversation mode.")
    mode.add_argument("--code", action="store_true", help="Run the one-shot task in coding mode. This is the default.")
    local = parser.add_mutually_exclusive_group()
    local.add_argument("--model", action="store_true", help="Show model provider configuration and exit.")
    local.add_argument("--config", action="store_true", help="Show resolved provider and execution configuration and exit.")
    local.add_argument("--tools", action="store_true", help="Show model tool names by category and exit.")
    local.add_argument("--tool", metavar="NAME", help="Show one model tool's description and input schema and exit.")
    local.add_argument("--permissions", action="store_true", help="Show approval-gated tools and hard command blocks and exit.")
    local.add_argument("--checks", action="store_true", help="Show suggested test, build, and lint commands and exit.")
    parser.add_argument("--checks-max", type=positive_int, default=20, metavar="N", help="Maximum suggested checks to show with --checks.")
    local.add_argument("--check-suggested-checks", nargs="?", const="", metavar="N", help="Preflight suggested test, build, and lint commands and exit.")
    parser.add_argument("--check-suggested-checks-max", type=positive_int, default=10, metavar="N", help="Maximum suggested checks to preflight with --check-suggested-checks.")
    local.add_argument("--run-suggested-checks", nargs="?", const="", metavar="N", help="Run suggested test, build, and lint commands and exit.")
    parser.add_argument("--run-suggested-checks-max", type=positive_int, default=10, metavar="N", help="Maximum suggested checks to run with --run-suggested-checks.")
    local.add_argument("--commands", action="store_true", help="Show project-defined commands from manifests and exit.")
    local.add_argument("--related-tests", nargs="*", metavar="PATH", help="Suggest test files related to paths or current git changes and exit.")
    local.add_argument("--focused-tests", nargs="*", metavar="PATH", help="Suggest focused test commands related to paths or current git changes and exit.")
    local.add_argument("--check-focused-tests", nargs="*", metavar="PATH", help="Preflight focused test commands related to paths or current git changes and exit.")
    local.add_argument("--run-focused-tests", nargs="*", metavar="PATH", help="Run focused test commands related to paths or current git changes and exit.")
    local.add_argument("--manifests", action="store_true", help="Show package and pyproject manifest metadata and exit.")
    local.add_argument("--instructions", action="store_true", help="Show AGENTS.md and CLAUDE.md instruction sources and exit.")
    local.add_argument("--todos", nargs="?", const="", metavar="PATH", help="Show TODO, FIXME, HACK, XXX, and BUG markers and exit.")
    local.add_argument("--command-check", metavar="COMMAND", help="Preview whether one shell command can run and exit.")
    local.add_argument("--run-command", metavar="COMMAND", help="Run one finite shell command with safety checks and exit.")
    local.add_argument("--check-run-commands", nargs="+", metavar="COMMAND", help="Preview a short ordered command sequence and exit.")
    local.add_argument("--run-commands", nargs="+", metavar="COMMAND", help="Run a short ordered command sequence and exit.")
    local.add_argument("--check-start-command", metavar="COMMAND", help="Preview starting one long-running shell command and exit.")
    local.add_argument("--start-command", metavar="COMMAND", help="Start one long-running shell command and exit.")
    local.add_argument("--port-check", type=positive_int, metavar="PORT", help="Check whether one local TCP port is reachable and exit.")
    local.add_argument("--http-check", metavar="URL", help="Check HTTP status and optional response text and exit.")
    local.add_argument("--http-fetch", metavar="URL", help="Fetch bounded HTTP response metadata and body text and exit.")
    local.add_argument("--overview", action="store_true", help="Show a compact project orientation bundle and exit.")
    local.add_argument("--repo-map", nargs="?", const="", metavar="PATH", help="Show a bounded repository tree and source symbol map and exit.")
    local.add_argument("--search", metavar="QUERY", help="Search project text with gitignore and safety filtering and exit.")
    local.add_argument("--search-contexts", metavar="QUERY", help="Search project text and show line-centered context snippets and exit.")
    local.add_argument("--glob", metavar="PATTERN", help="Find project files by glob pattern and exit.")
    local.add_argument("--tree", nargs="?", const="", metavar="PATH", help="Show a bounded project directory tree and exit.")
    local.add_argument("--symbols", nargs="+", metavar="PATH", help="Show source imports and symbol outlines and exit.")
    local.add_argument("--file-info", nargs="+", metavar="PATH", help="Show file, directory, size, and line metadata and exit.")
    local.add_argument("--image-info", nargs="+", metavar="PATH", help="Show image format, byte size, and dimensions and exit.")
    local.add_argument("--read", metavar="PATH", help="Read one project file and exit.")
    local.add_argument("--around", nargs=2, metavar=("PATH", "LINE"), help="Read one project file line with surrounding context and exit.")
    local.add_argument("--around-many", nargs="+", metavar="PATH:LINE[:CONTEXT]", help="Read several project file lines with surrounding context and exit.")
    local.add_argument("--output-contexts", metavar="TEXT", help="Extract file:line references from command output and read contexts.")
    local.add_argument("--output-diagnostics", metavar="TEXT", help="Summarize command output diagnostics and read referenced contexts.")
    local.add_argument("--python-traceback", metavar="TEXT", help="Summarize Python traceback or pytest exception output and read referenced contexts.")
    local.add_argument("--tail", metavar="PATH", help="Read the last lines of one project file and exit.")
    local.add_argument("--read-files", nargs="+", metavar="PATH", help="Read multiple project files and exit.")
    local.add_argument("--read-ranges", nargs="+", metavar="PATH:START[:END]", help="Read multiple focused project file line ranges and exit.")
    local.add_argument("--python-check", nargs="?", const="", metavar="PATH", help="Check Python syntax and exit.")
    local.add_argument("--python-deps", nargs="?", const="", metavar="PATH", help="Inspect Python imports and dependencies and exit.")
    local.add_argument("--python-defs", metavar="SYMBOL", help="Find Python class/function definitions and exit.")
    local.add_argument("--python-refs", metavar="SYMBOL", help="Find Python definitions, imports, and references and exit.")
    local.add_argument("--python-ref-contexts", metavar="SYMBOL", help="Find Python references with surrounding context and exit.")
    local.add_argument("--python-calls", metavar="SYMBOL", help="Find Python call sites for a symbol and exit.")
    local.add_argument("--python-call-graph", nargs="?", const="", metavar="PATH", help="Inspect Python caller-to-callee edges and exit.")
    local.add_argument("--python-rename-preview", nargs=2, metavar=("SYMBOL", "NEW_NAME"), help="Preview a Python symbol rename and exit.")
    local.add_argument("--python-rename", nargs=2, metavar=("SYMBOL", "NEW_NAME"), help="Rename a Python symbol and exit.")
    local.add_argument("--check-replace-python-def", nargs=2, metavar=("SYMBOL", "CONTENT"), help="Preview replacing one Python class/function definition and exit.")
    local.add_argument("--replace-python-def", nargs=2, metavar=("SYMBOL", "CONTENT"), help="Replace one Python class/function definition and exit.")
    local.add_argument("--config-check", nargs="?", const="", metavar="PATH", help="Check JSON/YAML/TOML config syntax and exit.")
    local.add_argument("--check-json-set", nargs=3, metavar=("PATH", "POINTER", "JSON_VALUE"), help="Preview updating one JSON value and exit.")
    local.add_argument("--json-set", nargs=3, metavar=("PATH", "POINTER", "JSON_VALUE"), help="Update one JSON value and exit.")
    parser.add_argument("--json-create-missing", action="store_true", help="Create missing JSON object parents with --check-json-set or --json-set.")
    local.add_argument("--check-json-remove", nargs=2, metavar=("PATH", "POINTER"), help="Preview removing one JSON value and exit.")
    local.add_argument("--json-remove", nargs=2, metavar=("PATH", "POINTER"), help="Remove one JSON value and exit.")
    local.add_argument("--check-json-patch", nargs=2, metavar=("PATH", "JSON_OPS"), help="Preview JSON Patch operations and exit.")
    local.add_argument("--json-patch", nargs=2, metavar=("PATH", "JSON_OPS"), help="Apply JSON Patch operations and exit.")
    local.add_argument("--check-replace-lines", nargs=4, metavar=("PATH", "START", "END", "TEXT"), help="Preview replacing an inclusive line range and exit.")
    local.add_argument("--replace-lines", nargs=4, metavar=("PATH", "START", "END", "TEXT"), help="Replace an inclusive line range and exit.")
    local.add_argument("--check-insert-lines", nargs=3, metavar=("PATH", "LINE", "TEXT"), help="Preview inserting text before a line and exit.")
    local.add_argument("--insert-lines", nargs=3, metavar=("PATH", "LINE", "TEXT"), help="Insert text before a line and exit.")
    local.add_argument("--check-append", nargs=2, metavar=("PATH", "TEXT"), help="Preview appending text to one file and exit.")
    local.add_argument("--append", nargs=2, metavar=("PATH", "TEXT"), help="Append text to one file and exit.")
    local.add_argument("--check-write", nargs=2, metavar=("PATH", "TEXT"), help="Preview writing one file and exit.")
    local.add_argument("--write", nargs=2, metavar=("PATH", "TEXT"), help="Write one file and exit.")
    local.add_argument("--check-write-files", nargs="+", metavar="ARG", help="Preview writing multiple files and exit. Usage: --check-write-files PATH TEXT [PATH TEXT ...].")
    local.add_argument("--write-files", nargs="+", metavar="ARG", help="Write multiple files and exit. Usage: --write-files PATH TEXT [PATH TEXT ...].")
    local.add_argument("--check-edit", nargs=3, metavar=("PATH", "OLD", "NEW"), help="Preview replacing exact text in one file and exit.")
    local.add_argument("--edit", nargs=3, metavar=("PATH", "OLD", "NEW"), help="Replace exact text in one file and exit.")
    local.add_argument("--check-multi-edit", nargs="+", metavar="ARG", help="Preview multiple exact replacements in one file and exit. Usage: --check-multi-edit PATH OLD NEW [OLD NEW ...].")
    local.add_argument("--multi-edit", nargs="+", metavar="ARG", help="Apply multiple exact replacements in one file and exit. Usage: --multi-edit PATH OLD NEW [OLD NEW ...].")
    local.add_argument("--check-delete", metavar="PATH", help="Preview deleting one file and exit.")
    local.add_argument("--delete", metavar="PATH", help="Delete one file and exit.")
    local.add_argument("--check-delete-files", nargs="+", metavar="PATH", help="Preview deleting multiple files and exit.")
    local.add_argument("--delete-files", nargs="+", metavar="PATH", help="Delete multiple files and exit.")
    local.add_argument("--check-move", nargs=2, metavar=("SOURCE", "DESTINATION"), help="Preview moving one file and exit.")
    local.add_argument("--move", nargs=2, metavar=("SOURCE", "DESTINATION"), help="Move one file and exit.")
    local.add_argument("--check-move-files", nargs="+", metavar="ARG", help="Preview moving multiple files and exit. Usage: --check-move-files SOURCE DESTINATION [SOURCE DESTINATION ...].")
    local.add_argument("--move-files", nargs="+", metavar="ARG", help="Move multiple files and exit. Usage: --move-files SOURCE DESTINATION [SOURCE DESTINATION ...].")
    local.add_argument("--check-copy", nargs=2, metavar=("SOURCE", "DESTINATION"), help="Preview copying one file and exit.")
    local.add_argument("--copy", nargs=2, metavar=("SOURCE", "DESTINATION"), help="Copy one file and exit.")
    local.add_argument("--check-copy-files", nargs="+", metavar="ARG", help="Preview copying multiple files and exit. Usage: --check-copy-files SOURCE DESTINATION [SOURCE DESTINATION ...].")
    local.add_argument("--copy-files", nargs="+", metavar="ARG", help="Copy multiple files and exit. Usage: --copy-files SOURCE DESTINATION [SOURCE DESTINATION ...].")
    local.add_argument("--check-move-dir", nargs=2, metavar=("SOURCE", "DESTINATION"), help="Preview moving one directory and exit.")
    local.add_argument("--move-dir", nargs=2, metavar=("SOURCE", "DESTINATION"), help="Move one directory and exit.")
    local.add_argument("--check-move-dirs", nargs="+", metavar="ARG", help="Preview moving multiple directories and exit. Usage: --check-move-dirs SOURCE DESTINATION [SOURCE DESTINATION ...].")
    local.add_argument("--move-dirs", nargs="+", metavar="ARG", help="Move multiple directories and exit. Usage: --move-dirs SOURCE DESTINATION [SOURCE DESTINATION ...].")
    local.add_argument("--check-copy-dir", nargs=2, metavar=("SOURCE", "DESTINATION"), help="Preview copying one directory and exit.")
    local.add_argument("--copy-dir", nargs=2, metavar=("SOURCE", "DESTINATION"), help="Copy one directory and exit.")
    local.add_argument("--check-copy-dirs", nargs="+", metavar="ARG", help="Preview copying multiple directories and exit. Usage: --check-copy-dirs SOURCE DESTINATION [SOURCE DESTINATION ...].")
    local.add_argument("--copy-dirs", nargs="+", metavar="ARG", help="Copy multiple directories and exit. Usage: --copy-dirs SOURCE DESTINATION [SOURCE DESTINATION ...].")
    local.add_argument("--check-mkdir", metavar="PATH", help="Preview creating one directory and exit.")
    local.add_argument("--mkdir", metavar="PATH", help="Create one directory and exit.")
    local.add_argument("--check-mkdirs", nargs="+", metavar="PATH", help="Preview creating multiple directories and exit.")
    local.add_argument("--mkdirs", nargs="+", metavar="PATH", help="Create multiple directories and exit.")
    local.add_argument("--check-rmdir", metavar="PATH", help="Preview deleting one empty directory and exit.")
    local.add_argument("--rmdir", metavar="PATH", help="Delete one empty directory and exit.")
    local.add_argument("--check-rmdirs", nargs="+", metavar="PATH", help="Preview deleting multiple empty directories and exit.")
    local.add_argument("--rmdirs", nargs="+", metavar="PATH", help="Delete multiple empty directories and exit.")
    local.add_argument("--check-executable", nargs="+", metavar="ARG", help="Preview changing one file's executable bit and exit. Usage: --check-executable PATH [true|false].")
    local.add_argument("--set-executable", nargs="+", metavar="ARG", help="Change one file's executable bit and exit. Usage: --set-executable PATH [true|false].")
    local.add_argument("--check-patch", nargs=2, metavar=("PATH", "PATCH"), help="Preview applying one unified diff hunk to a file and exit. Use PATCH=- to read stdin.")
    local.add_argument("--patch", nargs=2, metavar=("PATH", "PATCH"), help="Apply one unified diff hunk to a file and exit. Use PATCH=- to read stdin.")
    local.add_argument("--check-patches", metavar="PATCH", help="Preview applying one unified diff across files and exit. Use PATCH=- to read stdin.")
    local.add_argument("--patches", metavar="PATCH", help="Apply one unified diff across files and exit. Use PATCH=- to read stdin.")
    local.add_argument("--check-regex-replace", nargs=3, metavar=("PATH", "PATTERN", "REPLACEMENT"), help="Preview a regex replacement and exit.")
    local.add_argument("--regex-replace", nargs=3, metavar=("PATH", "PATTERN", "REPLACEMENT"), help="Apply a regex replacement and exit.")
    local.add_argument("--code-deps", nargs="?", const="", metavar="PATH", help="Inspect non-Python source imports and dependencies and exit.")
    local.add_argument("--code-refs", metavar="SYMBOL", help="Find non-Python source references for a symbol and exit.")
    local.add_argument("--code-ref-contexts", metavar="SYMBOL", help="Find non-Python source references with surrounding context and exit.")
    local.add_argument("--code-defs", metavar="SYMBOL", help="Find non-Python source definitions for a symbol and exit.")
    local.add_argument("--code-rename-preview", nargs=2, metavar=("SYMBOL", "NEW_NAME"), help="Preview a non-Python source symbol or literal rename and exit.")
    local.add_argument("--code-rename", nargs=2, metavar=("SYMBOL", "NEW_NAME"), help="Rename a non-Python source symbol or literal and exit.")
    local.add_argument("--git-status", action="store_true", help="Show raw short git status and exit.")
    local.add_argument("--conflicts", nargs="?", const="", metavar="PATH", help="Scan for unmerged git files and conflict marker lines and exit.")
    local.add_argument("--git-info", action="store_true", help="Show git branch, HEAD, upstream, remotes, and short status and exit.")
    local.add_argument("--branches", action="store_true", help="Show local git branches and current branch and exit.")
    local.add_argument("--log", nargs="?", const="", metavar="PATH", help="Show recent git commits, optionally scoped to one path, and exit.")
    local.add_argument("--show", nargs="?", const="HEAD", metavar="REV", help="Show one git revision with stat and patch and exit.")
    local.add_argument("--blame", metavar="PATH", help="Show git blame for one file and exit.")
    local.add_argument("--stashes", action="store_true", help="Show local git stash entries and exit.")
    local.add_argument("--check-git-fetch", nargs="?", const="", metavar="REMOTE", help="Preview selecting a git remote to fetch and exit.")
    local.add_argument("--git-fetch", nargs="?", const="", metavar="REMOTE", help="Run git fetch --prune for one remote and exit.")
    local.add_argument("--check-git-pull", action="store_true", help="Preview fast-forward pulling the current upstream and exit.")
    local.add_argument("--git-pull", action="store_true", help="Fast-forward pull the current upstream and exit.")
    local.add_argument("--check-git-push", action="store_true", help="Preview pushing the current branch to upstream and exit.")
    local.add_argument("--git-push", action="store_true", help="Push the current branch to upstream and exit.")
    local.add_argument("--check-git-stash", nargs="?", const="", metavar="MESSAGE", help="Preview saving non-runtime changes to git stash and exit.")
    local.add_argument("--git-stash", nargs="?", const="", metavar="MESSAGE", help="Save non-runtime changes to git stash and exit.")
    local.add_argument("--check-git-stash-apply", metavar="STASH_REF", help="Preview applying a stash to a clean worktree and exit.")
    local.add_argument("--git-stash-apply", metavar="STASH_REF", help="Apply a stash to a clean worktree and exit.")
    local.add_argument("--check-git-stash-drop", metavar="STASH_REF", help="Preview deleting a stash entry and exit.")
    local.add_argument("--git-stash-drop", metavar="STASH_REF", help="Delete a stash entry and exit.")
    local.add_argument("--check-git-stage", nargs="+", metavar="PATH", help="Preview staging explicit project paths and exit.")
    local.add_argument("--git-stage", nargs="+", metavar="PATH", help="Stage explicit project paths and exit.")
    local.add_argument("--check-git-unstage", nargs="+", metavar="PATH", help="Preview unstaging explicit project paths and exit.")
    local.add_argument("--git-unstage", nargs="+", metavar="PATH", help="Unstage explicit project paths and exit.")
    local.add_argument("--check-git-commit", metavar="MESSAGE", help="Preview committing currently staged changes and exit.")
    local.add_argument("--git-commit", metavar="MESSAGE", help="Commit currently staged changes and exit.")
    local.add_argument("--check-git-restore", nargs="+", metavar="PATH", help="Preview discarding unstaged tracked-file changes and exit.")
    local.add_argument("--git-restore", nargs="+", metavar="PATH", help="Discard unstaged tracked-file changes and exit.")
    local.add_argument("--check-git-switch", metavar="BRANCH", help="Preview switching or creating a local branch and exit.")
    local.add_argument("--git-switch", metavar="BRANCH", help="Switch or create a local branch and exit.")
    local.add_argument("--env", action="store_true", help="Show local OS, runtime, and tool availability and exit.")
    local.add_argument("--processes", action="store_true", help="Show VibeAgent-started background processes and exit.")
    local.add_argument("--process-output", metavar="ID", help="Show captured stdout and stderr for one VibeAgent-started background process and exit.")
    local.add_argument("--process-output-contexts", metavar="ID", help="Extract file:line source contexts from one background process output and exit.")
    local.add_argument("--process-output-diagnostics", metavar="ID", help="Summarize diagnostics from one background process output and exit.")
    local.add_argument("--wait-process", metavar="ID", help="Wait briefly for one VibeAgent-started background process and exit.")
    local.add_argument("--check-write-process", metavar="ID", help="Preview writing stdin text to one VibeAgent-started background process and exit.")
    local.add_argument("--write-process", metavar="ID", help="Write stdin text to one VibeAgent-started background process and exit.")
    local.add_argument("--check-stop-process", metavar="ID", help="Preview stopping one VibeAgent-started background process and exit.")
    local.add_argument("--stop-process", metavar="ID", help="Stop one VibeAgent-started background process and exit.")
    local.add_argument("--check-stop-all-processes", action="store_true", help="Preview stopping all VibeAgent-started background processes and exit.")
    local.add_argument("--stop-all-processes", action="store_true", help="Stop all VibeAgent-started background processes and exit.")
    local.add_argument("--status", action="store_true", help="Show default non-interactive status and exit.")
    local.add_argument("--context", action="store_true", help="Show project context sources and exit.")
    local.add_argument("--init", nargs="?", const="AGENTS.md", metavar="FILE", help="Create a starter AGENTS.md or CLAUDE.md and exit.")
    local.add_argument("--doctor", action="store_true", help="Show local diagnostics and exit.")
    local.add_argument("--review", action="store_true", help="Review current git changes, syntax checks, and suggested commands and exit.")
    parser.add_argument("--review-max-files", type=positive_int, default=200, metavar="N", help="Maximum changed files to show with --review.")
    parser.add_argument("--review-max-checks", type=positive_int, default=5, metavar="N", help="Maximum suggested checks to show with --review.")
    local.add_argument("--handoff", action="store_true", help="Show final handoff review, checks, changed files, and latest plan and exit.")
    parser.add_argument("--handoff-max-files", type=positive_int, default=200, metavar="N", help="Maximum changed files to show with --handoff.")
    parser.add_argument("--handoff-max-checks", type=positive_int, default=10, metavar="N", help="Maximum suggested checks to show with --handoff.")
    parser.add_argument("--handoff-max-status-chars", type=positive_int, default=4_000, metavar="N", help="Maximum git status characters to show with --handoff.")
    parser.add_argument("--handoff-max-plan-chars", type=positive_int, default=4_000, metavar="N", help="Maximum latest-plan characters to show with --handoff.")
    local.add_argument("--changes", action="store_true", help="Show a structured changed-file summary and exit.")
    parser.add_argument("--changes-max-files", type=positive_int, default=200, metavar="N", help="Maximum changed files to show with --changes.")
    local.add_argument("--diff", nargs="?", const="", metavar="ARGS", help="Show current git diff. Optional ARGS: '--staged [path]' or '[path]'.")
    local.add_argument("--diff-hunks", nargs="?", const="", metavar="ARGS", help="Show structured git diff hunks. Optional ARGS: '--staged [path]' or '[path]'.")
    local.add_argument("--diff-contexts", nargs="?", const="", metavar="ARGS", help="Show source context around git diff hunks. Optional ARGS: '--staged [path]' or '[path]'.")
    parser.add_argument("--diff-max-chars", type=positive_int, default=12_000, metavar="N", help="Maximum raw diff characters to show with --diff.")
    parser.add_argument("--diff-hunks-max-hunks", type=positive_int, default=80, metavar="N", help="Maximum hunks to show with --diff-hunks.")
    parser.add_argument("--diff-hunks-max-lines", type=positive_int, default=80, metavar="N", help="Maximum patch lines per hunk with --diff-hunks.")
    parser.add_argument("--diff-context-lines", type=nonnegative_int, default=5, metavar="N", help="Surrounding source lines for --diff-contexts.")
    parser.add_argument("--diff-contexts-max-hunks", type=positive_int, default=80, metavar="N", help="Maximum hunks to inspect with --diff-contexts.")
    parser.add_argument("--diff-contexts-max-bytes", type=positive_int, default=20_000, metavar="N", help="Maximum bytes per source context with --diff-contexts.")
    parser.add_argument("--staged", "--cached", action="store_true", dest="diff_staged", help="Show staged changes with --diff, --diff-hunks, or --diff-contexts.")
    parser.add_argument("--command-cwd", metavar="PATH", help="Project-relative command cwd for --command-check.")
    parser.add_argument("--run-cwd", metavar="PATH", help="Project-relative command cwd for --run-command, --run-commands, or --check-run-commands.")
    parser.add_argument("--start-cwd", metavar="PATH", help="Project-relative command cwd for --check-start-command or --start-command.")
    parser.add_argument("--port-host", default="127.0.0.1", metavar="HOST", help="TCP host for --port-check.")
    parser.add_argument("--port-timeout-ms", type=timeout_ms, default=1_000, metavar="N", help="Maximum milliseconds for --port-check.")
    parser.add_argument("--http-timeout-ms", type=timeout_ms, metavar="N", help="Maximum milliseconds for --http-check or --http-fetch.")
    parser.add_argument("--http-max-body-chars", type=positive_int, metavar="N", help="Maximum response body characters for --http-check or --http-fetch.")
    parser.add_argument("--http-contains", metavar="TEXT", help="Require response body text for --http-check.")
    parser.add_argument("--http-regex", action="store_true", help="Treat --http-contains as a regular expression.")
    parser.add_argument("--search-path", metavar="PATH", help="Project-relative search scope for --search.")
    parser.add_argument("--search-max-matches", type=positive_int, metavar="N", help="Maximum matches to show with --search or --search-contexts.")
    parser.add_argument("--search-regex", action="store_true", help="Treat --search or --search-contexts query as a regular expression.")
    parser.add_argument("--search-ignore-case", action="store_true", help="Use case-insensitive matching with --search or --search-contexts.")
    parser.add_argument("--search-context-lines", type=nonnegative_int, metavar="N", help="Surrounding source lines for --search or --search-contexts.")
    parser.add_argument("--search-context-max-bytes", type=positive_int, metavar="N", help="Maximum bytes per context with --search-contexts.")
    parser.add_argument("--related-tests-max-paths", type=positive_int, metavar="N", help="Maximum source paths to consider with --related-tests.")
    parser.add_argument("--related-tests-max-candidates", type=positive_int, metavar="N", help="Maximum related test candidates to show with --related-tests.")
    parser.add_argument("--focused-tests-max-paths", type=positive_int, metavar="N", help="Maximum source paths to consider with --focused-tests, --check-focused-tests, or --run-focused-tests.")
    parser.add_argument("--focused-tests-max-candidates", type=positive_int, metavar="N", help="Maximum related test candidates to consider with focused test commands.")
    parser.add_argument("--focused-tests-max-commands", type=positive_int, metavar="N", help="Maximum focused test commands to show, preflight, or run.")
    parser.add_argument("--commands-max-commands", type=positive_int, metavar="N", help="Maximum project commands to show with --commands.")
    parser.add_argument("--commands-max-files", type=positive_int, metavar="N", help="Maximum command metadata files to scan with --commands.")
    parser.add_argument("--manifests-max-files", type=positive_int, metavar="N", help="Maximum manifest files to scan with --manifests.")
    parser.add_argument("--manifests-max-items", type=positive_int, metavar="N", help="Maximum manifest items to show with --manifests.")
    parser.add_argument("--todos-max-items", type=positive_int, metavar="N", help="Maximum TODO marker count to show with --todos.")
    parser.add_argument("--todos-max-files", type=positive_int, metavar="N", help="Maximum files to scan with --todos.")
    parser.add_argument("--instructions-max-files", type=positive_int, metavar="N", help="Maximum instruction files to scan with --instructions.")
    parser.add_argument("--instructions-max-bytes", type=positive_int, metavar="N", help="Maximum instruction text bytes to include with --instructions.")
    parser.add_argument("--overview-max-files", type=positive_int, metavar="N", help="Maximum files to show with --overview.")
    parser.add_argument("--overview-max-commands", type=positive_int, metavar="N", help="Maximum project commands to show with --overview.")
    parser.add_argument("--overview-max-checks", type=positive_int, metavar="N", help="Maximum suggested checks to show with --overview.")
    parser.add_argument("--repo-map-max-depth", type=nonnegative_int, metavar="N", help="Maximum tree depth to show with --repo-map.")
    parser.add_argument("--repo-map-max-files", type=positive_int, metavar="N", help="Maximum files to show with --repo-map.")
    parser.add_argument("--repo-map-max-symbols", type=positive_int, metavar="N", help="Maximum symbols to show with --repo-map.")
    parser.add_argument("--glob-max-matches", type=positive_int, metavar="N", help="Maximum file matches to show with --glob.")
    parser.add_argument("--tree-max-depth", type=nonnegative_int, metavar="N", help="Maximum directory depth to show with --tree.")
    parser.add_argument("--tree-max-entries", type=positive_int, metavar="N", help="Maximum entries to show with --tree.")
    parser.add_argument("--symbols-max", type=positive_int, metavar="N", help="Maximum symbols to show with --symbols.")
    parser.add_argument(
        "--python-path",
        metavar="PATH",
        help="Project-relative source scope for --python-defs, --python-refs, --python-ref-contexts, --python-calls, --python-rename, or --replace-python-def.",
    )
    parser.add_argument("--python-max-matches", type=positive_int, metavar="N", help="Maximum matches for --python-defs, --python-refs, --python-ref-contexts, or --python-calls.")
    parser.add_argument("--python-def-max-lines", type=positive_int, metavar="N", help="Maximum definition lines to show with --python-defs.")
    parser.add_argument("--python-context-lines", type=nonnegative_int, metavar="N", help="Surrounding source lines for --python-ref-contexts.")
    parser.add_argument("--python-context-max-bytes", type=positive_int, metavar="N", help="Maximum bytes per context with --python-ref-contexts.")
    parser.add_argument("--code-path", metavar="PATH", help="Project-relative source scope for --code-refs, --code-ref-contexts, --code-defs, or --code-rename.")
    parser.add_argument("--code-max-matches", type=positive_int, metavar="N", help="Maximum matches for --code-refs, --code-ref-contexts, or --code-defs.")
    parser.add_argument("--code-def-max-lines", type=positive_int, metavar="N", help="Maximum definition lines to show with --code-defs.")
    parser.add_argument("--code-context-lines", type=nonnegative_int, metavar="N", help="Surrounding source lines for --code-ref-contexts.")
    parser.add_argument("--code-context-max-bytes", type=positive_int, metavar="N", help="Maximum bytes per context with --code-ref-contexts.")
    parser.add_argument("--read-lines", metavar="START[:END]", help="Optional inclusive line range for --read.")
    parser.add_argument("--read-max-bytes", type=positive_int, metavar="N", help="Maximum bytes to read with --read.")
    parser.add_argument("--read-files-max-bytes", type=positive_int, metavar="N", help="Maximum bytes per file with --read-files.")
    parser.add_argument("--read-ranges-max-bytes", type=positive_int, metavar="N", help="Maximum bytes per range with --read-ranges.")
    parser.add_argument("--around-lines", type=nonnegative_int, default=20, metavar="N", help="Surrounding line count for --around.")
    parser.add_argument("--around-max-bytes", type=positive_int, metavar="N", help="Maximum bytes to read with --around.")
    parser.add_argument("--around-many-max-bytes", type=positive_int, metavar="N", help="Maximum bytes per context with --around-many.")
    parser.add_argument("--output-context-lines", type=nonnegative_int, default=5, metavar="N", help="Surrounding line count for --output-contexts.")
    parser.add_argument("--output-context-max", type=positive_int, default=20, metavar="N", help="Maximum contexts to read with --output-contexts.")
    parser.add_argument("--output-context-max-bytes", type=positive_int, default=20_000, metavar="N", help="Maximum bytes per context with --output-contexts.")
    parser.add_argument("--output-diagnostic-lines", type=nonnegative_int, default=2, metavar="N", help="Surrounding source lines for --output-diagnostics.")
    parser.add_argument("--output-diagnostic-max", type=positive_int, default=50, metavar="N", help="Maximum diagnostic lines to show with --output-diagnostics.")
    parser.add_argument("--output-diagnostic-context-max", type=positive_int, default=20, metavar="N", help="Maximum source contexts to read with --output-diagnostics.")
    parser.add_argument("--output-diagnostic-context-max-bytes", type=positive_int, default=20_000, metavar="N", help="Maximum bytes per context with --output-diagnostics or --python-traceback.")
    parser.add_argument("--session-output-command-max", type=positive_int, default=20, metavar="N", help="Maximum session command outputs to scan with --session-output-contexts or --session-output-diagnostics.")
    parser.add_argument("--session-output-max-chars", type=positive_int, default=20_000, metavar="N", help="Maximum characters to read per session command output.")
    parser.add_argument("--session-output-context-lines", type=nonnegative_int, default=5, metavar="N", help="Surrounding line count for --session-output-contexts or --session-output-diagnostics.")
    parser.add_argument("--session-output-context-max", type=positive_int, default=20, metavar="N", help="Maximum contexts to read with --session-output-contexts or --session-output-diagnostics.")
    parser.add_argument("--session-output-context-max-bytes", type=positive_int, default=20_000, metavar="N", help="Maximum bytes per session output source context.")
    parser.add_argument("--session-output-diagnostic-max", type=positive_int, default=50, metavar="N", help="Maximum diagnostic lines to show with --session-output-diagnostics.")
    parser.add_argument("--session-transcript-event-max", type=positive_int, metavar="N", help="Maximum timeline events to show with --transcript.")
    parser.add_argument("--session-search-match-max", type=positive_int, metavar="N", help="Maximum matching timeline events to show with --session-search.")
    parser.add_argument("--session-search-case-sensitive", action="store_true", help="Use case-sensitive matching with --session-search.")
    parser.add_argument("--session-max-checks", type=positive_int, metavar="N", help="Maximum check rows per group to show with --session-verification, --session-audit, or --session-handoff.")
    parser.add_argument("--session-max-commands", type=positive_int, metavar="N", help="Maximum command results to show with --session-commands, --session-audit, or --session-handoff.")
    parser.add_argument("--session-max-output-chars", type=nonnegative_int, metavar="N", help="Maximum stdout/stderr tail characters per command with --session-commands or --session-handoff.")
    parser.add_argument("--session-max-files", type=positive_int, metavar="N", help="Maximum file references to show with --session-files, --session-audit, or --session-handoff.")
    parser.add_argument("--session-max-failures", type=positive_int, metavar="N", help="Maximum failure entries to show with --session-failures, --session-audit, or --session-handoff.")
    parser.add_argument("--session-max-text", type=positive_int, metavar="N", help="Maximum text characters per timeline, search, failure, or readiness entry.")
    parser.add_argument("--tail-lines", type=positive_int, default=80, metavar="N", help="Trailing line count for --tail.")
    parser.add_argument("--tail-max-bytes", type=positive_int, metavar="N", help="Maximum bytes to read with --tail.")
    parser.add_argument("--log-count", type=positive_int, default=5, metavar="N", help="Maximum commits to show with --log.")
    parser.add_argument("--show-path", metavar="PATH", help="Optional project-relative path for --show.")
    parser.add_argument("--show-max-chars", type=positive_int, default=12_000, metavar="N", help="Maximum output characters for --show.")
    parser.add_argument("--blame-lines", metavar="START[:END]", help="Optional inclusive line range for --blame.")
    parser.add_argument("--blame-max-chars", type=positive_int, default=12_000, metavar="N", help="Maximum output characters for --blame.")
    parser.add_argument("--stash-count", type=positive_int, default=20, metavar="N", help="Maximum stash entries to show with --stashes.")
    parser.add_argument("--stash-include-untracked", action="store_true", help="Include untracked files with --check-git-stash or --git-stash.")
    parser.add_argument("--git-switch-create", action="store_true", help="Create the branch when used with --check-git-switch or --git-switch.")
    parser.add_argument("--process-max-chars", type=positive_int, default=4_000, metavar="N", help="Maximum captured output characters for --process-output, --process-output-contexts, or --process-output-diagnostics.")
    parser.add_argument("--process-output-context-lines", type=nonnegative_int, default=5, metavar="N", help="Context lines around each extracted process output reference.")
    parser.add_argument("--process-output-context-max", type=positive_int, default=20, metavar="N", help="Maximum extracted process output contexts.")
    parser.add_argument("--process-output-context-max-bytes", type=positive_int, default=20_000, metavar="N", help="Maximum bytes per extracted process output context.")
    parser.add_argument("--process-output-diagnostic-max", type=positive_int, default=50, metavar="N", help="Maximum diagnostic lines to show with --process-output-diagnostics.")
    parser.add_argument("--wait-timeout-ms", type=timeout_ms, default=5_000, metavar="N", help="Maximum milliseconds to wait with --wait-process.")
    parser.add_argument("--wait-max-chars", type=positive_int, default=4_000, metavar="N", help="Maximum captured output characters for --wait-process.")
    parser.add_argument("--wait-stdout", metavar="TEXT", help="Return early when --wait-process stdout contains TEXT.")
    parser.add_argument("--wait-stderr", metavar="TEXT", help="Return early when --wait-process stderr contains TEXT.")
    parser.add_argument("--wait-regex", action="store_true", help="Treat --wait-stdout or --wait-stderr as a regular expression.")
    parser.add_argument("--write-stdin", metavar="TEXT", help="Stdin text for --check-write-process or --write-process. Use \\n when pressing Enter is required.")
    parser.add_argument("--regex-count", type=nonnegative_int, default=0, metavar="N", help="Maximum replacements for --check-regex-replace or --regex-replace. Use 0 for all.")
    parser.add_argument("--regex-max-replacements", type=positive_int, default=100, metavar="N", help="Safety cap for --check-regex-replace or --regex-replace.")
    parser.add_argument("--regex-ignore-case", action="store_true", help="Use case-insensitive matching with --check-regex-replace or --regex-replace.")
    parser.add_argument("--regex-multiline", action="store_true", help="Let ^ and $ match line boundaries with --check-regex-replace or --regex-replace.")
    parser.add_argument("--run-timeout-ms", type=timeout_ms, default=30_000, metavar="N", help="Maximum milliseconds for --run-command, --run-commands, or --run-suggested-checks.")
    parser.add_argument("--run-max-chars", type=positive_int, default=12_000, metavar="N", help="Maximum stdout/stderr characters for --run-command, --run-commands, or --run-suggested-checks.")
    parser.add_argument("--run-continue-on-failure", action="store_true", help="Continue after a failing command with --run-commands or --run-suggested-checks.")
    parser.add_argument("--run-output-contexts", action="store_true", help="Extract file:line source contexts from --run-command, --run-commands, or --run-suggested-checks output.")
    parser.add_argument("--run-output-diagnostics", action="store_true", help="Summarize errors, warnings, and failures from --run-command, --run-commands, or --run-suggested-checks output.")
    parser.add_argument("--run-output-context-lines", type=nonnegative_int, default=5, metavar="N", help="Context lines around each extracted run output reference.")
    parser.add_argument("--run-output-diagnostic-max", type=positive_int, default=50, metavar="N", help="Maximum diagnostic lines to show with --run-output-diagnostics or failed-command auto-diagnostics.")
    parser.add_argument("--run-output-context-max", type=positive_int, default=20, metavar="N", help="Maximum extracted run output contexts.")
    parser.add_argument("--run-output-context-max-bytes", type=positive_int, default=20_000, metavar="N", help="Maximum bytes per extracted run output context.")
    local.add_argument("--sessions", action="store_true", help="List recent local sessions and exit.")
    local.add_argument("--last", action="store_true", help="Show the newest session summary and exit.")
    local.add_argument("--session", metavar="RUN_ID", help="Show one compact session summary and exit.")
    local.add_argument("--plan", nargs="?", const="", metavar="RUN_ID", help="Show the newest or selected session task plan and exit.")
    local.add_argument("--transcript", nargs="?", const="", metavar="RUN_ID", help="Show a safe timeline of the newest or selected session and exit.")
    local.add_argument("--session-search", metavar="QUERY", help="Search the newest or selected safe session timeline and exit.")
    parser.add_argument("--session-search-run", metavar="RUN_ID", help="Session id for --session-search.")
    local.add_argument("--session-commands", nargs="?", const="", metavar="RUN_ID", help="Show bounded stdout/stderr from the newest or selected session commands and exit.")
    local.add_argument("--session-output-contexts", nargs="?", const="", metavar="RUN_ID", help="Extract file:line contexts from newest or selected session command output and exit.")
    local.add_argument("--session-output-diagnostics", nargs="?", const="", metavar="RUN_ID", help="Summarize diagnostics from newest or selected session command output and exit.")
    local.add_argument("--session-files", nargs="?", const="", metavar="RUN_ID", help="Show project paths referenced by the newest or selected session and exit.")
    local.add_argument("--session-failures", nargs="?", const="", metavar="RUN_ID", help="Show failed tools, commands, final results, malformed events, and denied approvals from the newest or selected session and exit.")
    local.add_argument("--session-verification", nargs="?", const="", metavar="RUN_ID", help="Show verified, pending, and failed suggested checks for the newest or selected session and exit.")
    local.add_argument("--session-audit", nargs="?", const="", metavar="RUN_ID", help="Show finish-time readiness, blockers, active processes, checks, failures, commands, and files for the newest or selected session and exit.")
    local.add_argument("--session-handoff", nargs="?", const="", metavar="RUN_ID", help="Show a compact recovery handoff bundle for the newest or selected session and exit.")
    local.add_argument("--checkpoint", nargs="?", const="", metavar="LABEL", help="Save current git status, diffs, and ordinary untracked files as a local checkpoint and exit.")
    local.add_argument("--checkpoints", action="store_true", help="List saved local checkpoints and exit.")
    local.add_argument("--checkpoint-show", metavar="ID", help="Show one saved local checkpoint and exit.")
    local.add_argument("--checkpoint-diff", metavar="ID", help="Show saved staged and unstaged checkpoint patches and exit.")
    local.add_argument("--checkpoint-status", metavar="ID", help="Compare current git status and diffs with a saved checkpoint and exit.")
    local.add_argument("--check-checkpoint-restore", metavar="ID", help="Preview restoring tracked staged/unstaged changes and saved untracked files from a checkpoint and exit.")
    local.add_argument("--checkpoint-restore", metavar="ID", help="Restore tracked staged/unstaged changes and saved untracked files from a checkpoint and exit.")
    local.add_argument("--check-checkpoint-delete", metavar="ID", help="Preview deleting one saved local checkpoint and exit.")
    local.add_argument("--checkpoint-delete", metavar="ID", help="Delete one saved local checkpoint and exit.")
    local.add_argument("--check-checkpoint-prune", metavar="N", help="Preview deleting older checkpoints while keeping the newest N and exit.")
    local.add_argument("--checkpoint-prune", metavar="N", help="Delete older checkpoints while keeping the newest N and exit.")
    local.add_argument("--usage", action="store_true", help="Show local session usage and exit.")
    local.add_argument("--cost", action="store_true", help="Show configured cost estimate and exit.")
    local.add_argument("--save-config", action="store_true", help="Save non-secret provider defaults to .vibeagent/config.json and exit.")
    parser.add_argument(
        "--approval",
        choices=("ask", "allow", "deny"),
        default="ask",
        help="Approval policy for one-shot coding tasks.",
    )
    parser.add_argument(
        "--resume",
        nargs="?",
        const="",
        metavar="RUN_ID",
        help="Load a previous session summary before a one-shot coding task. Omit RUN_ID to use the newest session.",
    )
    parser.add_argument("--resume-max-failures", type=positive_int, metavar="N", help="Maximum failure entries in --resume context.")
    parser.add_argument("--resume-max-files", type=positive_int, metavar="N", help="Maximum file references in --resume context.")
    parser.add_argument("--resume-max-commands", type=positive_int, metavar="N", help="Maximum command results in --resume context.")
    parser.add_argument("--resume-max-checks", type=positive_int, metavar="N", help="Maximum check rows per group in --resume context.")
    parser.add_argument("--resume-max-output-chars", type=nonnegative_int, metavar="N", help="Maximum stdout/stderr tail characters per command in --resume context.")
    parser.add_argument("--resume-max-text", type=positive_int, metavar="N", help="Maximum text characters per timeline, failure, or readiness entry in --resume context.")
    parser.add_argument(
        "--compact",
        nargs="?",
        const="",
        metavar="RUN_ID",
        help="Load a compact previous session handoff before a one-shot coding task. Omit RUN_ID to use the newest session.",
    )
    parser.add_argument("--compact-max-failures", type=positive_int, metavar="N", help="Maximum failure entries in --compact context.")
    parser.add_argument("--compact-max-files", type=positive_int, metavar="N", help="Maximum file references in --compact context.")
    parser.add_argument("--compact-max-commands", type=positive_int, metavar="N", help="Maximum command results in --compact context.")
    parser.add_argument("--compact-max-checks", type=positive_int, metavar="N", help="Maximum check rows per group in --compact context.")
    parser.add_argument("--compact-max-output-chars", type=nonnegative_int, metavar="N", help="Maximum stdout/stderr tail characters per command in --compact context.")
    parser.add_argument("--compact-max-text", type=positive_int, metavar="N", help="Maximum text characters per timeline, failure, or readiness entry in --compact context.")
    parser.add_argument("--cwd", help="Project directory for one-shot coding tasks.")
    parser.add_argument("--json", action="store_true", help="Print a single JSON result for one-shot or local command output.")
    parser.add_argument(
        "--provider",
        choices=("minimax", "deepseek", "openai-compatible"),
        help="Temporarily override the model provider for this command.",
    )
    parser.add_argument("--model-name", help="Temporarily override the model name for this command.")
    parser.add_argument("--base-url", help="Temporarily override the provider base URL for this command.")
    parser.add_argument("--api-key", help="Temporarily override the provider API key for this command.")
    parser.add_argument(
        "--max-iterations",
        type=positive_int,
        help="Maximum model/tool iterations for one-shot coding tasks. Defaults to project config or 20.",
    )
    parser.add_argument(
        "--command-timeout-ms",
        type=timeout_ms,
        help="Default command timeout in milliseconds for one-shot coding tasks. Defaults to project config or 30000.",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=positive_int,
        help="Maximum model output tokens per response. Defaults to project config or 4096.",
    )
    parser.add_argument(
        "--model-retries",
        type=nonnegative_int,
        help="Retry attempts after a provider request failure. Defaults to project config or 1.",
    )
    parser.add_argument(
        "--model-retry-delay-ms",
        type=nonnegative_int,
        help="Milliseconds to wait between provider retry attempts. Defaults to project config or 250.",
    )
    parser.add_argument(
        "--model-timeout-ms",
        type=timeout_ms,
        help="Provider request timeout in milliseconds. Defaults to project config or 120000.",
    )
    parser.add_argument("task", nargs="*", help="One-shot task text. Omit it to start the interactive prompt.")
    return parser.parse_args(list(argv))


def has_local_flag(args: argparse.Namespace) -> bool:
    return any(
        (
            args.model,
            args.config,
            args.tools,
            args.tool is not None,
            args.permissions,
            args.checks,
            args.check_suggested_checks is not None,
            args.run_suggested_checks is not None,
            args.commands,
            args.related_tests is not None,
            args.focused_tests is not None,
            args.check_focused_tests is not None,
            args.run_focused_tests is not None,
            args.manifests,
            args.instructions,
            args.todos is not None,
            args.command_check is not None,
            args.run_command is not None,
            args.check_run_commands is not None,
            args.run_commands is not None,
            args.check_start_command is not None,
            args.start_command is not None,
            args.port_check is not None,
            args.http_check is not None,
            args.http_fetch is not None,
            args.overview,
            args.repo_map is not None,
            args.search is not None,
            args.search_contexts is not None,
            args.glob is not None,
            args.tree is not None,
            args.symbols is not None,
            args.file_info is not None,
            args.image_info is not None,
            args.read is not None,
            args.around is not None,
            args.around_many is not None,
            args.output_contexts is not None,
            args.output_diagnostics is not None,
            args.python_traceback is not None,
            args.tail is not None,
            args.read_files is not None,
            args.read_ranges is not None,
            args.python_check is not None,
            args.python_deps is not None,
            args.python_defs is not None,
            args.python_refs is not None,
            args.python_ref_contexts is not None,
            args.python_calls is not None,
            args.python_call_graph is not None,
            args.python_rename_preview is not None,
            args.python_rename is not None,
            args.check_replace_python_def is not None,
            args.replace_python_def is not None,
            args.config_check is not None,
            args.check_json_set is not None,
            args.json_set is not None,
            args.check_json_remove is not None,
            args.json_remove is not None,
            args.check_json_patch is not None,
            args.json_patch is not None,
            args.check_replace_lines is not None,
            args.replace_lines is not None,
            args.check_insert_lines is not None,
            args.insert_lines is not None,
            args.check_append is not None,
            args.append is not None,
            args.check_write is not None,
            args.write is not None,
            args.check_write_files is not None,
            args.write_files is not None,
            args.check_edit is not None,
            args.edit is not None,
            args.check_multi_edit is not None,
            args.multi_edit is not None,
            args.check_delete is not None,
            args.delete is not None,
            args.check_delete_files is not None,
            args.delete_files is not None,
            args.check_move is not None,
            args.move is not None,
            args.check_move_files is not None,
            args.move_files is not None,
            args.check_copy is not None,
            args.copy is not None,
            args.check_copy_files is not None,
            args.copy_files is not None,
            args.check_move_dir is not None,
            args.move_dir is not None,
            args.check_move_dirs is not None,
            args.move_dirs is not None,
            args.check_copy_dir is not None,
            args.copy_dir is not None,
            args.check_copy_dirs is not None,
            args.copy_dirs is not None,
            args.check_mkdir is not None,
            args.mkdir is not None,
            args.check_mkdirs is not None,
            args.mkdirs is not None,
            args.check_rmdir is not None,
            args.rmdir is not None,
            args.check_rmdirs is not None,
            args.rmdirs is not None,
            args.check_executable is not None,
            args.set_executable is not None,
            args.check_patch is not None,
            args.patch is not None,
            args.check_patches is not None,
            args.patches is not None,
            args.check_regex_replace is not None,
            args.regex_replace is not None,
            args.code_deps is not None,
            args.code_refs is not None,
            args.code_ref_contexts is not None,
            args.code_defs is not None,
            args.code_rename_preview is not None,
            args.code_rename is not None,
            args.git_status,
            args.conflicts is not None,
            args.git_info,
            args.branches,
            args.log is not None,
            args.show is not None,
            args.blame is not None,
            args.stashes,
            args.check_git_fetch is not None,
            args.git_fetch is not None,
            args.check_git_pull,
            args.git_pull,
            args.check_git_push,
            args.git_push,
            args.check_git_stash is not None,
            args.git_stash is not None,
            args.check_git_stash_apply is not None,
            args.git_stash_apply is not None,
            args.check_git_stash_drop is not None,
            args.git_stash_drop is not None,
            args.check_git_stage is not None,
            args.git_stage is not None,
            args.check_git_unstage is not None,
            args.git_unstage is not None,
            args.check_git_commit is not None,
            args.git_commit is not None,
            args.check_git_restore is not None,
            args.git_restore is not None,
            args.check_git_switch is not None,
            args.git_switch is not None,
            args.env,
            args.processes,
            args.process_output is not None,
            args.process_output_contexts is not None,
            args.process_output_diagnostics is not None,
            args.wait_process is not None,
            args.check_write_process is not None,
            args.write_process is not None,
            args.check_stop_process is not None,
            args.stop_process is not None,
            args.check_stop_all_processes,
            args.stop_all_processes,
            args.status,
            args.context,
            args.init is not None,
            args.doctor,
            args.review,
            args.handoff,
            args.changes,
            args.diff is not None,
            args.diff_hunks is not None,
            args.diff_contexts is not None,
            args.sessions,
            args.last,
            args.session is not None,
            args.plan is not None,
            args.transcript is not None,
            args.session_search is not None,
            args.session_commands is not None,
            args.session_output_contexts is not None,
            args.session_output_diagnostics is not None,
            args.session_files is not None,
            args.session_failures is not None,
            args.session_verification is not None,
            args.session_audit is not None,
            args.session_handoff is not None,
            args.checkpoint is not None,
            args.checkpoints,
            args.checkpoint_show is not None,
            args.checkpoint_diff is not None,
            args.checkpoint_status is not None,
            args.check_checkpoint_restore is not None,
            args.checkpoint_restore is not None,
            args.check_checkpoint_delete is not None,
            args.checkpoint_delete is not None,
            args.check_checkpoint_prune is not None,
            args.checkpoint_prune is not None,
            args.usage,
            args.cost,
            args.save_config,
        )
    )


def run_local_flag(args: argparse.Namespace) -> int:
    try:
        project_root = resolve_project_root(args.cwd)
        config_root = project_root or Path.cwd()
        payload_extra: dict[str, object] = {}
        if args.save_config:
            text = save_project_config_from_args(args, config_root)
        else:
            provider_env = build_provider_env(args, config_root)
            if args.model:
                text = get_model_text(provider_env)
            elif args.config:
                text = get_config_text(
                    config_root,
                    provider_env,
                    max_iterations=args.max_iterations,
                    command_timeout_ms=args.command_timeout_ms,
                    max_output_tokens=args.max_output_tokens,
                    model_retries=args.model_retries,
                    model_retry_delay_ms=args.model_retry_delay_ms,
                    model_timeout_ms=args.model_timeout_ms,
                )
            elif args.tools:
                text = get_tools_text()
            elif args.tool is not None:
                text = get_tool_text(args.tool)
            elif args.permissions:
                payload_extra["permissions"] = get_permissions_report(args.approval)
                text = get_permissions_text(args.approval)
            elif args.checks:
                payload_extra["checks"] = get_checks_report(project_root or ".", max_checks=args.checks_max)
                text = get_checks_text(project_root or ".", max_checks=args.checks_max)
            elif args.check_suggested_checks is not None:
                text = get_check_suggested_checks_text(
                    project_root or ".",
                    args.check_suggested_checks or None,
                    max_checks=args.check_suggested_checks_max,
                )
            elif args.run_suggested_checks is not None:
                text = get_run_suggested_checks_text(
                    project_root or ".",
                    args.run_suggested_checks or None,
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
                text = get_commands_text(project_root or ".", **commands_kwargs)
            elif args.related_tests is not None:
                related_kwargs = {}
                if args.related_tests_max_paths is not None:
                    related_kwargs["max_paths"] = args.related_tests_max_paths
                if args.related_tests_max_candidates is not None:
                    related_kwargs["max_candidates"] = args.related_tests_max_candidates
                text = get_related_tests_text(project_root or ".", shlex.join(args.related_tests) if args.related_tests else None, **related_kwargs)
            elif args.focused_tests is not None:
                focused_kwargs = build_focused_tests_kwargs(args)
                text = get_focused_test_commands_text(project_root or ".", shlex.join(args.focused_tests) if args.focused_tests else None, **focused_kwargs)
            elif args.check_focused_tests is not None:
                focused_kwargs = build_focused_tests_kwargs(args)
                text = get_check_focused_test_commands_text(project_root or ".", shlex.join(args.check_focused_tests) if args.check_focused_tests else None, **focused_kwargs)
            elif args.run_focused_tests is not None:
                focused_kwargs = build_focused_tests_kwargs(args)
                text = get_run_focused_test_commands_text(
                    project_root or ".",
                    shlex.join(args.run_focused_tests) if args.run_focused_tests else None,
                    **focused_kwargs,
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
            elif args.manifests:
                manifests_kwargs = {}
                if args.manifests_max_files is not None:
                    manifests_kwargs["max_files"] = args.manifests_max_files
                if args.manifests_max_items is not None:
                    manifests_kwargs["max_items"] = args.manifests_max_items
                text = get_manifests_text(project_root or ".", **manifests_kwargs)
            elif args.instructions:
                instructions_kwargs = {}
                if args.instructions_max_files is not None:
                    instructions_kwargs["max_files"] = args.instructions_max_files
                if args.instructions_max_bytes is not None:
                    instructions_kwargs["max_bytes"] = args.instructions_max_bytes
                text = get_instructions_text(project_root or ".", **instructions_kwargs)
            elif args.todos is not None:
                todos_kwargs = {}
                if args.todos_max_items is not None:
                    todos_kwargs["max_items"] = args.todos_max_items
                if args.todos_max_files is not None:
                    todos_kwargs["max_files"] = args.todos_max_files
                text = get_todos_text(project_root or ".", args.todos or None, **todos_kwargs)
            elif args.command_check is not None:
                text = get_command_check_text(project_root or ".", args.command_check, args.command_cwd)
            elif args.run_command is not None:
                text = get_run_text(
                    project_root or ".",
                    args.run_command,
                    cwd=args.run_cwd,
                    timeout_ms=args.run_timeout_ms,
                    max_output_chars=args.run_max_chars,
                    extract_output_contexts=args.run_output_contexts,
                    extract_output_diagnostics=args.run_output_diagnostics,
                    context_lines=args.run_output_context_lines,
                    max_diagnostics=args.run_output_diagnostic_max,
                    max_contexts=args.run_output_context_max,
                    max_bytes_per_context=args.run_output_context_max_bytes,
                )
            elif args.check_run_commands is not None:
                text = get_check_run_sequence_text(project_root or ".", commands=args.check_run_commands, cwd=args.run_cwd)
            elif args.run_commands is not None:
                text = get_run_sequence_text(
                    project_root or ".",
                    commands=args.run_commands,
                    cwd=args.run_cwd,
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
            elif args.check_start_command is not None:
                text = get_check_start_text(project_root or ".", args.check_start_command, cwd=args.start_cwd)
            elif args.start_command is not None:
                text = get_start_text(project_root or ".", args.start_command, cwd=args.start_cwd)
            elif args.port_check is not None:
                text = get_port_text(
                    project_root or ".",
                    port=args.port_check,
                    host=args.port_host,
                    timeout_ms=args.port_timeout_ms,
                )
            elif args.http_check is not None:
                text = get_http_text(
                    project_root or ".",
                    url=args.http_check,
                    contains=args.http_contains,
                    timeout_ms=args.http_timeout_ms or 2_000,
                    max_body_chars=args.http_max_body_chars or 2_000,
                    regex=args.http_regex,
                )
            elif args.http_fetch is not None:
                text = get_http_fetch_text(
                    project_root or ".",
                    url=args.http_fetch,
                    timeout_ms=args.http_timeout_ms or 5_000,
                    max_body_chars=args.http_max_body_chars or 12_000,
                )
            elif args.overview:
                overview_kwargs = {}
                if args.overview_max_files is not None:
                    overview_kwargs["max_files"] = args.overview_max_files
                if args.overview_max_commands is not None:
                    overview_kwargs["max_commands"] = args.overview_max_commands
                if args.overview_max_checks is not None:
                    overview_kwargs["max_checks"] = args.overview_max_checks
                text = get_overview_text(project_root or ".", **overview_kwargs)
            elif args.repo_map is not None:
                repo_map_kwargs = {}
                if args.repo_map_max_depth is not None:
                    repo_map_kwargs["max_depth"] = args.repo_map_max_depth
                if args.repo_map_max_files is not None:
                    repo_map_kwargs["max_files"] = args.repo_map_max_files
                if args.repo_map_max_symbols is not None:
                    repo_map_kwargs["max_symbols"] = args.repo_map_max_symbols
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
                text = get_search_contexts_text(project_root or ".", args.search_contexts, args.search_path, **search_contexts_kwargs)
            elif args.glob is not None:
                glob_kwargs = {}
                if args.glob_max_matches is not None:
                    glob_kwargs["max_matches"] = args.glob_max_matches
                text = get_glob_text(project_root or ".", args.glob, **glob_kwargs)
            elif args.tree is not None:
                tree_kwargs = {}
                if args.tree_max_depth is not None:
                    tree_kwargs["max_depth"] = args.tree_max_depth
                if args.tree_max_entries is not None:
                    tree_kwargs["max_entries"] = args.tree_max_entries
                text = get_tree_text(project_root or ".", args.tree or None, **tree_kwargs)
            elif args.symbols is not None:
                symbols_kwargs = {}
                if args.symbols_max is not None:
                    symbols_kwargs["max_symbols"] = args.symbols_max
                text = get_symbols_text(project_root or ".", args.symbols, **symbols_kwargs)
            elif args.file_info is not None:
                text = get_file_info_text(project_root or ".", args.file_info)
            elif args.image_info is not None:
                text = get_image_info_text(project_root or ".", args.image_info)
            elif args.read is not None:
                read_kwargs = {}
                if args.read_max_bytes is not None:
                    read_kwargs["max_bytes"] = args.read_max_bytes
                text = get_read_text(project_root or ".", args.read, args.read_lines, **read_kwargs)
            elif args.around is not None:
                around_kwargs = {}
                if args.around_max_bytes is not None:
                    around_kwargs["max_bytes"] = args.around_max_bytes
                text = get_around_text(project_root or ".", f"{args.around[0]} {args.around[1]}", args.around_lines, **around_kwargs)
            elif args.around_many is not None:
                around_many_kwargs = {}
                if args.around_many_max_bytes is not None:
                    around_many_kwargs["max_bytes_per_context"] = args.around_many_max_bytes
                text = get_around_many_text(project_root or ".", args.around_many, **around_many_kwargs)
            elif args.output_contexts is not None:
                text = get_output_contexts_text(
                    project_root or ".",
                    args.output_contexts,
                    context_lines=args.output_context_lines,
                    max_contexts=args.output_context_max,
                    max_bytes_per_context=args.output_context_max_bytes,
                )
            elif args.output_diagnostics is not None:
                text = get_output_diagnostics_text(
                    project_root or ".",
                    args.output_diagnostics,
                    context_lines=args.output_diagnostic_lines,
                    max_diagnostics=args.output_diagnostic_max,
                    max_contexts=args.output_diagnostic_context_max,
                    max_bytes_per_context=args.output_diagnostic_context_max_bytes,
                )
            elif args.python_traceback is not None:
                text = get_python_traceback_text(
                    project_root or ".",
                    args.python_traceback,
                    context_lines=args.output_diagnostic_lines,
                    max_diagnostics=args.output_diagnostic_max,
                    max_contexts=args.output_diagnostic_context_max,
                    max_bytes_per_context=args.output_diagnostic_context_max_bytes,
                )
            elif args.tail is not None:
                tail_kwargs = {}
                if args.tail_max_bytes is not None:
                    tail_kwargs["max_bytes"] = args.tail_max_bytes
                text = get_tail_text(project_root or ".", args.tail, args.tail_lines, **tail_kwargs)
            elif args.read_files is not None:
                read_files_kwargs = {}
                if args.read_files_max_bytes is not None:
                    read_files_kwargs["max_bytes_per_file"] = args.read_files_max_bytes
                text = get_read_files_text(project_root or ".", args.read_files, **read_files_kwargs)
            elif args.read_ranges is not None:
                read_ranges_kwargs = {}
                if args.read_ranges_max_bytes is not None:
                    read_ranges_kwargs["max_bytes_per_range"] = args.read_ranges_max_bytes
                text = get_read_ranges_text(project_root or ".", args.read_ranges, **read_ranges_kwargs)
            elif args.python_check is not None:
                text = get_python_check_text(project_root or ".", args.python_check or None)
            elif args.python_deps is not None:
                text = get_python_deps_text(project_root or ".", args.python_deps or None)
            elif args.python_defs is not None:
                python_kwargs = {}
                if args.python_max_matches is not None:
                    python_kwargs["max_matches"] = args.python_max_matches
                if args.python_def_max_lines is not None:
                    python_kwargs["max_lines"] = args.python_def_max_lines
                text = get_python_defs_text(project_root or ".", symbol=args.python_defs, path=args.python_path, **python_kwargs)
            elif args.python_refs is not None:
                python_kwargs = {}
                if args.python_max_matches is not None:
                    python_kwargs["max_matches"] = args.python_max_matches
                text = get_python_refs_text(project_root or ".", symbol=args.python_refs, path=args.python_path, **python_kwargs)
            elif args.python_ref_contexts is not None:
                python_kwargs = {}
                if args.python_max_matches is not None:
                    python_kwargs["max_matches"] = args.python_max_matches
                if args.python_context_lines is not None:
                    python_kwargs["context_lines"] = args.python_context_lines
                if args.python_context_max_bytes is not None:
                    python_kwargs["max_bytes_per_context"] = args.python_context_max_bytes
                text = get_python_ref_contexts_text(project_root or ".", symbol=args.python_ref_contexts, path=args.python_path, **python_kwargs)
            elif args.python_calls is not None:
                python_kwargs = {}
                if args.python_max_matches is not None:
                    python_kwargs["max_matches"] = args.python_max_matches
                text = get_python_calls_text(project_root or ".", symbol=args.python_calls, path=args.python_path, **python_kwargs)
            elif args.python_call_graph is not None:
                text = get_python_call_graph_text(project_root or ".", args.python_call_graph or None)
            elif args.python_rename_preview is not None:
                text = get_python_rename_preview_text(
                    project_root or ".",
                    symbol=args.python_rename_preview[0],
                    new_name=args.python_rename_preview[1],
                    path=args.python_path,
                )
            elif args.python_rename is not None:
                text = get_python_rename_text(
                    project_root or ".",
                    symbol=args.python_rename[0],
                    new_name=args.python_rename[1],
                    path=args.python_path,
                )
            elif args.check_replace_python_def is not None:
                text = get_check_replace_python_definition_text(
                    project_root or ".",
                    symbol=args.check_replace_python_def[0],
                    content=args.check_replace_python_def[1],
                    path=args.python_path,
                )
            elif args.replace_python_def is not None:
                text = get_replace_python_definition_text(
                    project_root or ".",
                    symbol=args.replace_python_def[0],
                    content=args.replace_python_def[1],
                    path=args.python_path,
                )
            elif args.config_check is not None:
                text = get_config_check_text(project_root or ".", args.config_check or None)
            elif args.check_json_set is not None:
                text = get_check_json_set_text(
                    project_root or ".",
                    path=args.check_json_set[0],
                    pointer=args.check_json_set[1],
                    value=parse_cli_json_value(args.check_json_set[2]),
                    create_missing=args.json_create_missing,
                )
            elif args.json_set is not None:
                text = get_json_set_text(
                    project_root or ".",
                    path=args.json_set[0],
                    pointer=args.json_set[1],
                    value=parse_cli_json_value(args.json_set[2]),
                    create_missing=args.json_create_missing,
                )
            elif args.check_json_remove is not None:
                text = get_check_json_remove_text(project_root or ".", path=args.check_json_remove[0], pointer=args.check_json_remove[1])
            elif args.json_remove is not None:
                text = get_json_remove_text(project_root or ".", path=args.json_remove[0], pointer=args.json_remove[1])
            elif args.check_json_patch is not None:
                text = get_check_json_patch_text(
                    project_root or ".",
                    path=args.check_json_patch[0],
                    operations=parse_cli_json_value(args.check_json_patch[1]),
                )
            elif args.json_patch is not None:
                text = get_json_patch_text(
                    project_root or ".",
                    path=args.json_patch[0],
                    operations=parse_cli_json_value(args.json_patch[1]),
                )
            elif args.check_replace_lines is not None:
                text = get_check_replace_lines_text(
                    project_root or ".",
                    path=args.check_replace_lines[0],
                    start_line=args.check_replace_lines[1],
                    end_line=args.check_replace_lines[2],
                    content=args.check_replace_lines[3],
                )
            elif args.replace_lines is not None:
                text = get_replace_lines_text(
                    project_root or ".",
                    path=args.replace_lines[0],
                    start_line=args.replace_lines[1],
                    end_line=args.replace_lines[2],
                    content=args.replace_lines[3],
                )
            elif args.check_insert_lines is not None:
                text = get_check_insert_lines_text(
                    project_root or ".",
                    path=args.check_insert_lines[0],
                    line=args.check_insert_lines[1],
                    content=args.check_insert_lines[2],
                )
            elif args.insert_lines is not None:
                text = get_insert_lines_text(
                    project_root or ".",
                    path=args.insert_lines[0],
                    line=args.insert_lines[1],
                    content=args.insert_lines[2],
                )
            elif args.check_append is not None:
                text = get_check_append_file_text(project_root or ".", path=args.check_append[0], content=args.check_append[1])
            elif args.append is not None:
                text = get_append_file_text(project_root or ".", path=args.append[0], content=args.append[1])
            elif args.check_write is not None:
                text = get_check_write_file_text(project_root or ".", path=args.check_write[0], content=args.check_write[1])
            elif args.write is not None:
                text = get_write_file_text(project_root or ".", path=args.write[0], content=args.write[1])
            elif args.check_write_files is not None:
                text = get_check_write_files_text(project_root or ".", files=args.check_write_files)
            elif args.write_files is not None:
                text = get_write_files_text(project_root or ".", files=args.write_files)
            elif args.check_edit is not None:
                text = get_check_edit_file_text(project_root or ".", path=args.check_edit[0], old=args.check_edit[1], new=args.check_edit[2])
            elif args.edit is not None:
                text = get_edit_file_text(project_root or ".", path=args.edit[0], old=args.edit[1], new=args.edit[2])
            elif args.check_multi_edit is not None:
                path, edits = parse_multi_edit_flag_values(args.check_multi_edit, "--check-multi-edit")
                text = get_check_multi_edit_file_text(project_root or ".", path=path, edits=edits)
            elif args.multi_edit is not None:
                path, edits = parse_multi_edit_flag_values(args.multi_edit, "--multi-edit")
                text = get_multi_edit_file_text(project_root or ".", path=path, edits=edits)
            elif args.check_delete is not None:
                text = get_check_delete_file_text(project_root or ".", path=args.check_delete)
            elif args.delete is not None:
                text = get_delete_file_text(project_root or ".", path=args.delete)
            elif args.check_delete_files is not None:
                text = get_check_delete_files_text(project_root or ".", paths=args.check_delete_files)
            elif args.delete_files is not None:
                text = get_delete_files_text(project_root or ".", paths=args.delete_files)
            elif args.check_move is not None:
                text = get_check_move_file_text(project_root or ".", source=args.check_move[0], destination=args.check_move[1])
            elif args.move is not None:
                text = get_move_file_text(project_root or ".", source=args.move[0], destination=args.move[1])
            elif args.check_move_files is not None:
                text = get_check_move_files_text(project_root or ".", transfers=args.check_move_files)
            elif args.move_files is not None:
                text = get_move_files_text(project_root or ".", transfers=args.move_files)
            elif args.check_copy is not None:
                text = get_check_copy_file_text(project_root or ".", source=args.check_copy[0], destination=args.check_copy[1])
            elif args.copy is not None:
                text = get_copy_file_text(project_root or ".", source=args.copy[0], destination=args.copy[1])
            elif args.check_copy_files is not None:
                text = get_check_copy_files_text(project_root or ".", transfers=args.check_copy_files)
            elif args.copy_files is not None:
                text = get_copy_files_text(project_root or ".", transfers=args.copy_files)
            elif args.check_move_dir is not None:
                text = get_check_move_dir_text(project_root or ".", source=args.check_move_dir[0], destination=args.check_move_dir[1])
            elif args.move_dir is not None:
                text = get_move_dir_text(project_root or ".", source=args.move_dir[0], destination=args.move_dir[1])
            elif args.check_move_dirs is not None:
                text = get_check_move_dirs_text(project_root or ".", transfers=args.check_move_dirs)
            elif args.move_dirs is not None:
                text = get_move_dirs_text(project_root or ".", transfers=args.move_dirs)
            elif args.check_copy_dir is not None:
                text = get_check_copy_dir_text(project_root or ".", source=args.check_copy_dir[0], destination=args.check_copy_dir[1])
            elif args.copy_dir is not None:
                text = get_copy_dir_text(project_root or ".", source=args.copy_dir[0], destination=args.copy_dir[1])
            elif args.check_copy_dirs is not None:
                text = get_check_copy_dirs_text(project_root or ".", transfers=args.check_copy_dirs)
            elif args.copy_dirs is not None:
                text = get_copy_dirs_text(project_root or ".", transfers=args.copy_dirs)
            elif args.check_mkdir is not None:
                text = get_check_create_dir_text(project_root or ".", path=args.check_mkdir)
            elif args.mkdir is not None:
                text = get_create_dir_text(project_root or ".", path=args.mkdir)
            elif args.check_mkdirs is not None:
                text = get_check_create_dirs_text(project_root or ".", paths=args.check_mkdirs)
            elif args.mkdirs is not None:
                text = get_create_dirs_text(project_root or ".", paths=args.mkdirs)
            elif args.check_rmdir is not None:
                text = get_check_delete_empty_dir_text(project_root or ".", path=args.check_rmdir)
            elif args.rmdir is not None:
                text = get_delete_empty_dir_text(project_root or ".", path=args.rmdir)
            elif args.check_rmdirs is not None:
                text = get_check_delete_empty_dirs_text(project_root or ".", paths=args.check_rmdirs)
            elif args.rmdirs is not None:
                text = get_delete_empty_dirs_text(project_root or ".", paths=args.rmdirs)
            elif args.check_executable is not None:
                path, executable = parse_executable_flag_values(args.check_executable, "--check-executable")
                text = get_check_set_executable_text(project_root or ".", path=path, executable=executable)
            elif args.set_executable is not None:
                path, executable = parse_executable_flag_values(args.set_executable, "--set-executable")
                text = get_set_executable_text(project_root or ".", path=path, executable=executable)
            elif args.check_patch is not None:
                text = get_check_patch_text(project_root or ".", path=args.check_patch[0], patch=args.check_patch[1])
            elif args.patch is not None:
                text = get_patch_text(project_root or ".", path=args.patch[0], patch=args.patch[1])
            elif args.check_patches is not None:
                text = get_check_patches_text(project_root or ".", patch=args.check_patches)
            elif args.patches is not None:
                text = get_patches_text(project_root or ".", patch=args.patches)
            elif args.check_regex_replace is not None:
                text = get_check_regex_replace_text(
                    project_root or ".",
                    path=args.check_regex_replace[0],
                    pattern=args.check_regex_replace[1],
                    replacement=args.check_regex_replace[2],
                    count=args.regex_count,
                    case_sensitive=not args.regex_ignore_case,
                    multiline=args.regex_multiline,
                    max_replacements=args.regex_max_replacements,
                )
            elif args.regex_replace is not None:
                text = get_regex_replace_text(
                    project_root or ".",
                    path=args.regex_replace[0],
                    pattern=args.regex_replace[1],
                    replacement=args.regex_replace[2],
                    count=args.regex_count,
                    case_sensitive=not args.regex_ignore_case,
                    multiline=args.regex_multiline,
                    max_replacements=args.regex_max_replacements,
                )
            elif args.code_deps is not None:
                text = get_code_deps_text(project_root or ".", args.code_deps or None)
            elif args.code_refs is not None:
                code_kwargs = {}
                if args.code_max_matches is not None:
                    code_kwargs["max_matches"] = args.code_max_matches
                text = get_code_refs_text(project_root or ".", symbol=args.code_refs, path=args.code_path, **code_kwargs)
            elif args.code_ref_contexts is not None:
                code_kwargs = {}
                if args.code_max_matches is not None:
                    code_kwargs["max_matches"] = args.code_max_matches
                if args.code_context_lines is not None:
                    code_kwargs["context_lines"] = args.code_context_lines
                if args.code_context_max_bytes is not None:
                    code_kwargs["max_bytes_per_context"] = args.code_context_max_bytes
                text = get_code_ref_contexts_text(project_root or ".", symbol=args.code_ref_contexts, path=args.code_path, **code_kwargs)
            elif args.code_defs is not None:
                code_kwargs = {}
                if args.code_max_matches is not None:
                    code_kwargs["max_matches"] = args.code_max_matches
                if args.code_def_max_lines is not None:
                    code_kwargs["max_lines"] = args.code_def_max_lines
                text = get_code_defs_text(project_root or ".", symbol=args.code_defs, path=args.code_path, **code_kwargs)
            elif args.code_rename_preview is not None:
                text = get_code_rename_preview_text(
                    project_root or ".",
                    symbol=args.code_rename_preview[0],
                    new_name=args.code_rename_preview[1],
                    path=args.code_path,
                )
            elif args.code_rename is not None:
                text = get_code_rename_text(
                    project_root or ".",
                    symbol=args.code_rename[0],
                    new_name=args.code_rename[1],
                    path=args.code_path,
                )
            elif args.git_status:
                text = get_git_status_text(project_root or ".")
            elif args.conflicts is not None:
                text = get_git_conflicts_text(project_root or ".", args.conflicts or None)
            elif args.git_info:
                text = get_git_info_text(project_root or ".")
            elif args.branches:
                text = get_branches_text(project_root or ".")
            elif args.log is not None:
                text = get_log_text(project_root or ".", args.log or None, args.log_count)
            elif args.show is not None:
                text = get_show_text(project_root or ".", rev=args.show or "HEAD", path=args.show_path, max_output_chars=args.show_max_chars)
            elif args.blame is not None:
                text = get_blame_text(project_root or ".", args.blame, args.blame_lines, args.blame_max_chars)
            elif args.stashes:
                text = get_stashes_text(project_root or ".", max_entries=args.stash_count)
            elif args.check_git_fetch is not None:
                text = get_check_fetch_text(project_root or ".", args.check_git_fetch)
            elif args.git_fetch is not None:
                text = get_fetch_text(project_root or ".", args.git_fetch)
            elif args.check_git_pull:
                text = get_check_pull_text(project_root or ".")
            elif args.git_pull:
                text = get_pull_text(project_root or ".")
            elif args.check_git_push:
                text = get_check_push_text(project_root or ".")
            elif args.git_push:
                text = get_push_text(project_root or ".")
            elif args.check_git_stash is not None:
                stash_arg = build_stash_argument(args.check_git_stash, args.stash_include_untracked)
                text = get_check_stash_text(project_root or ".", stash_arg)
            elif args.git_stash is not None:
                stash_arg = build_stash_argument(args.git_stash, args.stash_include_untracked)
                text = get_stash_text(project_root or ".", stash_arg)
            elif args.check_git_stash_apply is not None:
                text = get_check_stash_apply_text(project_root or ".", args.check_git_stash_apply)
            elif args.git_stash_apply is not None:
                text = get_stash_apply_text(project_root or ".", args.git_stash_apply)
            elif args.check_git_stash_drop is not None:
                text = get_check_stash_drop_text(project_root or ".", args.check_git_stash_drop)
            elif args.git_stash_drop is not None:
                text = get_stash_drop_text(project_root or ".", args.git_stash_drop)
            elif args.check_git_stage is not None:
                text = get_check_stage_text(project_root or ".", args.check_git_stage)
            elif args.git_stage is not None:
                text = get_stage_text(project_root or ".", args.git_stage)
            elif args.check_git_unstage is not None:
                text = get_check_unstage_text(project_root or ".", args.check_git_unstage)
            elif args.git_unstage is not None:
                text = get_unstage_text(project_root or ".", args.git_unstage)
            elif args.check_git_commit is not None:
                text = get_check_commit_text(project_root or ".", args.check_git_commit)
            elif args.git_commit is not None:
                text = get_commit_text(project_root or ".", args.git_commit)
            elif args.check_git_restore is not None:
                text = get_check_restore_text(project_root or ".", args.check_git_restore)
            elif args.git_restore is not None:
                text = get_restore_text(project_root or ".", args.git_restore)
            elif args.check_git_switch is not None:
                switch_arg = build_switch_argument(args.check_git_switch, args.git_switch_create)
                text = get_check_switch_text(project_root or ".", switch_arg)
            elif args.git_switch is not None:
                switch_arg = build_switch_argument(args.git_switch, args.git_switch_create)
                text = get_switch_text(project_root or ".", switch_arg)
            elif args.env:
                text = get_env_text(project_root or ".")
            elif args.processes:
                text = get_processes_text(project_root or ".")
            elif args.process_output is not None:
                text = get_process_text(project_root or ".", process_id=args.process_output, max_output_chars=args.process_max_chars)
            elif args.process_output_contexts is not None:
                text = get_process_output_contexts_text(
                    project_root or ".",
                    process_id=args.process_output_contexts,
                    max_output_chars=args.process_max_chars,
                    context_lines=args.process_output_context_lines,
                    max_contexts=args.process_output_context_max,
                    max_bytes_per_context=args.process_output_context_max_bytes,
                )
            elif args.process_output_diagnostics is not None:
                text = get_process_output_diagnostics_text(
                    project_root or ".",
                    process_id=args.process_output_diagnostics,
                    max_output_chars=args.process_max_chars,
                    context_lines=args.process_output_context_lines,
                    max_diagnostics=args.process_output_diagnostic_max,
                    max_contexts=args.process_output_context_max,
                    max_bytes_per_context=args.process_output_context_max_bytes,
                )
            elif args.wait_process is not None:
                text = get_wait_process_text(
                    project_root or ".",
                    process_id=args.wait_process,
                    timeout_ms=args.wait_timeout_ms,
                    max_output_chars=args.wait_max_chars,
                    stdout_contains=args.wait_stdout,
                    stderr_contains=args.wait_stderr,
                    regex=args.wait_regex,
                )
            elif args.check_write_process is not None:
                text = get_check_write_process_text(project_root or ".", process_id=args.check_write_process, content=args.write_stdin)
            elif args.write_process is not None:
                text = get_write_process_text(project_root or ".", process_id=args.write_process, content=args.write_stdin)
            elif args.check_stop_process is not None:
                text = get_check_stop_process_text(project_root or ".", args.check_stop_process)
            elif args.stop_process is not None:
                text = get_stop_process_text(project_root or ".", args.stop_process)
            elif args.check_stop_all_processes:
                text = get_check_stop_all_processes_text(project_root or ".")
            elif args.stop_all_processes:
                text = get_stop_all_processes_text(project_root or ".")
            elif args.status:
                text = get_status_text("code", args.approval, None, chat_turns=0)
            elif args.context:
                text = get_context_text(project_root)
            elif args.init is not None:
                text = init_project_instructions(project_root or ".", args.init)
            elif args.doctor:
                payload_extra["doctor"] = get_doctor_report(project_root or ".", provider_env)
                text = get_doctor_text(project_root or ".", provider_env)
            elif args.review:
                text = get_review_text(project_root or ".", max_files=args.review_max_files, max_checks=args.review_max_checks)
            elif args.handoff:
                text = get_handoff_text(
                    project_root or ".",
                    max_files=args.handoff_max_files,
                    max_checks=args.handoff_max_checks,
                    max_status_chars=args.handoff_max_status_chars,
                    max_plan_chars=args.handoff_max_plan_chars,
                )
            elif args.changes:
                text = get_changes_text(project_root or ".", max_files=args.changes_max_files)
            elif args.diff is not None:
                text = get_diff_text(project_root or ".", args.diff or None, max_chars=args.diff_max_chars)
            elif args.diff_hunks is not None:
                text = get_diff_hunks_text(
                    project_root or ".",
                    args.diff_hunks or None,
                    max_hunks=args.diff_hunks_max_hunks,
                    max_lines_per_hunk=args.diff_hunks_max_lines,
                )
            elif args.diff_contexts is not None:
                text = get_diff_contexts_text(
                    project_root or ".",
                    args.diff_contexts or None,
                    context_lines=args.diff_context_lines,
                    max_hunks=args.diff_contexts_max_hunks,
                    max_bytes_per_context=args.diff_contexts_max_bytes,
                )
            elif args.sessions:
                text = get_sessions_text(project_root or ".")
            elif args.last:
                text = get_last_session_text(project_root or ".")
            elif args.session is not None:
                text = get_session_text(args.session, project_root or ".")
            elif args.plan is not None:
                text = get_plan_text(project_root or ".", args.plan or None)
            elif args.transcript is not None:
                session_kwargs = {}
                if args.session_transcript_event_max is not None:
                    session_kwargs["max_events"] = args.session_transcript_event_max
                if args.session_max_text is not None:
                    session_kwargs["max_text"] = args.session_max_text
                text = get_transcript_text(project_root or ".", args.transcript or None, **session_kwargs)
            elif args.session_search is not None:
                session_kwargs = {}
                if args.session_search_match_max is not None:
                    session_kwargs["max_matches"] = args.session_search_match_max
                if args.session_max_text is not None:
                    session_kwargs["max_text"] = args.session_max_text
                if args.session_search_case_sensitive:
                    session_kwargs["case_sensitive"] = True
                text = get_session_search_text(project_root or ".", args.session_search, args.session_search_run, **session_kwargs)
            elif args.session_commands is not None:
                session_kwargs = {}
                if args.session_max_commands is not None:
                    session_kwargs["max_commands"] = args.session_max_commands
                if args.session_max_output_chars is not None:
                    session_kwargs["max_output_chars"] = args.session_max_output_chars
                text = get_session_commands_text(project_root or ".", args.session_commands or None, **session_kwargs)
            elif args.session_output_contexts is not None:
                text = get_session_output_contexts_text(
                    project_root or ".",
                    args.session_output_contexts or None,
                    max_commands=args.session_output_command_max,
                    max_output_chars=args.session_output_max_chars,
                    context_lines=args.session_output_context_lines,
                    max_contexts=args.session_output_context_max,
                    max_bytes_per_context=args.session_output_context_max_bytes,
                )
            elif args.session_output_diagnostics is not None:
                text = get_session_output_diagnostics_text(
                    project_root or ".",
                    args.session_output_diagnostics or None,
                    max_commands=args.session_output_command_max,
                    max_output_chars=args.session_output_max_chars,
                    context_lines=args.session_output_context_lines,
                    max_diagnostics=args.session_output_diagnostic_max,
                    max_contexts=args.session_output_context_max,
                    max_bytes_per_context=args.session_output_context_max_bytes,
                )
            elif args.session_files is not None:
                session_kwargs = {}
                if args.session_max_files is not None:
                    session_kwargs["max_files"] = args.session_max_files
                text = get_session_files_text(project_root or ".", args.session_files or None, **session_kwargs)
            elif args.session_failures is not None:
                session_kwargs = {}
                if args.session_max_failures is not None:
                    session_kwargs["max_failures"] = args.session_max_failures
                if args.session_max_text is not None:
                    session_kwargs["max_text"] = args.session_max_text
                text = get_session_failures_text(project_root or ".", args.session_failures or None, **session_kwargs)
            elif args.session_verification is not None:
                session_kwargs = {}
                if args.session_max_checks is not None:
                    session_kwargs["max_checks"] = args.session_max_checks
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
                text = get_session_handoff_text(project_root or ".", args.session_handoff or None, **session_kwargs)
            elif args.checkpoint is not None:
                text = get_checkpoint_text(project_root or ".", args.checkpoint or None)
            elif args.checkpoints:
                text = get_checkpoints_text(project_root or ".")
            elif args.checkpoint_show is not None:
                text = get_checkpoint_show_text(args.checkpoint_show, project_root or ".")
            elif args.checkpoint_diff is not None:
                text = get_checkpoint_diff_text(args.checkpoint_diff, project_root or ".")
            elif args.checkpoint_status is not None:
                text = get_checkpoint_status_text(args.checkpoint_status, project_root or ".")
            elif args.check_checkpoint_restore is not None:
                text = get_check_checkpoint_restore_text(args.check_checkpoint_restore, project_root or ".")
            elif args.checkpoint_restore is not None:
                text = get_checkpoint_restore_text(args.checkpoint_restore, project_root or ".")
            elif args.check_checkpoint_delete is not None:
                text = get_check_checkpoint_delete_text(args.check_checkpoint_delete, project_root or ".")
            elif args.checkpoint_delete is not None:
                text = get_checkpoint_delete_text(args.checkpoint_delete, project_root or ".")
            elif args.check_checkpoint_prune is not None:
                text = get_check_checkpoint_prune_text(args.check_checkpoint_prune, project_root or ".")
            elif args.checkpoint_prune is not None:
                text = get_checkpoint_prune_text(args.checkpoint_prune, project_root or ".")
            elif args.usage:
                text = get_usage_text(project_root or ".")
            elif args.cost:
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


def resolve_task_text(parts: Sequence[str]) -> str:
    if len(parts) == 1 and parts[0] == "-":
        return sys.stdin.read().strip()
    return " ".join(parts)


def local_result_exit_code(args: argparse.Namespace, text: str) -> int:
    result_flag = any(local_result_arg_selected(getattr(args, name, None)) for name in LOCAL_RESULT_ARG_NAMES)
    if not result_flag:
        return 0
    if text.startswith("Usage:"):
        return 2
    if text == "No sessions found.":
        return 1
    if text.startswith("Session not found:") or text.startswith("Invalid session id:"):
        return 1
    if text.startswith("Tool not found:"):
        return 1
    if has_local_diagnostic_error(text):
        return 1
    if (args.session is not None or args.last) and has_bad_session_summary_status(text):
        return 1
    if args.session_failures is not None and has_positive_top_level_count(text, "failures"):
        return 1
    if text.startswith("Checkpoint not found:") or text.startswith("Invalid checkpoint id:"):
        return 1
    if text.startswith("Path escapes the project directory:"):
        return 1
    if has_top_level_ok(text, "no"):
        return 1
    if has_top_level_field(text, "ready", "no"):
        return 1
    if has_top_level_field(text, "created", "no"):
        return 1
    if has_top_level_field(text, "matches", "no"):
        return 1
    if has_top_level_field(text, "restored", "no"):
        return 1
    if has_top_level_field(text, "deleted", "no"):
        return 1
    if has_top_level_field(text, "canDelete", "no"):
        return 1
    if args.around_many is not None and has_incomplete_top_level_count(text, "contexts"):
        return 1
    if args.read_files is not None and has_incomplete_top_level_count(text, "files"):
        return 1
    if args.read_ranges is not None and has_incomplete_top_level_count(text, "ranges"):
        return 1
    if args.image_info is not None and has_incomplete_top_level_count(text, "images"):
        return 1
    if args.file_info is not None and has_incomplete_top_level_count(text, "paths"):
        return 1
    if args.output_contexts is not None and has_incomplete_top_level_count(text, "contexts"):
        return 1
    if args.output_diagnostics is not None and has_incomplete_top_level_count(text, "contexts"):
        return 1
    if args.python_traceback is not None and has_incomplete_top_level_count(text, "contexts"):
        return 1
    if args.process_output_contexts is not None and has_incomplete_top_level_count(text, "contexts"):
        return 1
    if args.process_output_diagnostics is not None and has_incomplete_top_level_count(text, "contexts"):
        return 1
    if args.session_output_contexts is not None and has_incomplete_top_level_count(text, "contexts"):
        return 1
    if args.session_output_diagnostics is not None and has_incomplete_top_level_count(text, "contexts"):
        return 1
    if args.session_verification is not None and has_session_verification_issue(text):
        return 1
    if args.symbols is not None and has_incomplete_top_level_count(text, "files"):
        return 1
    if args.python_deps is not None and has_incomplete_top_level_count(text, "files"):
        return 1
    if args.code_deps is not None and has_incomplete_top_level_count(text, "files"):
        return 1
    if args.diff is not None and has_top_level_error(text):
        return 1
    if args.port_check is not None and has_top_level_field(text, "reachable", "no"):
        return 1
    if (args.http_check is not None or args.http_fetch is not None) and has_top_level_field(text, "reachable", "no"):
        return 1
    if args.http_check is not None and args.http_contains is not None and has_top_level_field(text, "matched", "no"):
        return 1
    if args.wait_process is not None and (args.wait_stdout is not None or args.wait_stderr is not None) and has_top_level_field(text, "matched", "no"):
        return 1
    if (
        args.processes
        or args.process_output is not None
        or args.process_output_contexts is not None
        or args.process_output_diagnostics is not None
        or args.wait_process is not None
    ) and has_process_status_failure(text):
        return 1
    return 0


def local_result_arg_selected(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return value is not None


def has_top_level_ok(text: str, value: str) -> bool:
    return any(line == f"  ok: {value}" for line in text.splitlines())


def has_top_level_field(text: str, name: str, value: str) -> bool:
    return any(line == f"  {name}: {value}" for line in text.splitlines())


def has_top_level_error(text: str) -> bool:
    return any(line.startswith("  error: ") for line in text.splitlines())


def has_positive_top_level_count(text: str, name: str) -> bool:
    prefix = f"  {name}: "
    for line in text.splitlines():
        if not line.startswith(prefix):
            continue
        try:
            return int(line[len(prefix) :].strip()) > 0
        except ValueError:
            return False
    return False


def has_bad_session_summary_status(text: str) -> bool:
    return any(
        has_top_level_field(text, "status", status)
        for status in ("failed", "blocked", "incomplete")
    )


def has_local_diagnostic_error(text: str) -> bool:
    if text.startswith("Unsupported VIBEAGENT_PROVIDER:"):
        return True
    return any(
        line.startswith("  provider: Unsupported VIBEAGENT_PROVIDER:")
        or line.startswith("  projectConfigError: ")
        or line == "  costRates: invalid"
        for line in text.splitlines()
    )


def has_session_verification_issue(text: str) -> bool:
    active_section: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("pendingChecks:") or stripped.startswith("failedChecks:"):
            active_section = stripped.split(":", 1)[0]
            continue
        if stripped.endswith(":"):
            active_section = None
            continue
        if active_section and stripped.startswith("- "):
            return True
    return False


def has_process_status_failure(text: str) -> bool:
    if has_top_level_field(text, "timedOut", "yes"):
        return True
    for line in text.splitlines():
        if line.startswith("  status: ") and process_status_value_failed(line[len("  status: ") :]):
            return True
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        for field in stripped.split(";"):
            field = field.strip()
            if field.startswith("status=") and process_status_value_failed(field[len("status=") :]):
                return True
    return False


def process_status_value_failed(value: str) -> bool:
    if value == "signaled(.)":
        return False
    if value.startswith("signaled(") and value.endswith(")"):
        return True
    if value.startswith("exited(") and value.endswith(")"):
        try:
            return int(value[len("exited(") : -1]) != 0
        except ValueError:
            return True
    return False


def has_incomplete_top_level_count(text: str, name: str) -> bool:
    prefix = f"  {name}: "
    for line in text.splitlines():
        if not line.startswith(prefix):
            continue
        value = line[len(prefix) :]
        parts = value.split("/", 1)
        if len(parts) != 2:
            continue
        try:
            actual = int(parts[0])
            expected = int(parts[1])
        except ValueError:
            continue
        return actual < expected
    return False


def build_diff_argument(diff_argument: str | None, staged: bool, task_parts: Sequence[str]) -> str | None:
    parts: list[str] = []
    if staged:
        parts.append("--staged")
    if diff_argument:
        parts.append(diff_argument)
    parts.extend(task_parts)
    return " ".join(parts) if parts else None


def parse_interactive_diff_argument(argument: str | None) -> tuple[str | None, int, str | None]:
    usage = "Usage: /diff [--staged|--cached] [--max-chars N] [path]"
    if not argument:
        return None, 12_000, None
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        return None, 12_000, f"{usage}\n  error: {error}"

    diff_parts: list[str] = []
    max_chars = 12_000
    index = 0
    while index < len(parts):
        part = parts[index]
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag == "--max-chars":
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            value, error = parse_interactive_positive_option("--max-chars", raw_value)
            if error:
                return None, 12_000, f"{usage}\n  error: {error}"
            max_chars = int(value)
            continue
        diff_parts.append(part)
        index += 1
    return " ".join(diff_parts) if diff_parts else None, max_chars, None


def parse_interactive_diff_hunks_argument(argument: str | None) -> tuple[str | None, dict[str, int], str | None]:
    usage = "Usage: /diff-hunks [--staged|--cached] [--max-hunks N] [--max-lines N] [path]"
    option_specs = {
        "--max-hunks": ("max_hunks", False),
        "--max-lines": ("max_lines_per_hunk", False),
    }
    return parse_interactive_diff_detail_argument(argument, usage, option_specs)


def parse_interactive_diff_contexts_argument(argument: str | None) -> tuple[str | None, dict[str, int], str | None]:
    usage = "Usage: /diff-contexts [--staged|--cached] [--context-lines N] [--max-hunks N] [--max-bytes N] [path]"
    option_specs = {
        "--context-lines": ("context_lines", True),
        "--max-hunks": ("max_hunks", False),
        "--max-bytes": ("max_bytes_per_context", False),
    }
    return parse_interactive_diff_detail_argument(argument, usage, option_specs)


def parse_interactive_diff_detail_argument(
    argument: str | None,
    usage: str,
    option_specs: dict[str, tuple[str, bool]],
) -> tuple[str | None, dict[str, int], str | None]:
    if not argument:
        return None, {}, None
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        return None, {}, f"{usage}\n  error: {error}"

    diff_parts: list[str] = []
    kwargs: dict[str, int] = {}
    index = 0
    while index < len(parts):
        part = parts[index]
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in option_specs:
            keyword, allow_zero = option_specs[flag]
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            parser = parse_interactive_nonnegative_option if allow_zero else parse_interactive_positive_option
            value, error = parser(flag, raw_value)
            if error:
                return None, {}, f"{usage}\n  error: {error}"
            kwargs[keyword] = int(value)
            continue
        if part.startswith("--") and part not in {"--staged", "--cached", "--"}:
            return None, {}, f"{usage}\n  error: Unknown option: {part}"
        diff_parts.append(part)
        index += 1
    return " ".join(diff_parts) if diff_parts else None, kwargs, None


def build_switch_argument(branch: str, create: bool) -> str:
    return f"--create {branch}" if create else branch


def build_stash_argument(message: str, include_untracked: bool) -> str:
    parts: list[str] = []
    if include_untracked:
        parts.append("--include-untracked")
    if message:
        parts.append(message)
    return " ".join(parts)


def parse_executable_flag_values(values: Sequence[str], flag: str) -> tuple[str, str | None]:
    if len(values) not in (1, 2):
        raise ValueError(f"{flag} expects PATH and optional true|false.")
    return values[0], values[1] if len(values) == 2 else None


def parse_multi_edit_flag_values(values: Sequence[str], flag: str) -> tuple[str, list[str]]:
    if len(values) < 3:
        raise ValueError(f"{flag} expects PATH and at least one OLD NEW pair.")
    if (len(values) - 1) % 2 != 0:
        raise ValueError(f"{flag} expects OLD NEW pairs after PATH.")
    return values[0], list(values[1:])


def parse_cli_json_value(value: str) -> object:
    try:
        return json.loads(value)
    except json.JSONDecodeError as error:
        raise ValueError(f"JSON value is invalid: {error.msg}") from error


def build_context_limit_kwargs(
    max_failures: int | None = None,
    max_files: int | None = None,
    max_commands: int | None = None,
    max_checks: int | None = None,
    max_output_chars: int | None = None,
    max_text: int | None = None,
) -> dict[str, int]:
    values = {
        "max_failures": max_failures,
        "max_files": max_files,
        "max_commands": max_commands,
        "max_checks": max_checks,
        "max_output_chars": max_output_chars,
        "max_text": max_text,
    }
    return {key: value for key, value in values.items() if value is not None}


def run_one_shot(
    task: str,
    request_mode: str,
    approval_policy: ApprovalPolicy,
    resume_arg: str | None = None,
    compact_arg: str | None = None,
    resume_max_failures: int | None = None,
    resume_max_files: int | None = None,
    resume_max_commands: int | None = None,
    resume_max_checks: int | None = None,
    resume_max_output_chars: int | None = None,
    resume_max_text: int | None = None,
    compact_max_failures: int | None = None,
    compact_max_files: int | None = None,
    compact_max_commands: int | None = None,
    compact_max_checks: int | None = None,
    compact_max_output_chars: int | None = None,
    compact_max_text: int | None = None,
    base_dir: str | None = None,
    max_iterations: int | None = None,
    command_timeout_ms: int | None = None,
    max_output_tokens: int | None = None,
    model_retries: int | None = None,
    model_retry_delay_ms: int | None = None,
    model_timeout_ms: int | None = None,
    output_json: bool = False,
    provider_args: argparse.Namespace | None = None,
) -> int:
    try:
        if not task.strip():
            return print_error_result("No task provided.", output_json)
        project_root = resolve_project_root(base_dir) or Path.cwd()
        config_root = project_root
        execution_config = resolve_execution_config(
            config_root,
            max_iterations=max_iterations,
            command_timeout_ms=command_timeout_ms,
            max_output_tokens=max_output_tokens,
            model_retries=model_retries,
            model_retry_delay_ms=model_retry_delay_ms,
            model_timeout_ms=model_timeout_ms,
        )
        provider_env = build_provider_env(provider_args, config_root)
        if request_mode == "chat":
            client = create_chat_client(provider_env)
            response = run_chat(
                task,
                client=client,
                history=[],
                max_output_tokens=execution_config.max_output_tokens,
                model_retries=execution_config.model_retries,
                model_retry_delay_ms=execution_config.model_retry_delay_ms,
                model_timeout_ms=execution_config.model_timeout_ms,
            )
            print_output({"kind": "chat", "success": True, "message": response}, output_json)
            return 0

        resume_context = None
        if resume_arg is not None:
            normalized_resume_arg = normalize_resume_arg(resume_arg)
            resume_kwargs = build_context_limit_kwargs(
                max_failures=resume_max_failures,
                max_files=resume_max_files,
                max_commands=resume_max_commands,
                max_checks=resume_max_checks,
                max_output_chars=resume_max_output_chars,
                max_text=resume_max_text,
            )
            _selected, resume_context, text = get_resume_context(normalized_resume_arg, project_root, **resume_kwargs)
            if resume_context is None and not is_resume_clear_arg(normalized_resume_arg):
                return print_error_result(text, output_json)
        elif compact_arg is not None:
            compact_kwargs = build_context_limit_kwargs(
                max_failures=compact_max_failures,
                max_files=compact_max_files,
                max_commands=compact_max_commands,
                max_checks=compact_max_checks,
                max_output_chars=compact_max_output_chars,
                max_text=compact_max_text,
            )
            _selected, resume_context, text = get_compact_context(normalize_resume_arg(compact_arg), project_root, **compact_kwargs)
            if resume_context is None:
                return print_error_result(text, output_json)
        client = create_chat_client(provider_env)
        result = run_agent(
            task,
            client=client,
            base_dir=project_root,
            max_iterations=execution_config.max_iterations,
            command_timeout_ms=execution_config.command_timeout_ms,
            max_output_tokens=execution_config.max_output_tokens,
            model_retries=execution_config.model_retries,
            model_retry_delay_ms=execution_config.model_retry_delay_ms,
            model_timeout_ms=execution_config.model_timeout_ms,
            approval_handler=build_approval_handler(approval_policy),
            prior_context=resume_context,
        )
        if output_json:
            print_output(
                {
                    "kind": "code",
                    "success": result.success,
                    "status": result.status,
                    "message": result.message,
                    "runId": result.run_id,
                    "runDir": str(result.run_dir),
                    "iterations": result.iterations,
                    "steps": len(result.steps),
                    "completionReady": result.completion_ready,
                    "completionBlockers": result.completion_blockers,
                    "completionWarnings": result.completion_warnings,
                    "completionBlockedCount": result.completion_blocked_count,
                    "latestCompletionBlockers": result.latest_completion_blockers,
                    "latestCompletionPendingChecks": result.latest_completion_pending_verification_checks,
                    "latestCompletionFailedChecks": result.latest_completion_failed_verification_checks,
                    "verificationChecks": result.verification_checks,
                    "pendingVerificationChecks": result.pending_verification_checks,
                    "failedVerificationChecks": result.failed_verification_checks,
                },
                True,
            )
        else:
            print_agent_result(result)
        return 0 if result.success and result.completion_ready else 1
    except KeyboardInterrupt:
        return print_interrupted_result(output_json)
    except Exception as error:
        return print_error_result(format_error(error), output_json, prefix=True)


def print_output(payload: dict[str, object], output_json: bool) -> None:
    if output_json:
        json_payload = dict(payload)
        if json_payload.get("success") is True and "status" not in json_payload:
            json_payload["status"] = "completed"
        print(json.dumps(json_payload, ensure_ascii=False, sort_keys=True))
        return
    text = payload.get("text") if "text" in payload else payload.get("message")
    print("" if text is None else text)


def print_error_result(error: str, output_json: bool, exit_code: int = 1, prefix: bool = False) -> int:
    if output_json:
        print(json.dumps({"kind": "error", "success": False, "status": "failed", "error": error}, ensure_ascii=False, sort_keys=True))
    else:
        print(f"Error: {error}" if prefix else error)
    return exit_code


def print_interrupted_result(output_json: bool) -> int:
    if output_json:
        print(
            json.dumps(
                {"kind": "interrupted", "success": False, "status": "interrupted", "error": "Interrupted."},
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    else:
        print("Interrupted.")
    return 130


def build_focused_tests_kwargs(args: argparse.Namespace) -> dict[str, int]:
    kwargs: dict[str, int] = {}
    if args.focused_tests_max_paths is not None:
        kwargs["max_paths"] = args.focused_tests_max_paths
    if args.focused_tests_max_candidates is not None:
        kwargs["max_candidates"] = args.focused_tests_max_candidates
    if args.focused_tests_max_commands is not None:
        kwargs["max_commands"] = args.focused_tests_max_commands
    return kwargs


def resolve_project_root(value: str | None) -> Path | None:
    if value is None:
        return None
    root = Path(value).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Project directory not found: {value}")
    return root


def build_provider_env(args: argparse.Namespace | None, project_root: Path | None = None) -> dict[str, str | None]:
    env: dict[str, str | None] = dict(os.environ)
    config_root = project_root or Path.cwd()
    for key, value in load_project_config_env(config_root).items():
        if not env.get(key):
            env[key] = value
    arg_provider = getattr(args, "provider", None)
    arg_model_name = getattr(args, "model_name", None)
    arg_base_url = getattr(args, "base_url", None)
    arg_api_key = getattr(args, "api_key", None)
    provider = arg_provider or get_provider_name(env)
    if arg_provider:
        env["VIBEAGENT_PROVIDER"] = arg_provider
    if arg_model_name:
        if provider == "minimax":
            env["MINIMAX_MODEL"] = arg_model_name
        else:
            env["OPENAI_COMPAT_MODEL"] = arg_model_name
            env["DEEPSEEK_MODEL"] = arg_model_name
    if arg_base_url:
        if provider == "minimax":
            env["MINIMAX_BASE_URL"] = arg_base_url
        else:
            env["OPENAI_COMPAT_BASE_URL"] = arg_base_url
            env["DEEPSEEK_BASE_URL"] = arg_base_url
    if arg_api_key:
        if provider == "minimax":
            env["MINIMAX_API_KEY"] = arg_api_key
        else:
            env["OPENAI_COMPAT_API_KEY"] = arg_api_key
            env["DEEPSEEK_API_KEY"] = arg_api_key
    return env


def save_project_config_from_args(args: argparse.Namespace, project_root: str | Path) -> str:
    if args.api_key:
        raise ValueError("--save-config does not write API keys. Use environment variables or --api-key for one command.")
    return save_project_config(
        project_root,
        provider=args.provider,
        model=args.model_name,
        base_url=args.base_url,
        max_iterations=args.max_iterations,
        command_timeout_ms=args.command_timeout_ms,
        max_output_tokens=args.max_output_tokens,
        model_retries=args.model_retries,
        model_retry_delay_ms=args.model_retry_delay_ms,
        model_timeout_ms=args.model_timeout_ms,
    )


def normalize_resume_arg(value: str) -> str | None:
    return value or None


def is_resume_clear_arg(value: str | None) -> bool:
    return isinstance(value, str) and value.strip().lower() in {"off", "clear", "none"}


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a positive integer") from error
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def nonnegative_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a non-negative integer") from error
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    return parsed


def timeout_ms(value: str) -> int:
    parsed = positive_int(value)
    if parsed < 100:
        raise argparse.ArgumentTypeError("must be at least 100")
    return parsed


def parse_interactive_positive_option(flag: str, value: str | None) -> tuple[int | None, str | None]:
    if value is None:
        return None, f"{flag} requires a value."
    try:
        return positive_int(value), None
    except argparse.ArgumentTypeError as error:
        return None, f"{flag} {error}."


def parse_interactive_nonnegative_option(flag: str, value: str | None) -> tuple[int | None, str | None]:
    if value is None:
        return None, f"{flag} requires a value."
    try:
        return nonnegative_int(value), None
    except argparse.ArgumentTypeError as error:
        return None, f"{flag} {error}."


def parse_interactive_timeout_option(flag: str, value: str | None) -> tuple[int | None, str | None]:
    if value is None:
        return None, f"{flag} requires a value."
    try:
        return timeout_ms(value), None
    except argparse.ArgumentTypeError as error:
        return None, f"{flag} {error}."


def parse_interactive_transcript_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int], str | None]:
    usage = "Usage: /transcript [run-id] [--max-events N] [--max-text N]"
    if not argument:
        return None, {}, None
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        return None, {}, f"{usage}\n  error: {error}"
    run_id: str | None = None
    kwargs: dict[str, int] = {}
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--max-events":
            raw_value = parts[index + 1] if index + 1 < len(parts) else None
            value, error = parse_interactive_positive_option(part, raw_value)
            if error:
                return None, {}, f"{usage}\n  error: {error}"
            kwargs["max_events"] = int(value)
            index += 2
            continue
        if part.startswith("--max-events="):
            value, error = parse_interactive_positive_option("--max-events", part.split("=", 1)[1])
            if error:
                return None, {}, f"{usage}\n  error: {error}"
            kwargs["max_events"] = int(value)
            index += 1
            continue
        if part == "--max-text":
            raw_value = parts[index + 1] if index + 1 < len(parts) else None
            value, error = parse_interactive_positive_option(part, raw_value)
            if error:
                return None, {}, f"{usage}\n  error: {error}"
            kwargs["max_text"] = int(value)
            index += 2
            continue
        if part.startswith("--max-text="):
            value, error = parse_interactive_positive_option("--max-text", part.split("=", 1)[1])
            if error:
                return None, {}, f"{usage}\n  error: {error}"
            kwargs["max_text"] = int(value)
            index += 1
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}"
        if run_id is not None:
            return None, {}, usage
        run_id = part
        index += 1
    return run_id, kwargs, None


def parse_interactive_session_search_argument(
    argument: str | None,
) -> tuple[str | None, str | None, dict[str, int | bool], str | None]:
    usage = "Usage: /session-search [--run run-id] [--max-matches N] [--case-sensitive] [--max-text N] <query>"
    if not argument:
        return None, None, {}, usage
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        return None, None, {}, f"{usage}\n  error: {error}"
    run_id: str | None = None
    query_parts: list[str] = []
    kwargs: dict[str, int | bool] = {}
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            query_parts.extend(parts[index + 1 :])
            break
        if part == "--run":
            if index + 1 >= len(parts):
                return None, None, {}, f"{usage}\n  error: --run requires a value."
            run_id = parts[index + 1]
            index += 2
            continue
        if part.startswith("--run="):
            run_id = part.split("=", 1)[1]
            index += 1
            continue
        if part == "--max-matches":
            raw_value = parts[index + 1] if index + 1 < len(parts) else None
            value, error = parse_interactive_positive_option(part, raw_value)
            if error:
                return None, None, {}, f"{usage}\n  error: {error}"
            kwargs["max_matches"] = int(value)
            index += 2
            continue
        if part.startswith("--max-matches="):
            value, error = parse_interactive_positive_option("--max-matches", part.split("=", 1)[1])
            if error:
                return None, None, {}, f"{usage}\n  error: {error}"
            kwargs["max_matches"] = int(value)
            index += 1
            continue
        if part == "--max-text":
            raw_value = parts[index + 1] if index + 1 < len(parts) else None
            value, error = parse_interactive_positive_option(part, raw_value)
            if error:
                return None, None, {}, f"{usage}\n  error: {error}"
            kwargs["max_text"] = int(value)
            index += 2
            continue
        if part.startswith("--max-text="):
            value, error = parse_interactive_positive_option("--max-text", part.split("=", 1)[1])
            if error:
                return None, None, {}, f"{usage}\n  error: {error}"
            kwargs["max_text"] = int(value)
            index += 1
            continue
        if part == "--case-sensitive":
            kwargs["case_sensitive"] = True
            index += 1
            continue
        if part.startswith("--"):
            return None, None, {}, f"{usage}\n  error: Unknown option: {part}"
        query_parts.append(part)
        index += 1
    query = " ".join(query_parts).strip()
    if not query:
        return None, run_id, kwargs, usage
    return query, run_id, kwargs, None


def parse_interactive_session_detail_argument(
    argument: str | None,
    usage: str,
    option_specs: dict[str, tuple[str, bool]],
) -> tuple[str | None, dict[str, int], str | None]:
    if not argument:
        return None, {}, None
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        return None, {}, f"{usage}\n  error: {error}"
    run_id: str | None = None
    kwargs: dict[str, int] = {}
    index = 0
    while index < len(parts):
        part = parts[index]
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in option_specs:
            keyword, allow_zero = option_specs[flag]
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            parser = parse_interactive_nonnegative_option if allow_zero else parse_interactive_positive_option
            value, error = parser(flag, raw_value)
            if error:
                return None, {}, f"{usage}\n  error: {error}"
            kwargs[keyword] = int(value)
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}"
        if run_id is not None:
            return None, {}, usage
        run_id = part
        index += 1
    return run_id, kwargs, None


def parse_interactive_process_output_argument(
    argument: str | None,
    usage: str,
    option_specs: dict[str, tuple[str, bool]],
) -> tuple[str | None, dict[str, int], str | None]:
    if not argument:
        return None, {}, usage
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        return None, {}, f"{usage}\n  error: {error}"
    process_id: str | None = None
    legacy_max_chars: int | None = None
    kwargs: dict[str, int] = {}
    index = 0
    while index < len(parts):
        part = parts[index]
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in option_specs:
            keyword, allow_zero = option_specs[flag]
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            parser = parse_interactive_nonnegative_option if allow_zero else parse_interactive_positive_option
            value, error = parser(flag, raw_value)
            if error:
                return None, {}, f"{usage}\n  error: {error}"
            kwargs[keyword] = int(value)
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}"
        if process_id is None:
            process_id = part
            index += 1
            continue
        if legacy_max_chars is None:
            value, error = parse_interactive_positive_option("[chars]", part)
            if error:
                return None, {}, f"{usage}\n  error: invalid max chars: {part}"
            legacy_max_chars = int(value)
            kwargs["max_output_chars"] = legacy_max_chars
            index += 1
            continue
        return None, {}, usage
    if process_id is None:
        return None, {}, f"{usage}\n  error: process id is required."
    return process_id, kwargs, None


def parse_interactive_port_argument(
    argument: str | None,
) -> tuple[int | None, dict[str, int | str], str | None, bool]:
    usage = "Usage: /port <port> [host] [timeout-ms] [--host HOST] [--timeout-ms N]"
    if not argument:
        return None, {}, None, False
    value_options = {
        "--host": ("host", "string"),
        "--timeout-ms": ("timeout_ms", "timeout"),
    }
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in value_options):
            return None, {}, f"{usage}\n  error: {error}", True
        return None, {}, None, False

    uses_named_options = "--" in parts
    if not uses_named_options:
        for part in parts:
            flag = part.split("=", 1)[0] if part.startswith("--") else part
            if part.startswith("--") or flag in value_options:
                uses_named_options = True
                break
    if not uses_named_options:
        return None, {}, None, False

    kwargs: dict[str, int | str] = {}
    positional: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            positional.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in value_options:
            keyword, value_type = value_options[flag]
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            if value_type == "timeout":
                value, error = parse_interactive_timeout_option(flag, raw_value)
            else:
                if raw_value is None:
                    value, error = None, f"{flag} requires a value."
                elif raw_value == "":
                    value, error = None, f"{flag} must be a non-empty string."
                else:
                    value, error = raw_value, None
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            kwargs[keyword] = value
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}", True
        positional.append(part)
        index += 1

    if not positional:
        return None, {}, f"{usage}\n  error: port is required.", True
    if len(positional) > 1:
        return None, {}, usage, True
    value, error = parse_interactive_positive_option("[port]", positional[0])
    if error:
        return None, {}, f"{usage}\n  error: invalid port: {positional[0]}", True
    return int(value), kwargs, None, True


def parse_interactive_http_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int | str | bool], str | None, bool]:
    usage = "Usage: /http <url> [contains] [--timeout-ms N] [--max-body-chars N] [--contains TEXT] [--regex]"
    if not argument:
        return None, {}, None, False
    value_options: dict[str, tuple[str, str]] = {
        "--timeout-ms": ("timeout_ms", "timeout"),
        "--max-body-chars": ("max_body_chars", "positive"),
        "--contains": ("contains", "string"),
    }
    bool_options = {"--regex": "regex"}
    recognized_flags = set(value_options) | set(bool_options)
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in recognized_flags):
            return None, {}, f"{usage}\n  error: {error}", True
        return None, {}, None, False

    uses_named_options = "--" in parts
    if not uses_named_options:
        for part in parts:
            flag = part.split("=", 1)[0] if part.startswith("--") else part
            if part.startswith("--") or flag in recognized_flags:
                uses_named_options = True
                break
    if not uses_named_options:
        return None, {}, None, False

    kwargs: dict[str, int | str | bool] = {}
    positional: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            positional.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in bool_options:
            if "=" in part:
                return None, {}, f"{usage}\n  error: {flag} does not take a value.", True
            kwargs[bool_options[flag]] = True
            index += 1
            continue
        if flag in value_options:
            keyword, value_type = value_options[flag]
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            if value_type == "timeout":
                value, error = parse_interactive_timeout_option(flag, raw_value)
            elif value_type == "positive":
                value, error = parse_interactive_positive_option(flag, raw_value)
            else:
                if raw_value is None:
                    value, error = None, f"{flag} requires a value."
                elif raw_value == "":
                    value, error = None, f"{flag} must be a non-empty string."
                else:
                    value, error = raw_value, None
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            kwargs[keyword] = value
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}", True
        positional.append(part)
        index += 1

    if not positional:
        return None, {}, f"{usage}\n  error: url is required.", True
    url = positional[0]
    positional_contains = " ".join(positional[1:]).strip() or None
    if positional_contains is not None:
        if "contains" in kwargs:
            return None, {}, f"{usage}\n  error: contains can only be provided once.", True
        kwargs["contains"] = positional_contains
    return url, kwargs, None, True


def parse_interactive_http_fetch_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int], str | None, bool]:
    usage = "Usage: /http-fetch <url> [--timeout-ms N] [--max-body-chars N]"
    if not argument:
        return None, {}, None, False
    option_specs = {
        "--timeout-ms": ("timeout_ms", "timeout"),
        "--max-body-chars": ("max_body_chars", "positive"),
    }
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in option_specs):
            return None, {}, f"{usage}\n  error: {error}", True
        return None, {}, None, False

    uses_named_options = "--" in parts
    if not uses_named_options:
        for part in parts:
            flag = part.split("=", 1)[0] if part.startswith("--") else part
            if part.startswith("--") or flag in option_specs:
                uses_named_options = True
                break
    if not uses_named_options:
        return None, {}, None, False

    kwargs: dict[str, int] = {}
    positional: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            positional.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in option_specs:
            keyword, value_type = option_specs[flag]
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            if value_type == "timeout":
                value, error = parse_interactive_timeout_option(flag, raw_value)
            else:
                value, error = parse_interactive_positive_option(flag, raw_value)
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            kwargs[keyword] = int(value)
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}", True
        positional.append(part)
        index += 1

    if not positional:
        return None, {}, f"{usage}\n  error: url is required.", True
    if len(positional) > 1:
        return None, {}, usage, True
    return positional[0], kwargs, None, True


def parse_interactive_search_argument(
    argument: str | None,
    *,
    include_max_bytes: bool,
) -> tuple[str | None, dict[str, int | str | bool], str | None, bool]:
    usage = (
        "Usage: /search-contexts [--path PATH] [--max-matches N] [--regex] [--ignore-case] "
        "[--context-lines N] [--max-bytes N] -- <query>"
        if include_max_bytes
        else "Usage: /search [--path PATH] [--max-matches N] [--regex] [--ignore-case] [--context-lines N] -- <query>"
    )
    if not argument:
        return None, {}, None, False
    value_options: dict[str, tuple[str, str]] = {
        "--path": ("path", "string"),
        "--max-matches": ("max_matches", "positive"),
        "--context-lines": ("context_lines", "nonnegative"),
    }
    if include_max_bytes:
        value_options["--max-bytes"] = ("max_bytes_per_context", "positive")
    bool_options = {
        "--regex": ("regex", True),
        "--ignore-case": ("case_sensitive", False),
        "--case-insensitive": ("case_sensitive", False),
        "--case-sensitive": ("case_sensitive", True),
    }
    recognized_flags = set(value_options) | set(bool_options)
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in recognized_flags):
            return None, {}, f"{usage}\n  error: {error}", True
        return None, {}, None, False

    uses_named_options = "--" in parts
    if not uses_named_options:
        for part in parts:
            flag = part.split("=", 1)[0] if part.startswith("--") else part
            if part.startswith("--") or flag in recognized_flags:
                uses_named_options = True
                break
    if not uses_named_options:
        return None, {}, None, False

    kwargs: dict[str, int | str | bool] = {}
    query_parts: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            query_parts.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in bool_options:
            if "=" in part:
                return None, {}, f"{usage}\n  error: {flag} does not take a value.", True
            keyword, value = bool_options[flag]
            kwargs[keyword] = value
            index += 1
            continue
        if flag in value_options:
            keyword, value_type = value_options[flag]
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            if value_type == "positive":
                value, error = parse_interactive_positive_option(flag, raw_value)
            elif value_type == "nonnegative":
                value, error = parse_interactive_nonnegative_option(flag, raw_value)
            else:
                if raw_value is None:
                    value, error = None, f"{flag} requires a value."
                elif raw_value == "":
                    value, error = None, f"{flag} must be a non-empty string."
                else:
                    value, error = raw_value, None
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            kwargs[keyword] = value
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}", True
        query_parts.append(part)
        index += 1

    query = " ".join(query_parts).strip()
    if not query:
        return None, {}, f"{usage}\n  error: query is required.", True
    return query, kwargs, None, True


def parse_interactive_overview_argument(
    argument: str | None,
) -> tuple[dict[str, int], str | None, bool]:
    usage = "Usage: /overview [--max-files N] [--max-commands N] [--max-checks N]"
    if not argument:
        return {}, None, False
    option_specs = {
        "--max-files": "max_files",
        "--max-commands": "max_commands",
        "--max-checks": "max_checks",
    }
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in option_specs):
            return {}, f"{usage}\n  error: {error}", True
        return {}, None, False

    uses_named_options = "--" in parts
    if not uses_named_options:
        for part in parts:
            flag = part.split("=", 1)[0] if part.startswith("--") else part
            if part.startswith("--") or flag in option_specs:
                uses_named_options = True
                break
    if not uses_named_options:
        return {}, None, False

    kwargs: dict[str, int] = {}
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            if parts[index + 1 :]:
                return {}, usage, True
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in option_specs:
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            value, error = parse_interactive_positive_option(flag, raw_value)
            if error:
                return {}, f"{usage}\n  error: {error}", True
            kwargs[option_specs[flag]] = int(value)
            continue
        if part.startswith("--"):
            return {}, f"{usage}\n  error: Unknown option: {part}", True
        return {}, usage, True
    return kwargs, None, True


def parse_interactive_repo_map_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int], str | None, bool]:
    usage = "Usage: /repo-map [path] [--max-depth N] [--max-files N] [--max-symbols N]"
    if not argument:
        return None, {}, None, False
    option_specs = {
        "--max-depth": ("max_depth", "nonnegative"),
        "--max-files": ("max_files", "positive"),
        "--max-symbols": ("max_symbols", "positive"),
    }
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in option_specs):
            return None, {}, f"{usage}\n  error: {error}", True
        return None, {}, None, False

    uses_named_options = "--" in parts
    if not uses_named_options:
        for part in parts:
            flag = part.split("=", 1)[0] if part.startswith("--") else part
            if part.startswith("--") or flag in option_specs:
                uses_named_options = True
                break
    if not uses_named_options:
        return None, {}, None, False

    kwargs: dict[str, int] = {}
    path_parts: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            path_parts.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in option_specs:
            keyword, value_type = option_specs[flag]
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            parser = parse_interactive_nonnegative_option if value_type == "nonnegative" else parse_interactive_positive_option
            value, error = parser(flag, raw_value)
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            kwargs[keyword] = int(value)
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}", True
        path_parts.append(part)
        index += 1

    if len(path_parts) > 1:
        return None, {}, usage, True
    path = path_parts[0].strip() if path_parts else None
    if path == "":
        path = None
    return path, kwargs, None, True


def parse_interactive_glob_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int], str | None, bool]:
    usage = "Usage: /glob [--max-matches N] -- <pattern>"
    if not argument:
        return None, {}, None, False
    option_specs = {"--max-matches": "max_matches"}
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in option_specs):
            return None, {}, f"{usage}\n  error: {error}", True
        return None, {}, None, False

    uses_named_options = "--" in parts
    if not uses_named_options:
        for part in parts:
            flag = part.split("=", 1)[0] if part.startswith("--") else part
            if part.startswith("--") or flag in option_specs:
                uses_named_options = True
                break
    if not uses_named_options:
        return None, {}, None, False

    kwargs: dict[str, int] = {}
    pattern_parts: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            pattern_parts.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in option_specs:
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            value, error = parse_interactive_positive_option(flag, raw_value)
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            kwargs[option_specs[flag]] = int(value)
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}", True
        pattern_parts.append(part)
        index += 1

    pattern = " ".join(pattern_parts).strip()
    if not pattern:
        return None, {}, f"{usage}\n  error: pattern is required.", True
    return pattern, kwargs, None, True


def parse_interactive_todos_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int], str | None, bool]:
    usage = "Usage: /todos [--max-items N] [--max-files N] -- [path]"
    if not argument:
        return None, {}, None, False
    option_specs = {
        "--max-items": "max_items",
        "--max-files": "max_files",
    }
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in option_specs):
            return None, {}, f"{usage}\n  error: {error}", True
        return None, {}, None, False

    uses_named_options = "--" in parts
    if not uses_named_options:
        for part in parts:
            flag = part.split("=", 1)[0] if part.startswith("--") else part
            if part.startswith("--") or flag in option_specs:
                uses_named_options = True
                break
    if not uses_named_options:
        return None, {}, None, False

    kwargs: dict[str, int] = {}
    path_parts: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            path_parts.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in option_specs:
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            value, error = parse_interactive_positive_option(flag, raw_value)
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            kwargs[option_specs[flag]] = int(value)
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}", True
        path_parts.append(part)
        index += 1

    if len(path_parts) > 1:
        return None, {}, usage, True
    path = path_parts[0].strip() if path_parts else None
    if path == "":
        path = None
    return path, kwargs, None, True


def parse_interactive_option_limit_argument(
    argument: str | None,
    usage: str,
    option_specs: dict[str, str],
) -> tuple[dict[str, int], str | None, bool]:
    if not argument:
        return {}, None, False
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in option_specs):
            return {}, f"{usage}\n  error: {error}", True
        return {}, None, False

    uses_named_options = False
    for part in parts:
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if part.startswith("--") or flag in option_specs:
            uses_named_options = True
            break
    if not uses_named_options:
        return {}, usage, True

    kwargs: dict[str, int] = {}
    index = 0
    while index < len(parts):
        part = parts[index]
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in option_specs:
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            value, error = parse_interactive_positive_option(flag, raw_value)
            if error:
                return {}, f"{usage}\n  error: {error}", True
            kwargs[option_specs[flag]] = int(value)
            continue
        return {}, f"{usage}\n  error: Unknown option: {part}", True

    return kwargs, None, True


def parse_interactive_commands_argument(
    argument: str | None,
) -> tuple[dict[str, int], str | None, bool]:
    return parse_interactive_option_limit_argument(
        argument,
        "Usage: /commands [--max-commands N] [--max-files N]",
        {"--max-commands": "max_commands", "--max-files": "max_files"},
    )


def parse_interactive_manifests_argument(
    argument: str | None,
) -> tuple[dict[str, int], str | None, bool]:
    return parse_interactive_option_limit_argument(
        argument,
        "Usage: /manifests [--max-files N] [--max-items N]",
        {"--max-files": "max_files", "--max-items": "max_items"},
    )


def parse_interactive_instructions_argument(
    argument: str | None,
) -> tuple[dict[str, int], str | None, bool]:
    return parse_interactive_option_limit_argument(
        argument,
        "Usage: /instructions [--max-files N] [--max-bytes N]",
        {"--max-files": "max_files", "--max-bytes": "max_bytes"},
    )


def parse_interactive_test_paths_argument(
    argument: str | None,
    usage: str,
    include_max_commands: bool = False,
) -> tuple[str | None, dict[str, int], str | None, bool]:
    if not argument:
        return None, {}, None, False
    option_specs = {
        "--max-paths": "max_paths",
        "--max-candidates": "max_candidates",
    }
    if include_max_commands:
        option_specs["--max-commands"] = "max_commands"
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in option_specs):
            return None, {}, f"{usage}\n  error: {error}", True
        return None, {}, None, False

    uses_named_options = "--" in parts
    if not uses_named_options:
        for part in parts:
            flag = part.split("=", 1)[0] if part.startswith("--") else part
            if part.startswith("--") or flag in option_specs:
                uses_named_options = True
                break
    if not uses_named_options:
        return None, {}, None, False

    kwargs: dict[str, int] = {}
    path_parts: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            path_parts.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in option_specs:
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            value, error = parse_interactive_positive_option(flag, raw_value)
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            kwargs[option_specs[flag]] = int(value)
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}", True
        path_parts.append(part)
        index += 1

    path_argument = shlex.join(path_parts) if path_parts else None
    return path_argument, kwargs, None, True


def parse_interactive_output_analysis_argument(
    argument: str | None,
    usage: str,
    include_max_diagnostics: bool = False,
) -> tuple[str | None, dict[str, int], str | None, bool]:
    if not argument:
        return None, {}, None, False
    option_specs: dict[str, tuple[str, str]] = {
        "--context-lines": ("context_lines", "nonnegative"),
        "--max-contexts": ("max_contexts", "positive"),
        "--max-bytes": ("max_bytes_per_context", "positive"),
    }
    if include_max_diagnostics:
        option_specs["--max-diagnostics"] = ("max_diagnostics", "positive")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in option_specs):
            return None, {}, f"{usage}\n  error: {error}", True
        return argument, {}, None, False

    uses_named_options = False
    if parts:
        first_flag = parts[0].split("=", 1)[0] if parts[0].startswith("--") else parts[0]
        uses_named_options = parts[0] == "--" or parts[0].startswith("--") or first_flag in option_specs
    if not uses_named_options:
        return argument, {}, None, False

    kwargs: dict[str, int] = {}
    text_parts: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            text_parts.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in option_specs:
            keyword, value_type = option_specs[flag]
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            parser = parse_interactive_nonnegative_option if value_type == "nonnegative" else parse_interactive_positive_option
            value, error = parser(flag, raw_value)
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            kwargs[keyword] = int(value)
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}", True
        text_parts.extend(parts[index:])
        break

    text = shlex.join(text_parts).strip() if text_parts else None
    if not text:
        return None, {}, f"{usage}\n  error: text is required.", True
    return text, kwargs, None, True


def parse_interactive_max_bytes_argument(
    argument: str | None,
    usage: str,
    keyword: str,
    required_message: str,
) -> tuple[str | None, dict[str, int], str | None, bool]:
    if not argument:
        return None, {}, None, False
    option_specs = {"--max-bytes": keyword}
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in option_specs):
            return None, {}, f"{usage}\n  error: {error}", True
        return None, {}, None, False

    uses_named_options = "--" in parts
    if not uses_named_options:
        for part in parts:
            flag = part.split("=", 1)[0] if part.startswith("--") else part
            if part.startswith("--") or flag in option_specs:
                uses_named_options = True
                break
    if not uses_named_options:
        return None, {}, None, False

    kwargs: dict[str, int] = {}
    positional: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            positional.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in option_specs:
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            value, error = parse_interactive_positive_option(flag, raw_value)
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            kwargs[option_specs[flag]] = int(value)
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}", True
        positional.append(part)
        index += 1

    if not positional:
        return None, {}, f"{usage}\n  error: {required_message}", True
    argument_text = shlex.join(positional)
    return argument_text, kwargs, None, True


def parse_interactive_read_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int], str | None, bool]:
    return parse_interactive_max_bytes_argument(
        argument,
        "Usage: /read [--max-bytes N] -- <path> [start[:end]]",
        "max_bytes",
        "path is required.",
    )


def parse_interactive_tail_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int], str | None, bool]:
    return parse_interactive_max_bytes_argument(
        argument,
        "Usage: /tail [--max-bytes N] -- <path> [lines]",
        "max_bytes",
        "path is required.",
    )


def parse_interactive_around_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int], str | None, bool]:
    return parse_interactive_max_bytes_argument(
        argument,
        "Usage: /around [--max-bytes N] -- <path> <line> [context-lines]",
        "max_bytes",
        "path and line are required.",
    )


def parse_interactive_around_many_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int], str | None, bool]:
    return parse_interactive_max_bytes_argument(
        argument,
        "Usage: /around-many [--max-bytes N] -- <path:line[:context-lines]...>",
        "max_bytes_per_context",
        "at least one context is required.",
    )


def parse_interactive_read_ranges_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int], str | None, bool]:
    return parse_interactive_max_bytes_argument(
        argument,
        "Usage: /read-ranges [--max-bytes N] -- <path:start[:end]...>",
        "max_bytes_per_range",
        "at least one range is required.",
    )


def parse_interactive_read_files_argument(
    argument: str | None,
) -> tuple[list[str] | None, dict[str, int], str | None, bool]:
    usage = "Usage: /read-files [--max-bytes N] -- <path...>"
    if not argument:
        return None, {}, None, False
    option_specs = {"--max-bytes": "max_bytes_per_file"}
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in option_specs):
            return None, {}, f"{usage}\n  error: {error}", True
        return None, {}, None, False

    uses_named_options = "--" in parts
    if not uses_named_options:
        for part in parts:
            flag = part.split("=", 1)[0] if part.startswith("--") else part
            if part.startswith("--") or flag in option_specs:
                uses_named_options = True
                break
    if not uses_named_options:
        return None, {}, None, False

    kwargs: dict[str, int] = {}
    paths: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            paths.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in option_specs:
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            value, error = parse_interactive_positive_option(flag, raw_value)
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            kwargs[option_specs[flag]] = int(value)
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}", True
        paths.append(part)
        index += 1

    if not paths:
        return None, {}, f"{usage}\n  error: at least one path is required.", True
    return paths, kwargs, None, True


def parse_interactive_tree_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int], str | None, bool]:
    usage = "Usage: /tree [path] [--max-depth N] [--max-entries N]"
    if not argument:
        return None, {}, None, False
    option_specs = {
        "--max-depth": ("max_depth", "nonnegative"),
        "--max-entries": ("max_entries", "positive"),
    }
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in option_specs):
            return None, {}, f"{usage}\n  error: {error}", True
        return None, {}, None, False

    uses_named_options = "--" in parts
    if not uses_named_options:
        for part in parts:
            flag = part.split("=", 1)[0] if part.startswith("--") else part
            if part.startswith("--") or flag in option_specs:
                uses_named_options = True
                break
    if not uses_named_options:
        return None, {}, None, False

    kwargs: dict[str, int] = {}
    path_parts: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            path_parts.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in option_specs:
            keyword, value_type = option_specs[flag]
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            parser = parse_interactive_nonnegative_option if value_type == "nonnegative" else parse_interactive_positive_option
            value, error = parser(flag, raw_value)
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            kwargs[keyword] = int(value)
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}", True
        path_parts.append(part)
        index += 1

    if len(path_parts) > 1:
        return None, {}, usage, True
    path = path_parts[0].strip() if path_parts else None
    if path == "":
        path = None
    return path, kwargs, None, True


def parse_interactive_symbols_argument(
    argument: str | None,
) -> tuple[list[str] | None, dict[str, int], str | None, bool]:
    usage = "Usage: /symbols [--max-symbols N] -- <path...>"
    if not argument:
        return None, {}, None, False
    option_specs = {"--max-symbols": "max_symbols"}
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in option_specs):
            return None, {}, f"{usage}\n  error: {error}", True
        return None, {}, None, False

    uses_named_options = "--" in parts
    if not uses_named_options:
        for part in parts:
            flag = part.split("=", 1)[0] if part.startswith("--") else part
            if part.startswith("--") or flag in option_specs:
                uses_named_options = True
                break
    if not uses_named_options:
        return None, {}, None, False

    kwargs: dict[str, int] = {}
    paths: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            paths.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in option_specs:
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            value, error = parse_interactive_positive_option(flag, raw_value)
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            kwargs[option_specs[flag]] = int(value)
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}", True
        paths.append(part)
        index += 1

    if not paths:
        return None, {}, f"{usage}\n  error: at least one path is required.", True
    return paths, kwargs, None, True


def parse_interactive_python_symbol_argument(
    argument: str | None,
    *,
    command_name: str,
    include_max_lines: bool = False,
    include_context: bool = False,
) -> tuple[str | None, str | None, dict[str, int], str | None, bool]:
    options = "[--path PATH] [--max-matches N]"
    if include_max_lines:
        options += " [--max-lines N]"
    if include_context:
        options += " [--context-lines N] [--max-bytes N]"
    usage = f"Usage: /{command_name} {options} -- <symbol> [path]"
    if not argument:
        return None, None, {}, None, False

    value_options: dict[str, tuple[str, str]] = {
        "--path": ("path", "string"),
        "--max-matches": ("max_matches", "positive"),
    }
    if include_max_lines:
        value_options["--max-lines"] = ("max_lines", "positive")
    if include_context:
        value_options["--context-lines"] = ("context_lines", "nonnegative")
        value_options["--max-bytes"] = ("max_bytes_per_context", "positive")

    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in value_options):
            return None, None, {}, f"{usage}\n  error: {error}", True
        return None, None, {}, None, False

    uses_named_options = "--" in parts
    if not uses_named_options:
        for part in parts:
            flag = part.split("=", 1)[0] if part.startswith("--") else part
            if part.startswith("--") or flag in value_options:
                uses_named_options = True
                break
    if not uses_named_options:
        return None, None, {}, None, False

    symbol_parts: list[str] = []
    kwargs: dict[str, int] = {}
    path: str | None = None
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            symbol_parts.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in value_options:
            keyword, value_type = value_options[flag]
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            if value_type == "positive":
                value, error = parse_interactive_positive_option(flag, raw_value)
            elif value_type == "nonnegative":
                value, error = parse_interactive_nonnegative_option(flag, raw_value)
            else:
                if raw_value is None:
                    value, error = None, f"{flag} requires a value."
                elif raw_value == "":
                    value, error = None, f"{flag} must be a non-empty string."
                else:
                    value, error = raw_value, None
            if error:
                return None, None, {}, f"{usage}\n  error: {error}", True
            if keyword == "path":
                path = str(value)
            else:
                kwargs[keyword] = int(value)
            continue
        if part.startswith("--"):
            return None, None, {}, f"{usage}\n  error: Unknown option: {part}", True
        symbol_parts.append(part)
        index += 1

    if not symbol_parts:
        return None, path, kwargs, f"{usage}\n  error: symbol is required.", True
    if len(symbol_parts) > 2:
        return None, None, {}, usage, True
    if len(symbol_parts) == 2:
        if path is not None:
            return None, None, {}, f"{usage}\n  error: path can only be provided once.", True
        path = symbol_parts[1]
    return symbol_parts[0], path, kwargs, None, True


def parse_interactive_wait_process_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int | str | bool], str | None, bool]:
    usage = (
        "Usage: /wait-process <id> [timeout-ms] [chars] "
        "[--timeout-ms N] [--max-chars N] [--stdout TEXT] [--stderr TEXT] [--regex]"
    )
    if not argument:
        return None, {}, None, False
    value_options: dict[str, tuple[str, str]] = {
        "--timeout-ms": ("timeout_ms", "timeout"),
        "--max-chars": ("max_output_chars", "positive"),
        "--stdout": ("stdout_contains", "string"),
        "--stderr": ("stderr_contains", "string"),
    }
    bool_options = {"--regex": "regex"}
    recognized_flags = set(value_options) | set(bool_options)
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in recognized_flags):
            return None, {}, f"{usage}\n  error: {error}", True
        return None, {}, None, False

    uses_named_options = "--" in parts
    if not uses_named_options:
        for part in parts:
            flag = part.split("=", 1)[0] if part.startswith("--") else part
            if part.startswith("--") or flag in recognized_flags:
                uses_named_options = True
                break
    if not uses_named_options:
        return None, {}, None, False

    kwargs: dict[str, int | str | bool] = {}
    positional: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            positional.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in bool_options:
            if "=" in part:
                return None, {}, f"{usage}\n  error: {flag} does not take a value.", True
            kwargs[bool_options[flag]] = True
            index += 1
            continue
        if flag in value_options:
            keyword, value_type = value_options[flag]
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            if value_type == "timeout":
                value, error = parse_interactive_timeout_option(flag, raw_value)
            elif value_type == "positive":
                value, error = parse_interactive_positive_option(flag, raw_value)
            else:
                if raw_value is None:
                    value, error = None, f"{flag} requires a value."
                elif raw_value == "":
                    value, error = None, f"{flag} must be a non-empty string."
                else:
                    value, error = raw_value, None
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            kwargs[keyword] = value
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}", True
        positional.append(part)
        index += 1

    if not positional:
        return None, {}, f"{usage}\n  error: process id is required.", True
    if len(positional) > 3:
        return None, {}, usage, True
    process_id = positional[0]
    if len(positional) >= 2:
        value, error = parse_interactive_timeout_option("[timeout-ms]", positional[1])
        if error:
            return None, {}, f"{usage}\n  error: invalid timeout ms: {positional[1]}", True
        kwargs["timeout_ms"] = int(value)
    if len(positional) == 3:
        value, error = parse_interactive_positive_option("[chars]", positional[2])
        if error:
            return None, {}, f"{usage}\n  error: invalid max chars: {positional[2]}", True
        kwargs["max_output_chars"] = int(value)
    return process_id, kwargs, None, True


def parse_interactive_run_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int | str | bool], str | None, bool]:
    usage = (
        "Usage: /run [--timeout-ms N] [--max-chars N] [--cwd PATH] "
        "[--output-contexts] [--output-diagnostics] [--context-lines N] "
        "[--max-diagnostics N] [--max-contexts N] [--max-bytes N] -- <cmd>"
    )
    if not argument:
        return None, {}, None, False
    value_options: dict[str, tuple[str, str]] = {
        "--timeout-ms": ("timeout_ms", "timeout"),
        "--max-chars": ("max_output_chars", "positive"),
        "--cwd": ("cwd", "string"),
        "--context-lines": ("context_lines", "nonnegative"),
        "--max-diagnostics": ("max_diagnostics", "positive"),
        "--max-contexts": ("max_contexts", "positive"),
        "--max-bytes": ("max_bytes_per_context", "positive"),
    }
    bool_options = {
        "--output-contexts": "extract_output_contexts",
        "--output-diagnostics": "extract_output_diagnostics",
    }
    recognized_flags = set(value_options) | set(bool_options)
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in recognized_flags):
            return None, {}, f"{usage}\n  error: {error}", True
        return argument, {}, None, False

    uses_named_options = False
    for part in parts:
        if part == "--":
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in recognized_flags:
            uses_named_options = True
            break
        break
    if not uses_named_options:
        return argument, {}, None, False

    kwargs: dict[str, int | str | bool] = {}
    command_parts: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            command_parts.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in bool_options:
            if "=" in part:
                return None, {}, f"{usage}\n  error: {flag} does not take a value.", True
            kwargs[bool_options[flag]] = True
            index += 1
            continue
        if flag in value_options:
            keyword, value_type = value_options[flag]
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            if value_type == "timeout":
                value, error = parse_interactive_timeout_option(flag, raw_value)
            elif value_type == "nonnegative":
                value, error = parse_interactive_nonnegative_option(flag, raw_value)
            elif value_type == "positive":
                value, error = parse_interactive_positive_option(flag, raw_value)
            else:
                if raw_value is None:
                    value, error = None, f"{flag} requires a value."
                else:
                    value, error = raw_value, None
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            kwargs[keyword] = value
            continue
        command_parts.extend(parts[index:])
        break

    command = shlex.join(command_parts).strip()
    if not command:
        return None, {}, f"{usage}\n  error: command is required.", True
    return command, kwargs, None, True


def parse_interactive_run_sequence_argument(
    argument: str | None,
) -> tuple[list[str] | None, dict[str, int | str | bool], str | None, bool]:
    usage = (
        "Usage: /run-seq [--timeout-ms N] [--max-chars N] [--cwd PATH] "
        "[--continue-on-failure] [--output-contexts] [--output-diagnostics] "
        "[--context-lines N] [--max-diagnostics N] [--max-contexts N] "
        "[--max-bytes N] -- <cmd> ;; <cmd>"
    )
    if not argument:
        return None, {}, None, False
    value_options: dict[str, tuple[str, str]] = {
        "--timeout-ms": ("timeout_ms", "timeout"),
        "--max-chars": ("max_output_chars", "positive"),
        "--cwd": ("cwd", "string"),
        "--context-lines": ("context_lines", "nonnegative"),
        "--max-diagnostics": ("max_diagnostics", "positive"),
        "--max-contexts": ("max_contexts", "positive"),
        "--max-bytes": ("max_bytes_per_context", "positive"),
    }
    bool_options = {
        "--output-contexts": ("extract_output_contexts", True),
        "--output-diagnostics": ("extract_output_diagnostics", True),
        "--continue-on-failure": ("stop_on_failure", False),
        "--stop-on-failure": ("stop_on_failure", True),
    }
    recognized_flags = set(value_options) | set(bool_options)
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in recognized_flags):
            return None, {}, f"{usage}\n  error: {error}", True
        return None, {}, None, False

    uses_named_options = False
    for part in parts:
        if part == "--":
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in recognized_flags:
            uses_named_options = True
            break
        break
    if not uses_named_options:
        return None, {}, None, False

    kwargs: dict[str, int | str | bool] = {}
    command_parts: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            command_parts.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in bool_options:
            if "=" in part:
                return None, {}, f"{usage}\n  error: {flag} does not take a value.", True
            keyword, value = bool_options[flag]
            kwargs[keyword] = value
            index += 1
            continue
        if flag in value_options:
            keyword, value_type = value_options[flag]
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            if value_type == "timeout":
                value, error = parse_interactive_timeout_option(flag, raw_value)
            elif value_type == "nonnegative":
                value, error = parse_interactive_nonnegative_option(flag, raw_value)
            elif value_type == "positive":
                value, error = parse_interactive_positive_option(flag, raw_value)
            else:
                if raw_value is None:
                    value, error = None, f"{flag} requires a value."
                else:
                    value, error = raw_value, None
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            kwargs[keyword] = value
            continue
        command_parts.extend(parts[index:])
        break

    commands: list[str] = []
    current: list[str] = []
    for part in command_parts:
        if part == ";;":
            command = shlex.join(current).strip()
            if command:
                commands.append(command)
            current = []
            continue
        current.append(part)
    command = shlex.join(current).strip()
    if command:
        commands.append(command)
    if not commands:
        return None, {}, f"{usage}\n  error: at least one command is required.", True
    if len(commands) > 10:
        return None, {}, f"{usage}\n  error: expected at most 10 commands.", True
    return commands, kwargs, None, True


def parse_interactive_run_focused_tests_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int | bool], str | None, bool]:
    usage = (
        "Usage: /run-focused-tests [--max-paths N] [--max-candidates N] [--max-commands N] "
        "[--timeout-ms N] [--max-chars N] "
        "[--continue-on-failure] [--output-contexts] [--output-diagnostics] "
        "[--context-lines N] [--max-diagnostics N] [--max-contexts N] "
        "[--max-bytes N] -- [path...]"
    )
    if not argument:
        return None, {}, None, False
    value_options: dict[str, tuple[str, str]] = {
        "--timeout-ms": ("timeout_ms", "timeout"),
        "--max-chars": ("max_output_chars", "positive"),
        "--max-paths": ("max_paths", "positive"),
        "--max-candidates": ("max_candidates", "positive"),
        "--max-commands": ("max_commands", "positive"),
        "--context-lines": ("context_lines", "nonnegative"),
        "--max-diagnostics": ("max_diagnostics", "positive"),
        "--max-contexts": ("max_contexts", "positive"),
        "--max-bytes": ("max_bytes_per_context", "positive"),
    }
    bool_options = {
        "--output-contexts": ("extract_output_contexts", True),
        "--output-diagnostics": ("extract_output_diagnostics", True),
        "--continue-on-failure": ("stop_on_failure", False),
        "--stop-on-failure": ("stop_on_failure", True),
    }
    recognized_flags = set(value_options) | set(bool_options)
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in recognized_flags):
            return None, {}, f"{usage}\n  error: {error}", True
        return argument, {}, None, False

    uses_named_options = False
    for part in parts:
        if part == "--":
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in recognized_flags:
            uses_named_options = True
            break
        break
    if not uses_named_options:
        return argument, {}, None, False

    kwargs: dict[str, int | bool] = {}
    path_parts: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            path_parts.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in bool_options:
            if "=" in part:
                return None, {}, f"{usage}\n  error: {flag} does not take a value.", True
            keyword, value = bool_options[flag]
            kwargs[keyword] = value
            index += 1
            continue
        if flag in value_options:
            keyword, value_type = value_options[flag]
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            if value_type == "timeout":
                value, error = parse_interactive_timeout_option(flag, raw_value)
            elif value_type == "nonnegative":
                value, error = parse_interactive_nonnegative_option(flag, raw_value)
            else:
                value, error = parse_interactive_positive_option(flag, raw_value)
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            kwargs[keyword] = int(value)
            continue
        path_parts.extend(parts[index:])
        break

    focused_argument = shlex.join(path_parts).strip() or None
    return focused_argument, kwargs, None, True


def parse_interactive_run_suggested_checks_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int | bool], str | None, bool]:
    usage = (
        "Usage: /run-suggested-checks [--max-checks N] [--timeout-ms N] [--max-chars N] "
        "[--continue-on-failure] [--output-contexts] [--output-diagnostics] "
        "[--context-lines N] [--max-diagnostics N] [--max-contexts N] "
        "[--max-bytes N] -- [max]"
    )
    if not argument:
        return None, {}, None, False
    value_options: dict[str, tuple[str, str]] = {
        "--max-checks": ("max_checks", "positive"),
        "--timeout-ms": ("timeout_ms", "timeout"),
        "--max-chars": ("max_output_chars", "positive"),
        "--context-lines": ("context_lines", "nonnegative"),
        "--max-diagnostics": ("max_diagnostics", "positive"),
        "--max-contexts": ("max_contexts", "positive"),
        "--max-bytes": ("max_bytes_per_context", "positive"),
    }
    bool_options = {
        "--output-contexts": ("extract_output_contexts", True),
        "--output-diagnostics": ("extract_output_diagnostics", True),
        "--continue-on-failure": ("stop_on_failure", False),
        "--stop-on-failure": ("stop_on_failure", True),
    }
    recognized_flags = set(value_options) | set(bool_options)
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in recognized_flags):
            return None, {}, f"{usage}\n  error: {error}", True
        return argument, {}, None, False

    uses_named_options = False
    for part in parts:
        if part == "--":
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in recognized_flags:
            uses_named_options = True
            break
        break
    if not uses_named_options:
        return argument, {}, None, False

    kwargs: dict[str, int | bool] = {}
    max_parts: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            max_parts.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in bool_options:
            if "=" in part:
                return None, {}, f"{usage}\n  error: {flag} does not take a value.", True
            keyword, value = bool_options[flag]
            kwargs[keyword] = value
            index += 1
            continue
        if flag in value_options:
            keyword, value_type = value_options[flag]
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            if value_type == "timeout":
                value, error = parse_interactive_timeout_option(flag, raw_value)
            elif value_type == "nonnegative":
                value, error = parse_interactive_nonnegative_option(flag, raw_value)
            else:
                value, error = parse_interactive_positive_option(flag, raw_value)
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            kwargs[keyword] = int(value)
            continue
        max_parts.extend(parts[index:])
        break

    selected_max = shlex.join(max_parts).strip() or None
    if selected_max and len(max_parts) != 1:
        return None, {}, f"{usage}\n  error: expected at most one max value.", True
    if selected_max and "max_checks" in kwargs:
        return None, {}, f"{usage}\n  error: provide either --max-checks or trailing max, not both.", True
    return selected_max, kwargs, None, True


def parse_interactive_cwd_command_argument(
    argument: str | None,
    usage: str,
) -> tuple[str | None, str | None, str | None, bool]:
    if not argument:
        return None, None, None, False
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if "--cwd" in argument:
            return None, None, f"{usage}\n  error: {error}", True
        return argument, None, None, False

    uses_named_options = False
    for part in parts:
        if part == "--":
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag == "--cwd":
            uses_named_options = True
            break
        break
    if not uses_named_options:
        return argument, None, None, False

    cwd: str | None = None
    command_parts: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            command_parts.extend(parts[index + 1 :])
            break
        if part == "--cwd" or part.startswith("--cwd="):
            if cwd is not None:
                return None, None, f"{usage}\n  error: --cwd can only be provided once.", True
            if part.startswith("--cwd="):
                cwd = part.split("=", 1)[1]
                index += 1
            else:
                if index + 1 >= len(parts):
                    return None, None, f"{usage}\n  error: --cwd requires a value.", True
                cwd = parts[index + 1]
                index += 2
            continue
        command_parts.extend(parts[index:])
        break

    command = shlex.join(command_parts).strip()
    if not command:
        return None, cwd, f"{usage}\n  error: command is required.", True
    return command, cwd, None, True


def parse_interactive_check_run_sequence_argument(
    argument: str | None,
) -> tuple[list[str] | None, str | None, str | None, bool]:
    usage = "Usage: /check-run-seq [--cwd PATH] -- <cmd> ;; <cmd>"
    if not argument:
        return None, None, None, False
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if "--cwd" in argument:
            return None, None, f"{usage}\n  error: {error}", True
        return None, None, None, False

    uses_named_options = False
    for part in parts:
        if part == "--":
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag == "--cwd":
            uses_named_options = True
            break
        break
    if not uses_named_options:
        return None, None, None, False

    cwd: str | None = None
    command_parts: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            command_parts.extend(parts[index + 1 :])
            break
        if part == "--cwd" or part.startswith("--cwd="):
            if cwd is not None:
                return None, None, f"{usage}\n  error: --cwd can only be provided once.", True
            if part.startswith("--cwd="):
                cwd = part.split("=", 1)[1]
                index += 1
            else:
                if index + 1 >= len(parts):
                    return None, None, f"{usage}\n  error: --cwd requires a value.", True
                cwd = parts[index + 1]
                index += 2
            continue
        command_parts.extend(parts[index:])
        break

    commands: list[str] = []
    current: list[str] = []
    for part in command_parts:
        if part == ";;":
            command = shlex.join(current).strip()
            if command:
                commands.append(command)
            current = []
            continue
        current.append(part)
    command = shlex.join(current).strip()
    if command:
        commands.append(command)
    if not commands:
        return None, cwd, f"{usage}\n  error: at least one command is required.", True
    if len(commands) > 10:
        return None, cwd, f"{usage}\n  error: expected at most 10 commands.", True
    return commands, cwd, None, True


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


def print_agent_result(result: AgentResult) -> None:
    if result.message:
        print(f"\n{result.message}")
    elif not result.success:
        print("\nStopped")
    if result.completion_blockers:
        print("Completion blockers:")
        for blocker in result.completion_blockers:
            print(f"- {blocker}")
    if result.completion_warnings:
        print("Warnings:")
        for warning in result.completion_warnings:
            print(f"- {warning}")
    if result.verification_checks:
        print("Verified:")
        for check in result.verification_checks:
            print(f"- {check}")
    if result.pending_verification_checks:
        print("Pending checks:")
        for check in result.pending_verification_checks:
            print(f"- {check}")
    if result.failed_verification_checks:
        print("Failed checks:")
        for check in result.failed_verification_checks:
            print(f"- {check}")


def prompt_approval(request: ApprovalRequest) -> ApprovalDecision:
    print(f"Action: {request.action_type}")
    print(f"Target: {request.target}")
    print(f"Risk: {request.risk}")
    if request.preview:
        print(f"Preview: {request.preview}")
    try:
        answer = input("Approve? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return ApprovalDecision(approved=False, message="Approval prompt interrupted.")

    if answer in {"y", "yes"}:
        return ApprovalDecision(approved=True, message="Approved by user.")
    return ApprovalDecision(approved=False, message="Denied by user.")


def handle_approval_command(argument: str | None, current: ApprovalPolicy) -> tuple[ApprovalPolicy, str]:
    if not argument:
        return current, f"Approval policy: {current}"
    requested = argument.strip().lower()
    if requested not in {"ask", "allow", "deny"}:
        return current, "Usage: /approval [ask|allow|deny]"
    policy = requested
    return policy, f"Approval policy: {policy}"


def build_approval_handler(policy: ApprovalPolicy) -> ApprovalHandler:
    if policy == "allow":
        return lambda request: ApprovalDecision(approved=True, message=f"Approved by policy for {request.action_type}.")
    if policy == "deny":
        return lambda request: ApprovalDecision(approved=False, message=f"Denied by policy for {request.action_type}.")
    return prompt_approval


def format_error(error: Exception) -> str:
    # Expand 401 guidance; otherwise return raw error text.
    if getattr(error, "status", None) == 401:
        return "\n".join(
            [
                str(error),
                "The configured model provider rejected the API key.",
                "Check /model for the active provider and key source.",
                "If you copied a value that starts with 'Bearer ', VibeAgent strips that prefix automatically.",
            ]
        )
    return str(error)


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
