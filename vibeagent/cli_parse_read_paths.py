from __future__ import annotations

import shlex

from .cli_parse_core import duplicate_option_error, parse_interactive_positive_option


ReadPathKwargs = dict[str, int | bool]

_BOOLEAN_VALUES = {
    "1": True,
    "true": True,
    "yes": True,
    "on": True,
    "0": False,
    "false": False,
    "no": False,
    "off": False,
}


def parse_interactive_read_path_options(
    argument: str | None,
    usage: str,
    max_bytes_keyword: str,
    required_message: str,
) -> tuple[list[str] | None, ReadPathKwargs, str | None, bool]:
    if not argument:
        return None, {}, None, False

    option_specs = {"--max-bytes": max_bytes_keyword}
    boolean_options = {"--line-numbers": "show_line_numbers"}
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        if any(flag in argument for flag in option_specs | boolean_options):
            return None, {}, f"{usage}\n  error: {error}", True
        return None, {}, None, False

    if not _uses_read_named_options(parts, option_specs, boolean_options):
        return None, {}, None, False

    kwargs: ReadPathKwargs = {}
    paths: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            paths.extend(parts[index + 1 :])
            break
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in boolean_options:
            value, error = _parse_boolean_option(part, flag, usage)
            if error:
                return None, {}, error, True
            keyword = boolean_options[flag]
            duplicate_error = duplicate_option_error(kwargs, keyword, flag, usage)
            if duplicate_error:
                return None, {}, duplicate_error, True
            kwargs[keyword] = value
            index += 1
            continue
        if flag in option_specs:
            raw_value, index = _consume_option_value(parts, index)
            value, error = parse_interactive_positive_option(flag, raw_value)
            if error:
                return None, {}, f"{usage}\n  error: {error}", True
            keyword = option_specs[flag]
            duplicate_error = duplicate_option_error(kwargs, keyword, flag, usage)
            if duplicate_error:
                return None, {}, duplicate_error, True
            kwargs[keyword] = int(value)
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}", True
        paths.append(part)
        index += 1

    if not paths:
        return None, {}, f"{usage}\n  error: {required_message}", True
    return paths, kwargs, None, True


def _uses_read_named_options(
    parts: list[str],
    option_specs: dict[str, str],
    boolean_options: dict[str, str],
) -> bool:
    if "--" in parts:
        return True
    for part in parts:
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if part.startswith("--") or flag in option_specs or flag in boolean_options:
            return True
    return False


def _parse_boolean_option(part: str, flag: str, usage: str) -> tuple[bool, str | None]:
    if "=" not in part:
        return True, None
    raw_value = part.split("=", 1)[1].strip().lower()
    if raw_value not in _BOOLEAN_VALUES:
        return False, f"{usage}\n  error: {flag} must be a boolean."
    return _BOOLEAN_VALUES[raw_value], None


def _consume_option_value(parts: list[str], index: int) -> tuple[str | None, int]:
    part = parts[index]
    if "=" in part:
        return part.split("=", 1)[1], index + 1
    return (parts[index + 1] if index + 1 < len(parts) else None), index + 2
