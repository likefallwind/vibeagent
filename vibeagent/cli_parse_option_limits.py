from __future__ import annotations

import shlex

from .cli_parse_core import parse_interactive_positive_option


def parse_interactive_option_limit_argument(
    argument: str | None,
    usage: str,
    option_specs: dict[str, str],
) -> tuple[dict[str, int], str | None, bool]:
    if not argument:
        return {}, None, False
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in option_specs):
            return {}, f"{usage}\n  error: {error}", True
        return {}, None, False

    if not _uses_limit_options(parts, option_specs):
        return {}, usage, True

    kwargs: dict[str, int] = {}
    index = 0
    while index < len(parts):
        part = parts[index]
        flag = _option_flag(part)
        if flag in option_specs:
            raw_value, index = _consume_option_value(parts, index)
            value, error = parse_interactive_positive_option(flag, raw_value)
            if error:
                return {}, f"{usage}\n  error: {error}", True
            keyword = option_specs[flag]
            if keyword in kwargs:
                return {}, f"{usage}\n  error: provide {flag} at most once.", True
            kwargs[keyword] = int(value)
            continue
        return {}, f"{usage}\n  error: Unknown option: {part}", True

    return kwargs, None, True


def _uses_limit_options(parts: list[str], option_specs: dict[str, str]) -> bool:
    for part in parts:
        flag = _option_flag(part)
        if part.startswith("--") or flag in option_specs:
            return True
    return False


def _option_flag(part: str) -> str:
    return part.split("=", 1)[0] if part.startswith("--") else part


def _consume_option_value(parts: list[str], index: int) -> tuple[str | None, int]:
    part = parts[index]
    if "=" in part:
        return part.split("=", 1)[1], index + 1
    return (parts[index + 1] if index + 1 < len(parts) else None), index + 2
