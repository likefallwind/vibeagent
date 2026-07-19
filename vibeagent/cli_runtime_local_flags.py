from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .cli_local_result import local_text_or_report
from .workspace_resolve import resolve_inside_run


def _resolve_write_stdin_content(args: argparse.Namespace, root: str | Path) -> str | None:
    if args.write_stdin_file is None:
        return args.write_stdin
    path = resolve_inside_run(root, args.write_stdin_file)
    if not path.exists():
        raise ValueError(f"--write-stdin-file does not exist: {args.write_stdin_file}")
    if not path.is_file():
        raise ValueError(f"--write-stdin-file is not a file: {args.write_stdin_file}")
    return path.read_text(encoding="utf-8")


def run_runtime_local_flag(
    args: argparse.Namespace,
    project_root: Path | None,
    commands: dict[str, Any],
) -> tuple[str, dict[str, object]] | None:
    root = project_root or "."
    if args.env:
        return local_text_or_report(
            args,
            "env",
            lambda: commands["get_env_report"](root),
            commands["format_env_report_text"],
            lambda: commands["get_env_text"](root),
        )
    if args.processes:
        return local_text_or_report(
            args,
            "processes",
            lambda: commands["get_processes_report"](root),
            commands["format_processes_report_text"],
            lambda: commands["get_processes_text"](root),
        )
    if args.process_output is not None:
        process_kwargs = {"process_id": args.process_output, "max_output_chars": args.process_max_chars}
        return local_text_or_report(
            args,
            "process",
            lambda: commands["get_process_report"](root, **process_kwargs),
            commands["format_process_report_text"],
            lambda: commands["get_process_text"](root, **process_kwargs),
        )
    if args.process_output_contexts is not None:
        process_context_kwargs = {
            "process_id": args.process_output_contexts,
            "max_output_chars": args.process_max_chars,
            "context_lines": args.process_output_context_lines,
            "max_contexts": args.process_output_context_max,
            "max_bytes_per_context": args.process_output_context_max_bytes,
        }
        return local_text_or_report(
            args,
            "processOutputContexts",
            lambda: commands["get_process_output_contexts_report"](root, **process_context_kwargs),
            commands["format_process_output_contexts_report_text"],
            lambda: commands["get_process_output_contexts_text"](root, **process_context_kwargs),
        )
    if args.process_output_diagnostics is not None:
        process_diagnostic_kwargs = {
            "process_id": args.process_output_diagnostics,
            "max_output_chars": args.process_max_chars,
            "context_lines": args.process_output_context_lines,
            "max_diagnostics": args.process_output_diagnostic_max,
            "max_contexts": args.process_output_context_max,
            "max_bytes_per_context": args.process_output_context_max_bytes,
        }
        return local_text_or_report(
            args,
            "processOutputDiagnostics",
            lambda: commands["get_process_output_diagnostics_report"](root, **process_diagnostic_kwargs),
            commands["format_process_output_diagnostics_report_text"],
            lambda: commands["get_process_output_diagnostics_text"](root, **process_diagnostic_kwargs),
        )
    if args.wait_process is not None:
        wait_process_kwargs = {
            "process_id": args.wait_process,
            "timeout_ms": args.wait_timeout_ms,
            "max_output_chars": args.wait_max_chars,
            "stdout_contains": args.wait_stdout,
            "stderr_contains": args.wait_stderr,
            "regex": args.wait_regex,
        }
        return local_text_or_report(
            args,
            "waitProcess",
            lambda: commands["get_wait_process_report"](root, **wait_process_kwargs),
            commands["format_wait_process_report_text"],
            lambda: commands["get_wait_process_text"](root, **wait_process_kwargs),
        )
    if args.check_write_process is not None:
        write_kwargs = {"process_id": args.check_write_process, "content": _resolve_write_stdin_content(args, root)}
        return local_text_or_report(
            args,
            "checkWriteProcess",
            lambda: commands["get_check_write_process_report"](root, **write_kwargs),
            commands["format_check_write_process_report_text"],
            lambda: commands["get_check_write_process_text"](root, **write_kwargs),
        )
    if args.write_process is not None:
        write_kwargs = {"process_id": args.write_process, "content": _resolve_write_stdin_content(args, root)}
        return local_text_or_report(
            args,
            "writeProcess",
            lambda: commands["get_write_process_report"](root, **write_kwargs),
            commands["format_write_process_report_text"],
            lambda: commands["get_write_process_text"](root, **write_kwargs),
        )
    if args.check_stop_process is not None:
        return local_text_or_report(
            args,
            "checkStopProcess",
            lambda: commands["get_check_stop_process_report"](root, args.check_stop_process),
            commands["format_check_stop_process_report_text"],
            lambda: commands["get_check_stop_process_text"](root, args.check_stop_process),
        )
    if args.stop_process is not None:
        return local_text_or_report(
            args,
            "stopProcess",
            lambda: commands["get_stop_process_report"](root, args.stop_process),
            commands["format_stop_process_report_text"],
            lambda: commands["get_stop_process_text"](root, args.stop_process),
        )
    if args.check_stop_all_processes:
        return local_text_or_report(
            args,
            "checkStopAllProcesses",
            lambda: commands["get_check_stop_all_processes_report"](root),
            commands["format_check_stop_all_processes_report_text"],
            lambda: commands["get_check_stop_all_processes_text"](root),
        )
    if args.stop_all_processes:
        return local_text_or_report(
            args,
            "stopAllProcesses",
            lambda: commands["get_stop_all_processes_report"](root),
            commands["format_stop_all_processes_report_text"],
            lambda: commands["get_stop_all_processes_text"](root),
        )
    return None


def _process_output_contexts(command: Any, commands: dict[str, Any]) -> str:
    process_id, kwargs, error = commands["parse_interactive_process_output_argument"](
        command.argument,
        "Usage: /process-output-contexts <id> [chars] [--max-chars N] [--context-lines N] [--max-contexts N] [--max-bytes N]",
        {
            "--max-chars": ("max_output_chars", False),
            "--context-lines": ("context_lines", True),
            "--max-contexts": ("max_contexts", False),
            "--max-bytes": ("max_bytes_per_context", False),
        },
    )
    return error if error else commands["get_process_output_contexts_text"](process_id=process_id, **kwargs)


def _process_output_diagnostics(command: Any, commands: dict[str, Any]) -> str:
    process_id, kwargs, error = commands["parse_interactive_process_output_argument"](
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
    return error if error else commands["get_process_output_diagnostics_text"](process_id=process_id, **kwargs)


def _wait_process(command: Any, commands: dict[str, Any]) -> str:
    process_id, kwargs, error = commands["parse_interactive_wait_process_argument"](command.argument)
    if error:
        return error
    return commands["get_wait_process_text"](process_id=process_id, **kwargs)


def run_interactive_runtime_command(command: Any, commands: dict[str, Any]) -> str | None:
    if command.type == "env":
        return commands["get_env_text"]()
    if command.type == "processes":
        return commands["get_processes_text"]()
    if command.type == "process":
        return commands["get_process_text"](argument=command.argument)
    if command.type == "process_output_contexts":
        return _process_output_contexts(command, commands)
    if command.type == "process_output_diagnostics":
        return _process_output_diagnostics(command, commands)
    if command.type == "wait_process":
        return _wait_process(command, commands)
    if command.type == "check_write_process":
        return commands["get_check_write_process_text"](argument=command.argument)
    if command.type == "write_process":
        return commands["get_write_process_text"](argument=command.argument)
    if command.type == "check_stop_process":
        return commands["get_check_stop_process_text"](process_id=command.argument)
    if command.type == "stop_process":
        return commands["get_stop_process_text"](process_id=command.argument)
    if command.type == "check_stop_all_processes":
        return commands["get_check_stop_all_processes_text"]()
    if command.type == "stop_all_processes":
        return commands["get_stop_all_processes_text"]()
    return None
