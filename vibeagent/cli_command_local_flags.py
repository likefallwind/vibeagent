from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .cli_local_result import local_text_or_report


def run_command_local_flag(
    args: argparse.Namespace,
    project_root: Path | None,
    commands: dict[str, Any],
) -> tuple[str, dict[str, object]] | None:
    root = project_root or "."
    if args.command_check is not None:
        return local_text_or_report(
            args,
            "commandCheck",
            lambda: commands["get_command_check_report"](root, args.command_check, args.command_cwd),
            commands["format_command_check_report_text"],
            lambda: commands["get_command_check_text"](root, args.command_check, args.command_cwd),
        )
    if args.run_command is not None:
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
        return local_text_or_report(
            args,
            "run",
            lambda: commands["get_run_report"](root, **run_kwargs),
            commands["format_run_report_text"],
            lambda: commands["get_run_text"](root, **run_kwargs),
        )
    if args.check_run_commands is not None:
        check_run_kwargs = {"commands": args.check_run_commands, "cwd": args.run_cwd}
        return local_text_or_report(
            args,
            "checkRunCommands",
            lambda: commands["get_check_run_sequence_report"](root, **check_run_kwargs),
            commands["format_check_run_sequence_report_text"],
            lambda: commands["get_check_run_sequence_text"](root, **check_run_kwargs),
        )
    if args.run_commands is not None:
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
        return local_text_or_report(
            args,
            "runCommands",
            lambda: commands["get_run_sequence_report"](root, **run_sequence_kwargs),
            commands["format_run_sequence_report_text"],
            lambda: commands["get_run_sequence_text"](root, **run_sequence_kwargs),
        )
    if args.check_start_command is not None:
        return local_text_or_report(
            args,
            "checkStartCommand",
            lambda: commands["get_check_start_report"](root, args.check_start_command, cwd=args.start_cwd),
            commands["format_check_start_report_text"],
            lambda: commands["get_check_start_text"](root, args.check_start_command, cwd=args.start_cwd),
        )
    if args.start_command is not None:
        return local_text_or_report(
            args,
            "startCommand",
            lambda: commands["get_start_report"](root, args.start_command, cwd=args.start_cwd),
            commands["format_start_report_text"],
            lambda: commands["get_start_text"](root, args.start_command, cwd=args.start_cwd),
        )
    if args.port_check is not None:
        port_kwargs = {"port": args.port_check, "host": args.port_host, "timeout_ms": args.port_timeout_ms}
        return local_text_or_report(
            args,
            "port",
            lambda: commands["get_port_report"](root, **port_kwargs),
            commands["format_port_report_text"],
            lambda: commands["get_port_text"](root, **port_kwargs),
        )
    if args.http_check is not None:
        http_kwargs = {
            "url": args.http_check,
            "contains": args.http_contains,
            "timeout_ms": args.http_timeout_ms or 2_000,
            "max_body_chars": args.http_max_body_chars or 2_000,
            "regex": args.http_regex,
        }
        return local_text_or_report(
            args,
            "http",
            lambda: commands["get_http_report"](root, **http_kwargs),
            commands["format_http_report_text"],
            lambda: commands["get_http_text"](root, **http_kwargs),
        )
    if args.http_fetch is not None:
        http_fetch_kwargs = {
            "url": args.http_fetch,
            "timeout_ms": args.http_timeout_ms or 5_000,
            "max_body_chars": args.http_max_body_chars or 12_000,
        }
        return local_text_or_report(
            args,
            "httpFetch",
            lambda: commands["get_http_fetch_report"](root, **http_fetch_kwargs),
            commands["format_http_fetch_report_text"],
            lambda: commands["get_http_fetch_text"](root, **http_fetch_kwargs),
        )
    return None


def _cwd_command_text(command: Any, commands: dict[str, Any], usage: str, getter_name: str) -> str:
    checked_command, cwd, error, uses_named_options = commands["parse_interactive_cwd_command_argument"](
        command.argument,
        usage,
    )
    if error:
        return error
    if uses_named_options:
        return commands[getter_name](command=checked_command, cwd=cwd)
    return commands[getter_name](command=command.argument)


def _maybe_option_text(
    command: Any,
    commands: dict[str, Any],
    parser_name: str,
    getter_name: str,
    parsed_name: str,
    original_name: str,
) -> str:
    parsed, kwargs, error, uses_named_options = commands[parser_name](command.argument)
    if error:
        return error
    if uses_named_options:
        return commands[getter_name](**{parsed_name: parsed}, **kwargs)
    return commands[getter_name](**{original_name: command.argument})


def run_interactive_command_execution(command: Any, commands: dict[str, Any]) -> str | None:
    if command.type == "command":
        return _cwd_command_text(command, commands, "Usage: /command [--cwd PATH] -- <cmd>", "get_command_check_text")
    if command.type == "run":
        run_command, kwargs, error, uses_named_options = commands["parse_interactive_run_argument"](command.argument)
        if error:
            return error
        if uses_named_options:
            return commands["get_run_text"](command=run_command, **kwargs)
        return commands["get_run_text"](command=command.argument)
    if command.type == "run_sequence":
        return _maybe_option_text(
            command,
            commands,
            "parse_interactive_run_sequence_argument",
            "get_run_sequence_text",
            "commands",
            "argument",
        )
    if command.type == "check_run_sequence":
        run_commands, cwd, error, uses_named_options = commands["parse_interactive_check_run_sequence_argument"](
            command.argument
        )
        if error:
            return error
        if uses_named_options:
            return commands["get_check_run_sequence_text"](commands=run_commands, cwd=cwd)
        return commands["get_check_run_sequence_text"](argument=command.argument)
    if command.type == "check_start":
        return _cwd_command_text(command, commands, "Usage: /check-start [--cwd PATH] -- <cmd>", "get_check_start_text")
    if command.type == "start":
        return _cwd_command_text(command, commands, "Usage: /start [--cwd PATH] -- <cmd>", "get_start_text")
    if command.type == "port":
        return _maybe_option_text(command, commands, "parse_interactive_port_argument", "get_port_text", "port", "argument")
    if command.type == "http":
        return _maybe_option_text(command, commands, "parse_interactive_http_argument", "get_http_text", "url", "argument")
    if command.type == "http_fetch":
        return _maybe_option_text(
            command,
            commands,
            "parse_interactive_http_fetch_argument",
            "get_http_fetch_text",
            "url",
            "argument",
        )
    return None
