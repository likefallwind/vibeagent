from __future__ import annotations

import shlex
from collections.abc import Mapping

from .check_limit_parsing import parse_named_suggested_checks_limit
from .cli_parse_core import (
    parse_interactive_nonnegative_option,
    parse_interactive_positive_option,
    parse_interactive_timeout_option,
)
from .cli_parse_cwd_command import (
    parse_interactive_check_run_sequence_argument,
    parse_interactive_cwd_command_argument,
)
from .cli_parse_process_run import parse_interactive_wait_process_argument


def _duplicate_option_error(
    kwargs: Mapping[str, object],
    keyword: str,
    flag: str,
    usage: str,
) -> str | None:
    if keyword in kwargs:
        return f"{usage}\n  error: provide {flag} at most once."
    return None


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
    value_options: dict[str, tuple[str, str]] = {
        "--timeout-ms": ("timeout_ms", "timeout"),
        "--max-chars": ("max_output_chars", "positive"),
        "--cwd": ("cwd", "string"),
        "--context-lines": ("context_lines", "nonnegative"),
        "--max-diagnostics": ("max_diagnostics", "positive"),
        "--max-contexts": ("max_contexts", "positive"),
        "--max-bytes": ("max_bytes_per_context", "positive"),
    }
    bool_options = {
        "--output-contexts": "extract_output_contexts",
        "--output-diagnostics": "extract_output_diagnostics",
    }
    recognized_flags = set(value_options) | set(bool_options)
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in recognized_flags):
            return None, {}, f"{usage}\n  error: {error}", True
        return argument, {}, None, False

    uses_named_options = False
    for part in parts:
        if part == "--":
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in recognized_flags:
            uses_named_options = True
            break
        break
    if not uses_named_options:
        return argument, {}, None, False

    kwargs: dict[str, int | str | bool] = {}
    command_parts: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            command_parts.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in bool_options:
            if "=" in part:
                return None, {}, f"{usage}\n  error: {flag} does not take a value.", True
            keyword = bool_options[flag]
            duplicate_error = _duplicate_option_error(kwargs, keyword, flag, usage)
            if duplicate_error:
                return None, {}, duplicate_error, True
            kwargs[keyword] = True
            index += 1
            continue
        if flag in value_options:
            keyword, value_type = value_options[flag]
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            if value_type == "timeout":
                value, error = parse_interactive_timeout_option(flag, raw_value)
            elif value_type == "nonnegative":
                value, error = parse_interactive_nonnegative_option(flag, raw_value)
            elif value_type == "positive":
                value, error = parse_interactive_positive_option(flag, raw_value)
            else:
                if raw_value is None:
                    value, error = None, f"{flag} requires a value."
                else:
                    value, error = raw_value, None
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            duplicate_error = _duplicate_option_error(kwargs, keyword, flag, usage)
            if duplicate_error:
                return None, {}, duplicate_error, True
            kwargs[keyword] = value
            continue
        command_parts.extend(parts[index:])
        break

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
    value_options: dict[str, tuple[str, str]] = {
        "--timeout-ms": ("timeout_ms", "timeout"),
        "--max-chars": ("max_output_chars", "positive"),
        "--cwd": ("cwd", "string"),
        "--context-lines": ("context_lines", "nonnegative"),
        "--max-diagnostics": ("max_diagnostics", "positive"),
        "--max-contexts": ("max_contexts", "positive"),
        "--max-bytes": ("max_bytes_per_context", "positive"),
    }
    bool_options = {
        "--output-contexts": ("extract_output_contexts", True),
        "--output-diagnostics": ("extract_output_diagnostics", True),
        "--continue-on-failure": ("stop_on_failure", False),
        "--stop-on-failure": ("stop_on_failure", True),
    }
    recognized_flags = set(value_options) | set(bool_options)
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in recognized_flags):
            return None, {}, f"{usage}\n  error: {error}", True
        return None, {}, None, False

    uses_named_options = False
    for part in parts:
        if part == "--":
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in recognized_flags:
            uses_named_options = True
            break
        break
    if not uses_named_options:
        return None, {}, None, False

    kwargs: dict[str, int | str | bool] = {}
    command_parts: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            command_parts.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in bool_options:
            if "=" in part:
                return None, {}, f"{usage}\n  error: {flag} does not take a value.", True
            keyword, value = bool_options[flag]
            duplicate_error = _duplicate_option_error(kwargs, keyword, flag, usage)
            if duplicate_error:
                return None, {}, duplicate_error, True
            kwargs[keyword] = value
            index += 1
            continue
        if flag in value_options:
            keyword, value_type = value_options[flag]
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            if value_type == "timeout":
                value, error = parse_interactive_timeout_option(flag, raw_value)
            elif value_type == "nonnegative":
                value, error = parse_interactive_nonnegative_option(flag, raw_value)
            elif value_type == "positive":
                value, error = parse_interactive_positive_option(flag, raw_value)
            else:
                if raw_value is None:
                    value, error = None, f"{flag} requires a value."
                else:
                    value, error = raw_value, None
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            duplicate_error = _duplicate_option_error(kwargs, keyword, flag, usage)
            if duplicate_error:
                return None, {}, duplicate_error, True
            kwargs[keyword] = value
            continue
        command_parts.extend(parts[index:])
        break

    commands: list[str] = []
    current: list[str] = []
    for part in command_parts:
        if part == ";;":
            command = shlex.join(current).strip()
            if command:
                commands.append(command)
            current = []
            continue
        current.append(part)
    command = shlex.join(current).strip()
    if command:
        commands.append(command)
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
    value_options: dict[str, tuple[str, str]] = {
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
    bool_options = {
        "--output-contexts": ("extract_output_contexts", True),
        "--output-diagnostics": ("extract_output_diagnostics", True),
        "--continue-on-failure": ("stop_on_failure", False),
        "--stop-on-failure": ("stop_on_failure", True),
    }
    recognized_flags = set(value_options) | set(bool_options)
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in recognized_flags):
            return None, {}, f"{usage}\n  error: {error}", True
        return argument, {}, None, False

    uses_named_options = False
    for part in parts:
        if part == "--":
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in recognized_flags:
            uses_named_options = True
            break
        break
    if not uses_named_options:
        return argument, {}, None, False

    kwargs: dict[str, int | bool] = {}
    path_parts: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            path_parts.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in bool_options:
            if "=" in part:
                return None, {}, f"{usage}\n  error: {flag} does not take a value.", True
            keyword, value = bool_options[flag]
            duplicate_error = _duplicate_option_error(kwargs, keyword, flag, usage)
            if duplicate_error:
                return None, {}, duplicate_error, True
            kwargs[keyword] = value
            index += 1
            continue
        if flag in value_options:
            keyword, value_type = value_options[flag]
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            if value_type == "timeout":
                value, error = parse_interactive_timeout_option(flag, raw_value)
            elif value_type == "nonnegative":
                value, error = parse_interactive_nonnegative_option(flag, raw_value)
            else:
                value, error = parse_interactive_positive_option(flag, raw_value)
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            duplicate_error = _duplicate_option_error(kwargs, keyword, flag, usage)
            if duplicate_error:
                return None, {}, duplicate_error, True
            kwargs[keyword] = int(value)
            continue
        path_parts.extend(parts[index:])
        break

    focused_argument = shlex.join(path_parts).strip() or None
    return focused_argument, kwargs, None, True


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
    value_options: dict[str, tuple[str, str]] = {
        "--max-checks": ("max_checks", "positive"),
        "--timeout-ms": ("timeout_ms", "timeout"),
        "--max-chars": ("max_output_chars", "positive"),
        "--context-lines": ("context_lines", "nonnegative"),
        "--max-diagnostics": ("max_diagnostics", "positive"),
        "--max-contexts": ("max_contexts", "positive"),
        "--max-bytes": ("max_bytes_per_context", "positive"),
    }
    bool_options = {
        "--output-contexts": ("extract_output_contexts", True),
        "--output-diagnostics": ("extract_output_diagnostics", True),
        "--continue-on-failure": ("stop_on_failure", False),
        "--stop-on-failure": ("stop_on_failure", True),
    }
    recognized_flags = set(value_options) | set(bool_options)
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in recognized_flags):
            return None, {}, f"{usage}\n  error: {error}", True
        return argument, {}, None, False

    uses_named_options = False
    for part in parts:
        if part == "--":
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in recognized_flags:
            uses_named_options = True
            break
        break
    if not uses_named_options:
        return argument, {}, None, False

    kwargs: dict[str, int | bool] = {}
    max_parts: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            max_parts.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in bool_options:
            if "=" in part:
                return None, {}, f"{usage}\n  error: {flag} does not take a value.", True
            keyword, value = bool_options[flag]
            duplicate_error = _duplicate_option_error(kwargs, keyword, flag, usage)
            if duplicate_error:
                return None, {}, duplicate_error, True
            kwargs[keyword] = value
            index += 1
            continue
        if flag in value_options:
            keyword, value_type = value_options[flag]
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            if flag == "--max-checks":
                if "max_checks" in kwargs:
                    return None, {}, f"{usage}\n  error: provide --max-checks at most once.", True
                try:
                    value = parse_named_suggested_checks_limit(raw_value)
                except ValueError as error:
                    return None, {}, f"{usage}\n  error: {error}", True
                if value <= 0:
                    return None, {}, f"{usage}\n  error: --max-checks must be a positive integer.", True
                error = None
            elif value_type == "timeout":
                value, error = parse_interactive_timeout_option(flag, raw_value)
            elif value_type == "nonnegative":
                value, error = parse_interactive_nonnegative_option(flag, raw_value)
            else:
                value, error = parse_interactive_positive_option(flag, raw_value)
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            duplicate_error = _duplicate_option_error(kwargs, keyword, flag, usage)
            if duplicate_error:
                return None, {}, duplicate_error, True
            kwargs[keyword] = int(value)
            continue
        max_parts.extend(parts[index:])
        break

    selected_max = shlex.join(max_parts).strip() or None
    if selected_max and len(max_parts) != 1:
        return None, {}, f"{usage}\n  error: expected at most one max value.", True
    if selected_max and "max_checks" in kwargs:
        return None, {}, f"{usage}\n  error: provide either --max-checks or trailing max, not both.", True
    return selected_max, kwargs, None, True
