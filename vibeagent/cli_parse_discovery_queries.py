from __future__ import annotations

import shlex

from .cli_parse_core import parse_interactive_nonnegative_option, parse_interactive_positive_option


QueryKwargs = dict[str, int | str | bool]
QueryValueOptions = dict[str, tuple[str, str]]
QueryBoolOptions = dict[str, tuple[str, bool]]


def parse_interactive_query_argument(
    argument: str | None,
    *,
    usage: str,
    value_options: QueryValueOptions,
    bool_options: QueryBoolOptions,
) -> tuple[str | None, QueryKwargs, str | None, bool]:
    if not argument:
        return None, {}, None, False

    recognized_flags = set(value_options) | set(bool_options)
    parts, error, handled = _split_named_parts(
        argument,
        usage=usage,
        recognized_flags=recognized_flags,
    )
    if error or not handled:
        return None, {}, error, handled
    assert parts is not None

    kwargs: QueryKwargs = {}
    query_parts: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            query_parts.extend(parts[index + 1 :])
            break
        flag = _option_flag(part)
        if flag in bool_options:
            if "=" in part:
                return None, {}, f"{usage}\n  error: {flag} does not take a value.", True
            keyword, value = bool_options[flag]
            if keyword in kwargs:
                return None, {}, f"{usage}\n  error: provide {flag} at most once.", True
            kwargs[keyword] = value
            index += 1
            continue
        if flag in value_options:
            keyword, value_type = value_options[flag]
            raw_value, index = _consume_option_value(parts, index)
            value, error = _parse_query_value(flag, raw_value, value_type)
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            if keyword in kwargs:
                return None, {}, f"{usage}\n  error: provide {flag} at most once.", True
            kwargs[keyword] = value
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}", True
        query_parts.append(part)
        index += 1

    query = " ".join(query_parts).strip()
    if not query:
        return None, {}, f"{usage}\n  error: query is required.", True
    return query, kwargs, None, True


def _split_named_parts(
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
        uses_named_options = any(part.startswith("--") or _option_flag(part) in recognized_flags for part in parts)
    if not uses_named_options:
        return None, None, False
    return parts, None, True


def _parse_query_value(
    flag: str,
    raw_value: str | None,
    value_type: str,
) -> tuple[int | str | None, str | None]:
    if value_type == "positive":
        return parse_interactive_positive_option(flag, raw_value)
    if value_type == "nonnegative":
        return parse_interactive_nonnegative_option(flag, raw_value)
    if raw_value is None:
        return None, f"{flag} requires a value."
    if raw_value == "":
        return None, f"{flag} must be a non-empty string."
    return raw_value, None


def _option_flag(part: str) -> str:
    return part.split("=", 1)[0] if part.startswith("--") else part


def _consume_option_value(parts: list[str], index: int) -> tuple[str | None, int]:
    part = parts[index]
    if "=" in part:
        return part.split("=", 1)[1], index + 1
    return (parts[index + 1] if index + 1 < len(parts) else None), index + 2
