from __future__ import annotations

import shlex

from .cli_parse_core import (
    duplicate_option_error,
    parse_interactive_max_chars_option,
    parse_interactive_nonnegative_option,
    parse_interactive_positive_option,
)
from .cli_parse_http_runtime import (
    parse_interactive_http_argument,
    parse_interactive_http_fetch_argument,
    parse_interactive_port_argument,
)


def parse_interactive_process_output_argument(
    argument: str | None,
    usage: str,
    option_specs: dict[str, tuple[str, bool]],
) -> tuple[str | None, dict[str, int], str | None]:
    if not argument:
        return None, {}, usage
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        return None, {}, f"{usage}\n  error: {error}"
    process_id: str | None = None
    legacy_max_chars: int | None = None
    kwargs: dict[str, int] = {}
    index = 0
    while index < len(parts):
        part = parts[index]
        flag = part.split("=", 1)[0] if part.startswith("--") else part
        if flag in option_specs:
            keyword, allow_zero = option_specs[flag]
            if "=" in part:
                raw_value = part.split("=", 1)[1]
                index += 1
            else:
                raw_value = parts[index + 1] if index + 1 < len(parts) else None
                index += 2
            if keyword == "max_output_chars":
                parser = parse_interactive_max_chars_option
            else:
                parser = parse_interactive_nonnegative_option if allow_zero else parse_interactive_positive_option
            value, error = parser(flag, raw_value)
            if error:
                return None, {}, f"{usage}\n  error: {error}"
            if keyword == "max_output_chars" and legacy_max_chars is not None:
                return None, {}, f"{usage}\n  error: provide either --max-chars or positional chars, not both."
            duplicate_error = duplicate_option_error(kwargs, keyword, flag, usage)
            if duplicate_error:
                return None, {}, duplicate_error
            kwargs[keyword] = int(value)
            continue
        if part.startswith("--"):
            return None, {}, f"{usage}\n  error: Unknown option: {part}"
        if process_id is None:
            process_id = part
            index += 1
            continue
        if legacy_max_chars is None:
            if "max_output_chars" in kwargs:
                return None, {}, f"{usage}\n  error: provide either --max-chars or positional chars, not both."
            value, error = parse_interactive_max_chars_option("[chars]", part)
            if error:
                return None, {}, f"{usage}\n  error: invalid max chars: {part}"
            legacy_max_chars = int(value)
            kwargs["max_output_chars"] = legacy_max_chars
            index += 1
            continue
        return None, {}, usage
    if process_id is None:
        return None, {}, f"{usage}\n  error: process id is required."
    return process_id, kwargs, None
