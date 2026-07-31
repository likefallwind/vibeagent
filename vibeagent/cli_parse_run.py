from __future__ import annotations

import shlex

from .cli_parse_cwd_command import (
    parse_interactive_check_run_sequence_argument,
    parse_interactive_cwd_command_argument,
)
from .cli_parse_process_run import parse_interactive_wait_process_argument
from .cli_parse_run_options import (
    RunBoolOptions,
    RunValueOptions,
    parse_run_named_options,
    split_run_argument,
    split_sequence_commands,
)


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
    value_options: RunValueOptions = {
        "--timeout-ms": ("timeout_ms", "timeout"),
        "--max-chars": ("max_output_chars", "positive"),
        "--cwd": ("cwd", "string"),
        "--context-lines": ("context_lines", "nonnegative"),
        "--max-diagnostics": ("max_diagnostics", "positive"),
        "--max-contexts": ("max_contexts", "positive"),
        "--max-bytes": ("max_bytes_per_context", "positive"),
    }
    bool_options: RunBoolOptions = {
        "--output-contexts": ("extract_output_contexts", True),
        "--output-diagnostics": ("extract_output_diagnostics", True),
    }
    recognized_flags = set(value_options) | set(bool_options)
    parts, split_error, uses_named_options = split_run_argument(argument, recognized_flags)
    if split_error:
        return None, {}, f"{usage}\n  error: {split_error}", True
    if not uses_named_options or parts is None:
        return argument, {}, None, False

    command_parts, kwargs, error = parse_run_named_options(
        parts,
        usage=usage,
        value_options=value_options,
        bool_options=bool_options,
    )
    if error:
        return None, {}, error, True

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
    value_options: RunValueOptions = {
        "--timeout-ms": ("timeout_ms", "timeout"),
        "--max-chars": ("max_output_chars", "positive"),
        "--cwd": ("cwd", "string"),
        "--context-lines": ("context_lines", "nonnegative"),
        "--max-diagnostics": ("max_diagnostics", "positive"),
        "--max-contexts": ("max_contexts", "positive"),
        "--max-bytes": ("max_bytes_per_context", "positive"),
    }
    bool_options: RunBoolOptions = {
        "--output-contexts": ("extract_output_contexts", True),
        "--output-diagnostics": ("extract_output_diagnostics", True),
        "--continue-on-failure": ("stop_on_failure", False),
        "--stop-on-failure": ("stop_on_failure", True),
    }
    recognized_flags = set(value_options) | set(bool_options)
    parts, split_error, uses_named_options = split_run_argument(argument, recognized_flags)
    if split_error:
        return None, {}, f"{usage}\n  error: {split_error}", True
    if not uses_named_options or parts is None:
        return None, {}, None, False

    command_parts, kwargs, error = parse_run_named_options(
        parts,
        usage=usage,
        value_options=value_options,
        bool_options=bool_options,
    )
    if error:
        return None, {}, error, True

    commands = split_sequence_commands(command_parts)
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
    value_options: RunValueOptions = {
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
    bool_options: RunBoolOptions = {
        "--output-contexts": ("extract_output_contexts", True),
        "--output-diagnostics": ("extract_output_diagnostics", True),
        "--continue-on-failure": ("stop_on_failure", False),
        "--stop-on-failure": ("stop_on_failure", True),
    }
    recognized_flags = set(value_options) | set(bool_options)
    parts, split_error, uses_named_options = split_run_argument(argument, recognized_flags)
    if split_error:
        return None, {}, f"{usage}\n  error: {split_error}", True
    if not uses_named_options or parts is None:
        return argument, {}, None, False

    path_parts, parsed_kwargs, error = parse_run_named_options(
        parts,
        usage=usage,
        value_options=value_options,
        bool_options=bool_options,
    )
    if error:
        return None, {}, error, True

    focused_argument = shlex.join(path_parts).strip() or None
    return focused_argument, parsed_kwargs, None, True


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
    value_options: RunValueOptions = {
        "--max-checks": ("max_checks", "suggested-checks-limit"),
        "--timeout-ms": ("timeout_ms", "timeout"),
        "--max-chars": ("max_output_chars", "positive"),
        "--context-lines": ("context_lines", "nonnegative"),
        "--max-diagnostics": ("max_diagnostics", "positive"),
        "--max-contexts": ("max_contexts", "positive"),
        "--max-bytes": ("max_bytes_per_context", "positive"),
    }
    bool_options: RunBoolOptions = {
        "--output-contexts": ("extract_output_contexts", True),
        "--output-diagnostics": ("extract_output_diagnostics", True),
        "--continue-on-failure": ("stop_on_failure", False),
        "--stop-on-failure": ("stop_on_failure", True),
    }
    recognized_flags = set(value_options) | set(bool_options)
    parts, split_error, uses_named_options = split_run_argument(argument, recognized_flags)
    if split_error:
        return None, {}, f"{usage}\n  error: {split_error}", True
    if not uses_named_options or parts is None:
        return argument, {}, None, False

    max_parts, kwargs, error = parse_run_named_options(
        parts,
        usage=usage,
        value_options=value_options,
        bool_options=bool_options,
    )
    if error:
        return None, {}, error, True

    selected_max = shlex.join(max_parts).strip() or None
    if selected_max and len(max_parts) != 1:
        return None, {}, f"{usage}\n  error: expected at most one max value.", True
    if selected_max and "max_checks" in kwargs:
        return None, {}, f"{usage}\n  error: provide either --max-checks or trailing max, not both.", True
    return selected_max, kwargs, None, True
