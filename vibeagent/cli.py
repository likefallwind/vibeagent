from __future__ import annotations

import argparse
from collections.abc import Sequence
import os
from pathlib import Path

from .agent import run_agent
from .btw import run_btw
from .chat import run_chat
from .session_recap import run_session_recap
from .cli_args import has_local_flag, parse_args
from .cli_config import resolve_project_root
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
from .cli_local_flag_runner import run_local_flag as _run_local_flag
from .cli_local_result import emit_local_result
from .cli_output import (
    build_approval_handler,
    format_error,
    handle_approval_command,
    print_agent_result,
    print_error_result,
    print_interrupted_result,
    prompt_approval,
)
from .cli_checkpoint_local_flags import run_checkpoint_local_flag
from .cli_background_agent_local_flags import run_background_agent_local_flag
from .cli_background_agent_attach import attach_background_agent_from_cli
from .cli_background_agent_launch import launch_background_agent_from_cli
from .cli_background_agent_followup import (
    prepare_background_agent_followup,
    record_background_agent_session_root,
)
from .cli_code_intel_local_flags import run_code_intel_local_flag, run_python_local_flag
from .cli_command_local_flags import run_command_local_flag
from .cli_edit_local_flags import run_edit_local_flag
from .cli_git_local_flags import run_git_local_flag
from .cli_json_local_flags import run_json_local_flag
from .cli_patch_local_flags import run_patch_local_flag
from .cli_session_local_flags import run_session_local_flag
from .cli_startup_context import InteractiveStartupContext, resolve_interactive_startup_context
from .cli_interactive import run_interactive_loop as _run_interactive_loop
from .cli_main_args import normalize_task_bound_diff_args
from .cli_runner import (
    build_one_shot_kwargs_from_args,
    run_one_shot as _run_one_shot,
)
from .cli_review_local_flags import run_review_local_flag
from .cli_read_local_flags import run_read_local_flag
from .cli_project_local_flags import run_project_local_flag
from .cli_session_kwargs import (
    session_audit_kwargs,
    session_commands_kwargs,
    session_failures_kwargs,
    session_files_kwargs,
    session_handoff_kwargs,
    session_output_contexts_kwargs,
    session_output_diagnostics_kwargs,
    run_session_verification_kwargs,
    session_search_kwargs,
    session_transcript_kwargs,
    session_verification_kwargs,
)
from .cli_runtime_local_flags import run_runtime_local_flag
from .cli_text_edit_local_flags import run_text_edit_local_flag
from .cli_validation import validate_cli_args
from .cli_worktree import create_cli_worktree
from .cli_parse_core import build_focused_tests_kwargs
from .cli_parse_diff_git import (
    build_stash_argument,
    build_switch_argument,
    parse_interactive_diff_argument,
    parse_interactive_diff_contexts_argument,
    parse_interactive_diff_hunks_argument,
)
from .cli_parse_session import (
    parse_interactive_session_detail_argument,
    parse_interactive_run_session_verification_argument,
    parse_interactive_session_search_argument,
    parse_interactive_transcript_argument,
)
from .cli_parse_runtime_checks import (
    parse_interactive_http_argument,
    parse_interactive_http_fetch_argument,
    parse_interactive_port_argument,
    parse_interactive_process_output_argument,
)
from .cli_parse_discovery import (
    parse_interactive_commands_argument,
    parse_interactive_find_files_argument,
    parse_interactive_glob_argument,
    parse_interactive_instructions_argument,
    parse_interactive_manifests_argument,
    parse_interactive_option_limit_argument,
    parse_interactive_overview_argument,
    parse_interactive_repo_map_argument,
    parse_interactive_search_argument,
    parse_interactive_todos_argument,
)
from .cli_parse_read import (
    parse_interactive_around_argument,
    parse_interactive_around_many_argument,
    parse_interactive_max_bytes_argument,
    parse_interactive_output_analysis_argument,
    parse_interactive_read_argument,
    parse_interactive_read_files_argument,
    parse_interactive_read_ranges_argument,
    parse_interactive_symbols_argument,
    parse_interactive_tail_argument,
    parse_interactive_tree_argument,
)
from .cli_parse_code_intel import (
    parse_interactive_python_call_graph_argument,
    parse_interactive_python_deps_argument,
    parse_interactive_python_symbol_argument,
    parse_interactive_test_paths_argument,
)
from .cli_parse_cwd_command import (
    parse_interactive_check_run_sequence_argument,
    parse_interactive_cwd_command_argument,
)
from .cli_parse_process_run import parse_interactive_wait_process_argument, parse_interactive_write_process_argument
from .cli_parse_run import (
    parse_interactive_run_argument,
    parse_interactive_run_focused_tests_argument,
    parse_interactive_run_sequence_argument,
    parse_interactive_run_suggested_checks_argument,
)
from .cli_command_namespace import *  # re-export command helpers for local flag dispatch and tests
from .cli_input_format import TaskInputFormatError
from .providers import create_chat_client
from .session_lifecycle_hooks import format_init_only_setup_report, run_init_only_setup
from .worktree_hooks import WorktreeHookContext
from .workspace_hooks import read_project_hooks
from .workspace_permissions import ProjectPermissions
from .workspace_core import RunWorkspace
from .model_effort import resolve_model_effort_setting


def main(argv: Sequence[str] | None = None) -> int:
    if argv is not None:
        args = parse_args(argv)
        try:
            prepare_background_agent_followup(args)
        except (OSError, ValueError) as error:
            return print_error_result(
                format_error(error),
                args.json,
                exit_code=2,
                output_format=args.output_format,
            )
        validation_error = validate_cli_args(args)
        if validation_error is not None:
            return print_error_result(validation_error, args.json, exit_code=2, output_format=args.output_format)
        normalize_task_bound_diff_args(args)
        if args.background:
            try:
                return launch_background_agent_from_cli(list(argv), args)
            except (OSError, ValueError) as error:
                return print_error_result(
                    format_error(error),
                    args.json,
                    exit_code=2,
                    output_format=args.output_format,
                )
        if args.attach_background_agent is not None:
            try:
                return attach_background_agent_from_cli(
                    args,
                    run_interactive_func=run_interactive_with_args,
                )
            except KeyboardInterrupt:
                return print_interrupted_result(args.json, args.output_format)
            except (OSError, ValueError) as error:
                return print_error_result(
                    format_error(error),
                    args.json,
                    exit_code=2,
                    output_format=args.output_format,
                )
        if args.worktree is not None:
            try:
                source_root = resolve_project_root(args.cwd) or Path.cwd()
                startup_workspace = RunWorkspace(
                    root=source_root,
                    run_id="cli-worktree",
                    session_dir=source_root / ".vibeagent" / "sessions" / "cli-worktree",
                )
                startup_policy = args.approval or "ask"
                worktree = create_cli_worktree(
                    source_root,
                    args.worktree or None,
                    hook_context=WorktreeHookContext(
                        read_project_hooks(startup_workspace),
                        ProjectPermissions(),
                        startup_policy,
                        build_approval_handler(startup_policy),
                        30_000,
                    ),
                )
            except ValueError as error:
                return print_error_result(str(error), args.json, exit_code=2, output_format=args.output_format)
            args.cwd = str(worktree.root)
        if getattr(args, "_background_agent_worker_token", None) is not None:
            try:
                record_background_agent_session_root(
                    args,
                    resolve_project_root(args.cwd) or Path.cwd(),
                )
            except (OSError, ValueError) as error:
                return print_error_result(
                    format_error(error),
                    args.json,
                    exit_code=2,
                    output_format=args.output_format,
                )
        if has_local_flag(args):
            if args.task:
                return print_error_result(
                    "Local command flags cannot be combined with a task.",
                    args.json,
                    exit_code=2,
                    output_format=args.output_format,
                )
            return run_local_flag(args)
        if args.task:
            try:
                kwargs = build_one_shot_kwargs_from_args(args)
            except (TaskInputFormatError, ValueError) as error:
                return print_error_result(str(error), args.json, exit_code=2, output_format=args.output_format)
            return run_one_shot(**kwargs)
    if argv is not None:
        try:
            return run_interactive_with_args(args)
        except KeyboardInterrupt:
            return print_interrupted_result(args.json, args.output_format)
        except ValueError as error:
            return print_error_result(str(error), args.json, exit_code=2, output_format=args.output_format)
    return run_interactive()


def console_main() -> int:
    import sys

    return main(sys.argv[1:])


def run_local_flag(args: argparse.Namespace) -> int:
    return _run_local_flag(args, globals())


def run_interactive(base_dir: str | None = None, startup_context: InteractiveStartupContext | None = None) -> int:
    project_root = resolve_project_root(base_dir)
    if startup_context is None:
        effort = resolve_model_effort_setting(None, os.environ)
        context = InteractiveStartupContext(effort=effort.level, effort_locked=effort.locked)
    else:
        context = startup_context
    if project_root is None:
        return run_interactive_loop(context)

    previous_cwd = Path.cwd()
    os.chdir(project_root)
    try:
        return run_interactive_loop(context)
    finally:
        os.chdir(previous_cwd)


def run_interactive_with_args(args: argparse.Namespace) -> int:
    project_root = resolve_project_root(args.cwd) or Path.cwd()
    startup_context = resolve_interactive_startup_context(
        args,
        project_root,
        get_resume_context_func=get_resume_context,
        get_compact_context_func=get_compact_context,
    )
    if startup_context.error is not None:
        return print_error_result(startup_context.error, args.json, exit_code=2, output_format=args.output_format)
    return run_interactive(args.cwd, startup_context)


def run_one_shot(*args, **kwargs) -> int:
    kwargs.setdefault("create_chat_client_func", create_chat_client)
    kwargs.setdefault("run_chat_func", run_chat)
    kwargs.setdefault("run_agent_func", run_agent)
    kwargs.setdefault("get_resume_context_func", get_resume_context)
    kwargs.setdefault("get_compact_context_func", get_compact_context)
    return _run_one_shot(*args, **kwargs)


def run_interactive_loop(startup_context: InteractiveStartupContext | None = None) -> int:
    context = startup_context or InteractiveStartupContext()
    return _run_interactive_loop(
        command_namespace=globals(),
        create_chat_client_func=create_chat_client,
        run_chat_func=run_chat,
        run_btw_func=run_btw,
        run_recap_func=run_session_recap,
        run_agent_func=run_agent,
        get_resume_context_func=get_resume_context,
        initial_resume_run_id=context.run_id,
        initial_resume_context=context.context,
        initial_resume_message=context.message,
        initial_agent=context.agent,
        initial_dynamic_agent_profiles=context.dynamic_agent_profiles,
        initial_effort=context.effort,
        initial_effort_locked=context.effort_locked,
        initial_autocompact_tokens=context.autocompact_tokens,
        initial_system_prompt=context.system_prompt,
        initial_append_system_prompt=context.append_system_prompt,
        initial_additional_directories=context.additional_directories,
        initial_pending_workspace=context.pending_workspace,
        initial_branch_source_run_id=context.branch_source_run_id,
        initial_conversation_messages=context.conversation,
    )
if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
