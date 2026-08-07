from __future__ import annotations

import shlex

from .cli_parse_core import (
    duplicate_option_error,
    parse_interactive_positive_option,
    parse_interactive_timeout_option,
)


def parse_interactive_port_argument(
    argument: str | None,
) -> tuple[int | None, dict[str, int | str], str | None, bool]:
    usage = "Usage: /port <port> [host] [timeout-ms] [--host HOST] [--timeout-ms N]"
    if not argument:
        return None, {}, None, False
    value_options = {
        "--host": ("host", "string"),
        "--timeout-ms": ("timeout_ms", "timeout"),
    }
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in value_options):
            return None, {}, f"{usage}\n  error: {error}", True
        return None, {}, None, False

    uses_named_options = "--" in parts
    if not uses_named_options:
        for part in parts:
            flag = part.split("=", 1)[0] if part.startswith("--") else part
            if part.startswith("--") or flag in value_options:
                uses_named_options = True
                break
    if not uses_named_options:
        return None, {}, None, False

    kwargs: dict[str, int | str] = {}
    positional: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            positional.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
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
            else:
                if raw_value is None:
                    value, error = None, f"{flag} requires a value."
                elif raw_value == "":
                    value, error = None, f"{flag} must be a non-empty string."
                else:
                    value, error = raw_value, None
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            duplicate_error = duplicate_option_error(kwargs, keyword, flag, usage)
            if duplicate_error:
                return None, {}, duplicate_error, True
            kwargs[keyword] = value
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}", True
        positional.append(part)
        index += 1

    if not positional:
        return None, {}, f"{usage}\n  error: port is required.", True
    if len(positional) > 1:
        return None, {}, usage, True
    value, error = parse_interactive_positive_option("[port]", positional[0])
    if error:
        return None, {}, f"{usage}\n  error: invalid port: {positional[0]}", True
    return int(value), kwargs, None, True


def parse_interactive_http_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int | str | bool], str | None, bool]:
    usage = "Usage: /http <url> [contains] [--timeout-ms N] [--max-body-chars N] [--contains TEXT] [--regex]"
    if not argument:
        return None, {}, None, False
    value_options: dict[str, tuple[str, str]] = {
        "--timeout-ms": ("timeout_ms", "timeout"),
        "--max-body-chars": ("max_body_chars", "positive"),
        "--contains": ("contains", "string"),
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
            keyword = bool_options[flag]
            duplicate_error = duplicate_option_error(kwargs, keyword, flag, usage)
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
            duplicate_error = duplicate_option_error(kwargs, keyword, flag, usage)
            if duplicate_error:
                return None, {}, duplicate_error, True
            kwargs[keyword] = value
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}", True
        positional.append(part)
        index += 1

    if not positional:
        return None, {}, f"{usage}\n  error: url is required.", True
    url = positional[0]
    positional_contains = " ".join(positional[1:]).strip() or None
    if positional_contains is not None:
        if "contains" in kwargs:
            return None, {}, f"{usage}\n  error: provide either --contains or positional contains, not both.", True
        kwargs["contains"] = positional_contains
    return url, kwargs, None, True


def parse_interactive_http_fetch_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int], str | None, bool]:
    usage = "Usage: /http-fetch <url> [--timeout-ms N] [--max-body-chars N]"
    if not argument:
        return None, {}, None, False
    option_specs = {
        "--timeout-ms": ("timeout_ms", "timeout"),
        "--max-body-chars": ("max_body_chars", "positive"),
    }
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in option_specs):
            return None, {}, f"{usage}\n  error: {error}", True
        return None, {}, None, False

    uses_named_options = "--" in parts
    if not uses_named_options:
        for part in parts:
            flag = part.split("=", 1)[0] if part.startswith("--") else part
            if part.startswith("--") or flag in option_specs:
                uses_named_options = True
                break
    if not uses_named_options:
        return None, {}, None, False

    kwargs: dict[str, int] = {}
    positional: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            positional.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in option_specs:
            keyword, value_type = option_specs[flag]
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            if value_type == "timeout":
                value, error = parse_interactive_timeout_option(flag, raw_value)
            else:
                value, error = parse_interactive_positive_option(flag, raw_value)
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            duplicate_error = duplicate_option_error(kwargs, keyword, flag, usage)
            if duplicate_error:
                return None, {}, duplicate_error, True
            kwargs[keyword] = int(value)
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}", True
        positional.append(part)
        index += 1

    if not positional:
        return None, {}, f"{usage}\n  error: url is required.", True
    if len(positional) > 1:
        return None, {}, usage, True
    return positional[0], kwargs, None, True
