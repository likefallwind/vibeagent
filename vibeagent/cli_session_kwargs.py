from __future__ import annotations

import argparse
from typing import Any


def _present_kwargs(*items: tuple[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in items if value is not None}


def session_transcript_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    return _present_kwargs(
        ("max_events", args.session_transcript_event_max),
        ("max_text", args.session_max_text),
    )


def session_search_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    kwargs = _present_kwargs(
        ("max_matches", args.session_search_match_max),
        ("max_text", args.session_max_text),
    )
    if args.session_search_case_sensitive:
        kwargs["case_sensitive"] = True
    return kwargs


def session_commands_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    return _present_kwargs(
        ("max_commands", args.session_max_commands),
        ("max_output_chars", args.session_max_output_chars),
    )


def session_output_contexts_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "max_commands": args.session_output_command_max,
        "max_output_chars": args.session_output_max_chars,
        "context_lines": args.session_output_context_lines,
        "max_contexts": args.session_output_context_max,
        "max_bytes_per_context": args.session_output_context_max_bytes,
    }


def session_output_diagnostics_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    kwargs = session_output_contexts_kwargs(args)
    kwargs["max_diagnostics"] = args.session_output_diagnostic_max
    return kwargs


def session_files_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    return _present_kwargs(("max_files", args.session_max_files))


def session_failures_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    return _present_kwargs(
        ("max_failures", args.session_max_failures),
        ("max_text", args.session_max_text),
    )


def session_verification_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    return _present_kwargs(("max_checks", args.session_max_checks))


def run_session_verification_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    kwargs = _present_kwargs(
        ("max_checks", args.session_max_checks),
        ("timeout_ms", args.run_timeout_ms),
        ("max_output_chars", args.run_max_chars),
    )
    if args.run_session_no_failed:
        kwargs["include_failed"] = False
    if args.run_session_no_pending:
        kwargs["include_pending"] = False
    if args.run_continue_on_failure:
        kwargs["stop_on_failure"] = False
    return kwargs


def session_audit_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    return _present_kwargs(
        ("max_failures", args.session_max_failures),
        ("max_files", args.session_max_files),
        ("max_commands", args.session_max_commands),
        ("max_checks", args.session_max_checks),
        ("max_text", args.session_max_text),
    )


def session_handoff_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    return _present_kwargs(
        ("max_failures", args.session_max_failures),
        ("max_files", args.session_max_files),
        ("max_commands", args.session_max_commands),
        ("max_checks", args.session_max_checks),
        ("max_output_chars", args.session_max_output_chars),
        ("max_text", args.session_max_text),
    )
