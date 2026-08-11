from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .cli_local_result import local_text_or_report


def run_review_local_flag(
    args: argparse.Namespace,
    project_root: Path | None,
    provider_env: dict[str, str],
    commands: dict[str, Any],
) -> tuple[str, dict[str, object]] | None:
    root = project_root or "."
    if args.status:
        return local_text_or_report(
            args,
            "runtimeStatus",
            lambda: commands["get_status_report"]("code", args.approval, None, chat_turns=0),
            commands["format_status_report_text"],
            lambda: commands["get_status_text"]("code", args.approval, None, chat_turns=0),
        )
    if args.context:
        return local_text_or_report(
            args,
            "context",
            lambda: commands["get_context_report"](root),
            commands["format_context_report_text"],
            lambda: commands["get_context_text"](root),
        )
    if args.init_only:
        report = commands["run_init_only_setup"](
            root,
            approval_policy=args.approval,
            approval_handler=commands["build_approval_handler"](args.approval),
            command_timeout_ms=args.command_timeout_ms or 30_000,
        )
        return commands["format_init_only_setup_report"](report), {"setup": report}
    if args.init is not None:
        file_name = args.init or "AGENTS.md"
        return local_text_or_report(
            args,
            "init",
            lambda: commands["get_init_report"](root, file_name),
            commands["format_init_report_text"],
            lambda: commands["init_project_instructions"](root, file_name),
        )
    if args.doctor:
        return local_text_or_report(
            args,
            "doctor",
            lambda: commands["get_doctor_report"](root, provider_env),
            commands["format_doctor_report_text"],
            lambda: commands["get_doctor_text"](root, provider_env),
        )
    if args.review:
        review_report = commands["get_review_report"](
            root,
            max_files=args.review_max_files,
            max_checks=args.review_max_checks,
        )
        return commands["format_review_report_text"](review_report), {"review": review_report}
    if args.handoff:
        handoff_report = commands["get_handoff_report"](
            root,
            max_files=args.handoff_max_files,
            max_checks=args.handoff_max_checks,
            max_status_chars=args.handoff_max_status_chars,
            max_plan_chars=args.handoff_max_plan_chars,
        )
        return commands["format_handoff_report_text"](handoff_report), {"handoff": handoff_report}
    if args.changes:
        changes_report = commands["get_changes_report"](root, max_files=args.changes_max_files)
        return commands["format_changes_report_text"](changes_report), {"changes": changes_report}
    if args.diff is not None:
        return local_text_or_report(
            args,
            "diff",
            lambda: commands["get_diff_report"](root, args.diff or None, max_chars=args.diff_max_chars),
            commands["format_diff_report_text"],
            lambda: commands["get_diff_text"](root, args.diff or None, max_chars=args.diff_max_chars),
        )
    if args.diff_hunks is not None:
        diff_kwargs = {
            "max_hunks": args.diff_hunks_max_hunks,
            "max_lines_per_hunk": args.diff_hunks_max_lines,
        }
        return local_text_or_report(
            args,
            "diffHunks",
            lambda: commands["get_diff_hunks_report"](root, args.diff_hunks or None, **diff_kwargs),
            commands["format_diff_hunks_report_text"],
            lambda: commands["get_diff_hunks_text"](root, args.diff_hunks or None, **diff_kwargs),
        )
    if args.diff_contexts is not None:
        diff_kwargs = {
            "context_lines": args.diff_context_lines,
            "max_hunks": args.diff_contexts_max_hunks,
            "max_bytes_per_context": args.diff_contexts_max_bytes,
        }
        return local_text_or_report(
            args,
            "diffContexts",
            lambda: commands["get_diff_contexts_report"](root, args.diff_contexts or None, **diff_kwargs),
            commands["format_diff_contexts_report_text"],
            lambda: commands["get_diff_contexts_text"](root, args.diff_contexts or None, **diff_kwargs),
        )
    return None


def _option_limited_text(
    command: Any,
    commands: dict[str, Any],
    usage: str,
    option_map: dict[str, str],
    getter_name: str,
) -> str:
    kwargs, error, uses_named_options = commands["parse_interactive_option_limit_argument"](
        command.argument,
        usage,
        option_map,
    )
    if error:
        return error
    if uses_named_options:
        return commands[getter_name](**kwargs)
    return commands[getter_name]()


def _diff_text(command: Any, commands: dict[str, Any]) -> str:
    diff_argument, max_chars, error = commands["parse_interactive_diff_argument"](command.argument)
    if error:
        return error
    try:
        return commands["get_diff_text"](argument=diff_argument, max_chars=max_chars)
    except ValueError as error:
        return f"Usage: /diff [--staged|--cached] [--max-chars N] [path]\n  error: {error}"


def run_interactive_review_command(command: Any, commands: dict[str, Any]) -> str | None:
    if command.type == "review":
        return _option_limited_text(
            command,
            commands,
            "Usage: /review [--max-files N] [--max-checks N]",
            {"--max-files": "max_files", "--max-checks": "max_checks"},
            "get_review_text",
        )
    if command.type == "handoff":
        return _option_limited_text(
            command,
            commands,
            "Usage: /handoff [--max-files N] [--max-checks N] [--max-status-chars N] [--max-plan-chars N]",
            {
                "--max-files": "max_files",
                "--max-checks": "max_checks",
                "--max-status-chars": "max_status_chars",
                "--max-plan-chars": "max_plan_chars",
            },
            "get_handoff_text",
        )
    if command.type == "changes":
        return _option_limited_text(
            command,
            commands,
            "Usage: /changes [--max-files N]",
            {"--max-files": "max_files"},
            "get_changes_text",
        )
    if command.type == "diff":
        return _diff_text(command, commands)
    if command.type == "diff_hunks":
        diff_argument, kwargs, error = commands["parse_interactive_diff_hunks_argument"](command.argument)
        return error if error else commands["get_diff_hunks_text"](argument=diff_argument, **kwargs)
    if command.type == "diff_contexts":
        diff_argument, kwargs, error = commands["parse_interactive_diff_contexts_argument"](command.argument)
        return error if error else commands["get_diff_contexts_text"](argument=diff_argument, **kwargs)
    return None
