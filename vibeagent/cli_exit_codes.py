from __future__ import annotations

import argparse

from .cli_exit_predicates import (
    INCOMPLETE_COUNT_FAILURES,
    has_bad_session_summary_status,
    has_incomplete_count_failure,
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


LOCAL_RESULT_ARG_NAMES = frozenset(
    {
        "model",
        "version",
        "tool",
        "tool_search",
        "config",
        "tools",
        "permissions",
        "sandbox_status",
        "trust_status",
        "trust_project",
        "untrust_project",
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
        "hooks",
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
        "find_files",
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
        "background_agents",
        "background_agent_log",
        "stop_background_agent",
        "send_background_agent",
        "respawn_background_agent",
        "remove_background_agent",
        "status",
        "context",
        "init",
        "init_only",
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
        "run_session_verification",
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
        "session_rewind_points",
        "check_session_rewind",
        "session_rewind",
        "usage",
        "cost",
        "save_config",
    }
)


def local_result_exit_code(args: argparse.Namespace, text: str) -> int:
    result_flag = any(local_result_arg_selected(getattr(args, name, None)) for name in LOCAL_RESULT_ARG_NAMES)
    if not result_flag:
        return 0
    if text.startswith("Usage:") and not args.usage:
        return 2
    if text == "No sessions found.":
        return 1
    if text.startswith("Session not found:") or text.startswith("Invalid session id:"):
        return 1
    if text.startswith("Tool not found:"):
        return 1
    if text.startswith("Background agent not found:"):
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
    if has_incomplete_count_failure(args, text):
        return 1
    if args.session_verification is not None and has_session_verification_issue(text):
        return 1
    if args.diff is not None and has_top_level_error(text):
        return 1
    if args.hooks and has_top_level_error(text):
        return 1
    if args.background_agent_log is not None and any(
        has_top_level_field(text, "status", status)
        for status in ("failed", "lost")
    ):
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
