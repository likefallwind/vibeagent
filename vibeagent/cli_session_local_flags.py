from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .cli_session_detail_local_flags import (
    SESSION_DETAIL_COMMAND_SPECS,
    interactive_session_detail_text as _interactive_session_detail_text,
    run_interactive_session_detail_command,
    run_session_detail_local_flag,
)
from .cli_session_summary_local_flags import (
    normalize_session_search_query as _normalize_session_search_query,
    run_session_summary_local_flag,
)
from .cli_local_result import local_text_or_report
from .session_input import normalize_optional_run_id


def run_session_local_flag(
    args: argparse.Namespace,
    project_root: Path | None,
    commands: dict[str, Any],
) -> tuple[str, dict[str, object]] | None:
    root = project_root or "."
    summary_result = run_session_summary_local_flag(args, project_root, commands)
    if summary_result is not None:
        return summary_result
    detail_result = run_session_detail_local_flag(args, project_root, commands)
    if detail_result is not None:
        return detail_result
    if args.session_audit is not None:
        session_kwargs = commands["session_audit_kwargs"](args)
        run_id = normalize_optional_run_id(args.session_audit)
        return local_text_or_report(
            args,
            "sessionAudit",
            lambda: commands["get_session_audit_report"](root, run_id, **session_kwargs),
            commands["format_session_audit_report_text"],
            lambda: commands["get_session_audit_text"](root, run_id, **session_kwargs),
        )
    if args.session_handoff is not None:
        session_kwargs = commands["session_handoff_kwargs"](args)
        run_id = normalize_optional_run_id(args.session_handoff)
        return local_text_or_report(
            args,
            "sessionHandoff",
            lambda: commands["get_session_handoff_report"](root, run_id, **session_kwargs),
            commands["format_session_handoff_report_text"],
            lambda: commands["get_session_handoff_text"](root, run_id, **session_kwargs),
        )
    if args.usage:
        return local_text_or_report(
            args,
            "usage",
            lambda: commands["get_usage_report"](root),
            commands["format_usage_report_text"],
            lambda: commands["get_usage_text"](root),
        )
    if args.cost:
        return local_text_or_report(
            args,
            "cost",
            lambda: commands["get_cost_report"](root),
            commands["format_cost_report_text"],
            lambda: commands["get_cost_text"](root),
        )
    return None


def run_interactive_session_command(command: Any, commands: dict[str, Any]) -> str | None:
    if command.type == "usage":
        return commands["get_usage_text"]()
    if command.type == "cost":
        return commands["get_cost_text"]()
    if command.type == "sessions":
        return commands["get_sessions_text"]()
    if command.type == "session":
        return commands["get_session_text"](command.argument)
    if command.type == "last":
        return commands["get_last_session_text"]()
    if command.type == "plan":
        return commands["get_plan_text"](run_id=command.argument)
    if command.type == "transcript":
        run_id, kwargs, error = commands["parse_interactive_transcript_argument"](command.argument)
        return error if error else commands["get_transcript_text"](run_id=run_id, **kwargs)
    if command.type == "session_search":
        query, run_id, kwargs, error = commands["parse_interactive_session_search_argument"](command.argument)
        return error if error else commands["get_session_search_text"](argument=query, run_id=run_id, **kwargs)
    detail_text = run_interactive_session_detail_command(command, commands)
    if detail_text is not None:
        return detail_text
    if command.type == "run_session_verification":
        run_id, kwargs, error = commands["parse_interactive_run_session_verification_argument"](command.argument)
        return error if error else commands["get_run_session_verification_text"](run_id=run_id, **kwargs)
    return None


def run_interactive_resume_command(
    command: Any,
    commands: dict[str, Any],
) -> tuple[str | None, str | None, str] | None:
    if command.type not in {"resume", "compact"}:
        return None
    usage = (
        f"Usage: /{command.type} [run-id{'|off' if command.type == 'resume' else ''}] "
        "[--max-failures N] [--max-files N] [--max-commands N] [--max-checks N] "
        "[--max-output-chars N] [--max-text N]"
    )
    run_id, kwargs, error = commands["parse_interactive_session_detail_argument"](
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
        return None, None, error
    getter_name = "get_resume_context" if command.type == "resume" else "get_compact_context"
    return commands[getter_name](run_id, **kwargs)
