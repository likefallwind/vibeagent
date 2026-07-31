from __future__ import annotations

import shlex
from typing import Literal

from .check_limit_parsing import parse_named_suggested_checks_limit
from .cli_parse_core import (
    duplicate_option_error,
    parse_interactive_nonnegative_option,
    parse_interactive_positive_option,
    parse_interactive_timeout_option,
)

RunValueOptionKind = Literal["timeout", "nonnegative", "positive", "string", "suggested-checks-limit"]
RunValueOptions = dict[str, tuple[str, RunValueOptionKind]]
RunBoolOptions = dict[str, tuple[str, bool]]
RunKwargs = dict[str, int | str | bool]


def split_run_argument(argument: str, recognized_flags: set[str]) -> tuple[list[str] | None, str | None, bool]:
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in recognized_flags):
            return None, str(error), True
        return None, None, False

    for part in parts:
        if part == "--":
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in recognized_flags:
            return parts, None, True
        break
    return parts, None, False


def parse_run_named_options(
    parts: list[str],
    *,
    usage: str,
    value_options: RunValueOptions,
    bool_options: RunBoolOptions,
) -> tuple[list[str] | None, RunKwargs, str | None]:
    kwargs: RunKwargs = {}
    trailing_parts: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            trailing_parts.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in bool_options:
            if "=" in part:
                return None, {}, f"{usage}\n  error: {flag} does not take a value."
            keyword, value = bool_options[flag]
            duplicate_error = duplicate_option_error(kwargs, keyword, flag, usage)
            if duplicate_error:
                return None, {}, duplicate_error
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
            if value_type == "suggested-checks-limit":
                duplicate_error = duplicate_option_error(kwargs, keyword, flag, usage)
                if duplicate_error:
                    return None, {}, duplicate_error
            value, error = parse_run_option_value(flag, raw_value, value_type)
            if error:
                return None, {}, f"{usage}\n  error: {error}"
            duplicate_error = duplicate_option_error(kwargs, keyword, flag, usage)
            if duplicate_error:
                return None, {}, duplicate_error
            kwargs[keyword] = value
            continue
        trailing_parts.extend(parts[index:])
        break
    return trailing_parts, kwargs, None


def parse_run_option_value(
    flag: str,
    raw_value: str | None,
    value_type: RunValueOptionKind,
) -> tuple[int | str | None, str | None]:
    if value_type == "timeout":
        return parse_interactive_timeout_option(flag, raw_value)
    if value_type == "nonnegative":
        return parse_interactive_nonnegative_option(flag, raw_value)
    if value_type == "positive":
        return parse_interactive_positive_option(flag, raw_value)
    if value_type == "suggested-checks-limit":
        try:
            value = parse_named_suggested_checks_limit(raw_value)
        except ValueError as error:
            return None, str(error)
        if value <= 0:
            return None, f"{flag} must be a positive integer."
        return value, None
    if raw_value is None:
        return None, f"{flag} requires a value."
    return raw_value, None


def split_sequence_commands(command_parts: list[str]) -> list[str]:
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
    return commands
