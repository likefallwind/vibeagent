from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .cli_local_result import local_text_or_report


def _normalize_run_id(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip() or None


def _normalize_session_search_query(value: str) -> str:
    return value.strip()


SESSION_DETAIL_COMMAND_SPECS: dict[str, tuple[str, dict[str, tuple[str, bool]], str]] = {
    "session_commands": (
        "Usage: /session-commands [run-id] [--max-commands N] [--max-output-chars N]",
        {"--max-commands": ("max_commands", False), "--max-output-chars": ("max_output_chars", True)},
        "get_session_commands_text",
    ),
    "session_output_contexts": (
        "Usage: /session-output-contexts [run-id] [--max-commands N] "
        "[--max-output-chars N] [--context-lines N] [--max-contexts N] [--max-bytes N]",
        {
            "--max-commands": ("max_commands", False),
            "--max-output-chars": ("max_output_chars", False),
            "--context-lines": ("context_lines", True),
            "--max-contexts": ("max_contexts", False),
            "--max-bytes": ("max_bytes_per_context", False),
        },
        "get_session_output_contexts_text",
    ),
    "session_output_diagnostics": (
        "Usage: /session-output-diagnostics [run-id] [--max-commands N] "
        "[--max-output-chars N] [--context-lines N] [--max-diagnostics N] "
        "[--max-contexts N] [--max-bytes N]",
        {
            "--max-commands": ("max_commands", False),
            "--max-output-chars": ("max_output_chars", False),
            "--context-lines": ("context_lines", True),
            "--max-diagnostics": ("max_diagnostics", False),
            "--max-contexts": ("max_contexts", False),
            "--max-bytes": ("max_bytes_per_context", False),
        },
        "get_session_output_diagnostics_text",
    ),
    "session_files": (
        "Usage: /session-files [run-id] [--max-files N]",
        {"--max-files": ("max_files", False)},
        "get_session_files_text",
    ),
    "session_failures": (
        "Usage: /session-failures [run-id] [--max-failures N] [--max-text N]",
        {"--max-failures": ("max_failures", False), "--max-text": ("max_text", False)},
        "get_session_failures_text",
    ),
    "session_verification": (
        "Usage: /session-verification [run-id] [--max-checks N]",
        {"--max-checks": ("max_checks", False)},
        "get_session_verification_text",
    ),
    "session_audit": (
        "Usage: /session-audit [run-id] [--max-failures N] [--max-files N] "
        "[--max-commands N] [--max-checks N] [--max-text N]",
        {
            "--max-failures": ("max_failures", False),
            "--max-files": ("max_files", False),
            "--max-commands": ("max_commands", False),
            "--max-checks": ("max_checks", False),
            "--max-text": ("max_text", False),
        },
        "get_session_audit_text",
    ),
    "session_handoff": (
        "Usage: /session-handoff [run-id] [--max-failures N] [--max-files N] "
        "[--max-commands N] [--max-checks N] [--max-output-chars N] [--max-text N]",
        {
            "--max-failures": ("max_failures", False),
            "--max-files": ("max_files", False),
            "--max-commands": ("max_commands", False),
            "--max-checks": ("max_checks", False),
            "--max-output-chars": ("max_output_chars", True),
            "--max-text": ("max_text", False),
        },
        "get_session_handoff_text",
    ),
}


def run_session_local_flag(
    args: argparse.Namespace,
    project_root: Path | None,
    commands: dict[str, Any],
) -> tuple[str, dict[str, object]] | None:
    root = project_root or "."
    if args.sessions:
        return local_text_or_report(
            args,
            "sessions",
            lambda: commands["get_sessions_report"](root),
            commands["format_sessions_report_text"],
            lambda: commands["get_sessions_text"](root),
        )
    if args.last:
        return local_text_or_report(
            args,
            "sessionSummary",
            lambda: commands["get_last_session_report"](root),
            commands["format_session_summary_report_text"],
            lambda: commands["get_last_session_text"](root),
        )
    if args.session is not None:
        run_id = _normalize_run_id(args.session)
        return local_text_or_report(
            args,
            "sessionSummary",
            lambda: commands["get_session_report"](run_id, root),
            commands["format_session_summary_report_text"],
            lambda: commands["get_session_text"](run_id, root),
        )
    if args.plan is not None:
        run_id = _normalize_run_id(args.plan)
        return local_text_or_report(
            args,
            "sessionPlan",
            lambda: commands["get_plan_report"](root, run_id),
            commands["format_session_plan_report_text"],
            lambda: commands["get_plan_text"](root, run_id),
        )
    if args.transcript is not None:
        session_kwargs = commands["session_transcript_kwargs"](args)
        run_id = _normalize_run_id(args.transcript)
        return local_text_or_report(
            args,
            "sessionTranscript",
            lambda: commands["get_transcript_report"](root, run_id, **session_kwargs),
            commands["format_session_transcript_report_text"],
            lambda: commands["get_transcript_text"](root, run_id, **session_kwargs),
        )
    if args.session_search is not None:
        session_kwargs = commands["session_search_kwargs"](args)
        query = _normalize_session_search_query(args.session_search)
        run_id = _normalize_run_id(args.session_search_run)
        return local_text_or_report(
            args,
            "sessionSearch",
            lambda: commands["get_session_search_report"](root, query, run_id, **session_kwargs),
            commands["format_session_search_report_text"],
            lambda: commands["get_session_search_text"](root, query, run_id, **session_kwargs),
        )
    if args.session_commands is not None:
        session_kwargs = commands["session_commands_kwargs"](args)
        run_id = _normalize_run_id(args.session_commands)
        return local_text_or_report(
            args,
            "sessionCommands",
            lambda: commands["get_session_commands_report"](root, run_id, **session_kwargs),
            commands["format_session_commands_report_text"],
            lambda: commands["get_session_commands_text"](root, run_id, **session_kwargs),
        )
    if args.session_output_contexts is not None:
        session_kwargs = commands["session_output_contexts_kwargs"](args)
        run_id = _normalize_run_id(args.session_output_contexts)
        return local_text_or_report(
            args,
            "sessionOutputContexts",
            lambda: commands["get_session_output_contexts_report"](root, run_id, **session_kwargs),
            commands["format_session_output_contexts_report_text"],
            lambda: commands["get_session_output_contexts_text"](root, run_id, **session_kwargs),
        )
    if args.session_output_diagnostics is not None:
        session_kwargs = commands["session_output_diagnostics_kwargs"](args)
        run_id = _normalize_run_id(args.session_output_diagnostics)
        return local_text_or_report(
            args,
            "sessionOutputDiagnostics",
            lambda: commands["get_session_output_diagnostics_report"](root, run_id, **session_kwargs),
            commands["format_session_output_diagnostics_report_text"],
            lambda: commands["get_session_output_diagnostics_text"](root, run_id, **session_kwargs),
        )
    if args.session_files is not None:
        session_kwargs = commands["session_files_kwargs"](args)
        run_id = _normalize_run_id(args.session_files)
        return local_text_or_report(
            args,
            "sessionFiles",
            lambda: commands["get_session_files_report"](root, run_id, **session_kwargs),
            commands["format_session_files_report_text"],
            lambda: commands["get_session_files_text"](root, run_id, **session_kwargs),
        )
    if args.session_failures is not None:
        session_kwargs = commands["session_failures_kwargs"](args)
        run_id = _normalize_run_id(args.session_failures)
        return local_text_or_report(
            args,
            "sessionFailures",
            lambda: commands["get_session_failures_report"](root, run_id, **session_kwargs),
            commands["format_session_failures_report_text"],
            lambda: commands["get_session_failures_text"](root, run_id, **session_kwargs),
        )
    if args.session_verification is not None:
        session_kwargs = commands["session_verification_kwargs"](args)
        run_id = _normalize_run_id(args.session_verification)
        return local_text_or_report(
            args,
            "sessionVerification",
            lambda: commands["get_session_verification_report"](root, run_id, **session_kwargs),
            commands["format_session_verification_report_text"],
            lambda: commands["get_session_verification_text"](root, run_id, **session_kwargs),
        )
    if args.run_session_verification is not None:
        session_kwargs = commands["run_session_verification_kwargs"](args)
        run_id = _normalize_run_id(args.run_session_verification)
        return local_text_or_report(
            args,
            "runSessionVerification",
            lambda: commands["get_run_session_verification_report"](root, run_id, **session_kwargs),
            commands["format_run_session_verification_report_text"],
            lambda: commands["get_run_session_verification_text"](root, run_id, **session_kwargs),
        )
    if args.session_audit is not None:
        session_kwargs = commands["session_audit_kwargs"](args)
        run_id = _normalize_run_id(args.session_audit)
        return local_text_or_report(
            args,
            "sessionAudit",
            lambda: commands["get_session_audit_report"](root, run_id, **session_kwargs),
            commands["format_session_audit_report_text"],
            lambda: commands["get_session_audit_text"](root, run_id, **session_kwargs),
        )
    if args.session_handoff is not None:
        session_kwargs = commands["session_handoff_kwargs"](args)
        run_id = _normalize_run_id(args.session_handoff)
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
    if command.type in SESSION_DETAIL_COMMAND_SPECS:
        usage, options, getter_name = SESSION_DETAIL_COMMAND_SPECS[command.type]
        return _interactive_session_detail_text(command, commands, usage, options, getter_name)
    if command.type == "run_session_verification":
        run_id, kwargs, error = commands["parse_interactive_run_session_verification_argument"](command.argument)
        return error if error else commands["get_run_session_verification_text"](run_id=run_id, **kwargs)
    return None


def _interactive_session_detail_text(
    command: Any,
    commands: dict[str, Any],
    usage: str,
    options: dict[str, tuple[str, bool]],
    getter_name: str,
) -> str:
    run_id, kwargs, error = commands["parse_interactive_session_detail_argument"](
        command.argument,
        usage,
        options,
    )
    return error if error else commands[getter_name](run_id=run_id, **kwargs)


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
