from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .cli_local_result import local_text_or_report
from .session_input import normalize_optional_run_id


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


def run_session_detail_local_flag(
    args: argparse.Namespace,
    project_root: Path | None,
    commands: dict[str, Any],
) -> tuple[str, dict[str, object]] | None:
    root = project_root or "."
    if getattr(args, "session_commands", None) is not None:
        session_kwargs = commands["session_commands_kwargs"](args)
        run_id = normalize_optional_run_id(args.session_commands)
        return local_text_or_report(
            args,
            "sessionCommands",
            lambda: commands["get_session_commands_report"](root, run_id, **session_kwargs),
            commands["format_session_commands_report_text"],
            lambda: commands["get_session_commands_text"](root, run_id, **session_kwargs),
        )
    if getattr(args, "session_output_contexts", None) is not None:
        session_kwargs = commands["session_output_contexts_kwargs"](args)
        run_id = normalize_optional_run_id(args.session_output_contexts)
        return local_text_or_report(
            args,
            "sessionOutputContexts",
            lambda: commands["get_session_output_contexts_report"](root, run_id, **session_kwargs),
            commands["format_session_output_contexts_report_text"],
            lambda: commands["get_session_output_contexts_text"](root, run_id, **session_kwargs),
        )
    if getattr(args, "session_output_diagnostics", None) is not None:
        session_kwargs = commands["session_output_diagnostics_kwargs"](args)
        run_id = normalize_optional_run_id(args.session_output_diagnostics)
        return local_text_or_report(
            args,
            "sessionOutputDiagnostics",
            lambda: commands["get_session_output_diagnostics_report"](root, run_id, **session_kwargs),
            commands["format_session_output_diagnostics_report_text"],
            lambda: commands["get_session_output_diagnostics_text"](root, run_id, **session_kwargs),
        )
    if getattr(args, "session_files", None) is not None:
        session_kwargs = commands["session_files_kwargs"](args)
        run_id = normalize_optional_run_id(args.session_files)
        return local_text_or_report(
            args,
            "sessionFiles",
            lambda: commands["get_session_files_report"](root, run_id, **session_kwargs),
            commands["format_session_files_report_text"],
            lambda: commands["get_session_files_text"](root, run_id, **session_kwargs),
        )
    if getattr(args, "session_failures", None) is not None:
        session_kwargs = commands["session_failures_kwargs"](args)
        run_id = normalize_optional_run_id(args.session_failures)
        return local_text_or_report(
            args,
            "sessionFailures",
            lambda: commands["get_session_failures_report"](root, run_id, **session_kwargs),
            commands["format_session_failures_report_text"],
            lambda: commands["get_session_failures_text"](root, run_id, **session_kwargs),
        )
    if getattr(args, "session_verification", None) is not None:
        session_kwargs = commands["session_verification_kwargs"](args)
        run_id = normalize_optional_run_id(args.session_verification)
        return local_text_or_report(
            args,
            "sessionVerification",
            lambda: commands["get_session_verification_report"](root, run_id, **session_kwargs),
            commands["format_session_verification_report_text"],
            lambda: commands["get_session_verification_text"](root, run_id, **session_kwargs),
        )
    if getattr(args, "run_session_verification", None) is not None:
        session_kwargs = commands["run_session_verification_kwargs"](args)
        run_id = normalize_optional_run_id(args.run_session_verification)
        return local_text_or_report(
            args,
            "runSessionVerification",
            lambda: commands["get_run_session_verification_report"](root, run_id, **session_kwargs),
            commands["format_run_session_verification_report_text"],
            lambda: commands["get_run_session_verification_text"](root, run_id, **session_kwargs),
        )
    return None


def run_interactive_session_detail_command(command: Any, commands: dict[str, Any]) -> str | None:
    if command.type not in SESSION_DETAIL_COMMAND_SPECS:
        return None
    usage, options, getter_name = SESSION_DETAIL_COMMAND_SPECS[command.type]
    return interactive_session_detail_text(command, commands, usage, options, getter_name)


def interactive_session_detail_text(
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
