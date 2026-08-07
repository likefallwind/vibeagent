from __future__ import annotations

import shlex

from .cli_parse_core import duplicate_option_error, parse_interactive_nonnegative_option, parse_interactive_positive_option


def option_flag(part: str) -> str:
    return part.split("=", 1)[0] if part.startswith("--") else part


def split_named_parts(
    argument: str | None,
    *,
    usage: str,
    recognized_flags: set[str],
) -> tuple[list[str] | None, str | None, bool]:
    if not argument:
        return None, None, False
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in recognized_flags):
            return None, f"{usage}\n  error: {error}", True
        return None, None, False

    uses_named_options = "--" in parts
    if not uses_named_options:
        uses_named_options = any(part.startswith("--") or option_flag(part) in recognized_flags for part in parts)
    if not uses_named_options:
        return None, None, False
    return parts, None, True


def parse_optional_path_limit_argument(
    argument: str | None,
    *,
    usage: str,
    option_specs: dict[str, tuple[str, str]],
) -> tuple[str | None, dict[str, int], str | None, bool]:
    parts, error, handled = split_named_parts(argument, usage=usage, recognized_flags=set(option_specs))
    if error or not handled:
        return None, {}, error, handled
    assert parts is not None

    kwargs: dict[str, int] = {}
    path_parts: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            path_parts.extend(parts[index + 1 :])
            break
        flag = option_flag(part)
        if flag in option_specs:
            keyword, value_type = option_specs[flag]
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            parser = parse_interactive_nonnegative_option if value_type == "nonnegative" else parse_interactive_positive_option
            value, value_error = parser(flag, raw_value)
            if value_error:
                return None, {}, f"{usage}\n  error: {value_error}", True
            duplicate_error = duplicate_option_error(kwargs, keyword, flag, usage)
            if duplicate_error:
                return None, {}, duplicate_error, True
            kwargs[keyword] = int(value)
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}", True
        path_parts.append(part)
        index += 1

    if len(path_parts) > 1:
        return None, {}, usage, True
    path = path_parts[0].strip() if path_parts else None
    if path == "":
        path = None
    return path, kwargs, None, True
