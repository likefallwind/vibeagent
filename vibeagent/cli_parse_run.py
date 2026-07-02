from __future__ import annotations

import shlex

from .cli_parse_core import (
    parse_interactive_nonnegative_option,
    parse_interactive_positive_option,
    parse_interactive_timeout_option,
)


def parse_interactive_wait_process_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int | str | bool], str | None, bool]:
    usage = (
        "Usage: /wait-process <id> [timeout-ms] [chars] "
        "[--timeout-ms N] [--max-chars N] [--stdout TEXT] [--stderr TEXT] [--regex]"
    )
    if not argument:
        return None, {}, None, False
    value_options: dict[str, tuple[str, str]] = {
        "--timeout-ms": ("timeout_ms", "timeout"),
        "--max-chars": ("max_output_chars", "positive"),
        "--stdout": ("stdout_contains", "string"),
        "--stderr": ("stderr_contains", "string"),
    }
    bool_options = {"--regex": "regex"}
    recognized_flags = set(value_options) | set(bool_options)
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in recognized_flags):
            return None, {}, f"{usage}\n  error: {error}", True
        return None, {}, None, False

    uses_named_options = "--" in parts
    if not uses_named_options:
        for part in parts:
            flag = part.split("=", 1)[0] if part.startswith("--") else part
            if part.startswith("--") or flag in recognized_flags:
                uses_named_options = True
                break
    if not uses_named_options:
        return None, {}, None, False

    kwargs: dict[str, int | str | bool] = {}
    positional: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            positional.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in bool_options:
            if "=" in part:
                return None, {}, f"{usage}\n  error: {flag} does not take a value.", True
            kwargs[bool_options[flag]] = True
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
            elif value_type == "positive":
                value, error = parse_interactive_positive_option(flag, raw_value)
            else:
                if raw_value is None:
                    value, error = None, f"{flag} requires a value."
                elif raw_value == "":
                    value, error = None, f"{flag} must be a non-empty string."
                else:
                    value, error = raw_value, None
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            kwargs[keyword] = value
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}", True
        positional.append(part)
        index += 1

    if not positional:
        return None, {}, f"{usage}\n  error: process id is required.", True
    if len(positional) > 3:
        return None, {}, usage, True
    process_id = positional[0]
    if len(positional) >= 2:
        value, error = parse_interactive_timeout_option("[timeout-ms]", positional[1])
        if error:
            return None, {}, f"{usage}\n  error: invalid timeout ms: {positional[1]}", True
        kwargs["timeout_ms"] = int(value)
    if len(positional) == 3:
        value, error = parse_interactive_positive_option("[chars]", positional[2])
        if error:
            return None, {}, f"{usage}\n  error: invalid max chars: {positional[2]}", True
        kwargs["max_output_chars"] = int(value)
    return process_id, kwargs, None, True


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
            kwargs[bool_options[flag]] = True
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


def parse_interactive_cwd_command_argument(
    argument: str | None,
    usage: str,
) -> tuple[str | None, str | None, str | None, bool]:
    if not argument:
        return None, None, None, False
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if "--cwd" in argument:
            return None, None, f"{usage}\n  error: {error}", True
        return argument, None, None, False

    uses_named_options = False
    for part in parts:
        if part == "--":
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag == "--cwd":
            uses_named_options = True
            break
        break
    if not uses_named_options:
        return argument, None, None, False

    cwd: str | None = None
    command_parts: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            command_parts.extend(parts[index + 1 :])
            break
        if part == "--cwd" or part.startswith("--cwd="):
            if cwd is not None:
                return None, None, f"{usage}\n  error: --cwd can only be provided once.", True
            if part.startswith("--cwd="):
                cwd = part.split("=", 1)[1]
                index += 1
            else:
                if index + 1 >= len(parts):
                    return None, None, f"{usage}\n  error: --cwd requires a value.", True
                cwd = parts[index + 1]
                index += 2
            continue
        command_parts.extend(parts[index:])
        break

    command = shlex.join(command_parts).strip()
    if not command:
        return None, cwd, f"{usage}\n  error: command is required.", True
    return command, cwd, None, True


def parse_interactive_check_run_sequence_argument(
    argument: str | None,
) -> tuple[list[str] | None, str | None, str | None, bool]:
    usage = "Usage: /check-run-seq [--cwd PATH] -- <cmd> ;; <cmd>"
    if not argument:
        return None, None, None, False
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if "--cwd" in argument:
            return None, None, f"{usage}\n  error: {error}", True
        return None, None, None, False

    uses_named_options = False
    for part in parts:
        if part == "--":
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag == "--cwd":
            uses_named_options = True
            break
        break
    if not uses_named_options:
        return None, None, None, False

    cwd: str | None = None
    command_parts: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            command_parts.extend(parts[index + 1 :])
            break
        if part == "--cwd" or part.startswith("--cwd="):
            if cwd is not None:
                return None, None, f"{usage}\n  error: --cwd can only be provided once.", True
            if part.startswith("--cwd="):
                cwd = part.split("=", 1)[1]
                index += 1
            else:
                if index + 1 >= len(parts):
                    return None, None, f"{usage}\n  error: --cwd requires a value.", True
                cwd = parts[index + 1]
                index += 2
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
        return None, cwd, f"{usage}\n  error: at least one command is required.", True
    if len(commands) > 10:
        return None, cwd, f"{usage}\n  error: expected at most 10 commands.", True
    return commands, cwd, None, True
