from __future__ import annotations

import shlex

from .process_commands import decode_stdin_escapes


def parse_regex_replace_argument(
    argument: str | None,
    *,
    path: str | None = None,
    pattern: str | None = None,
    replacement: str | None = None,
    count: int | str = 0,
    case_sensitive: bool = True,
    multiline: bool = False,
    max_replacements: int | str = 100,
    usage: str,
) -> dict[str, object]:
    if any(value is not None for value in (path, pattern, replacement)):
        if not path or not path.strip():
            raise ValueError(f"{usage} requires a non-empty path.")
        if not pattern:
            raise ValueError(f"{usage} requires a non-empty pattern.")
        if replacement is None:
            raise ValueError(f"{usage} requires replacement text.")
        return {
            "path": path.strip(),
            "pattern": pattern,
            "replacement": decode_stdin_escapes(replacement),
            "count": validate_nonnegative_int(count, "count", maximum=1000),
            "case_sensitive": bool(case_sensitive),
            "multiline": bool(multiline),
            "max_replacements": validate_positive_int(max_replacements, "max-replacements", maximum=1000),
        }

    if not argument or not argument.strip():
        raise ValueError(f"{usage} requires path, pattern, and replacement.")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error

    parsed_count = 0
    parsed_case_sensitive = True
    parsed_multiline = False
    parsed_max_replacements = 100
    positional: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--ignore-case":
            parsed_case_sensitive = False
            index += 1
        elif part == "--case-sensitive":
            parsed_case_sensitive = True
            index += 1
        elif part == "--multiline":
            parsed_multiline = True
            index += 1
        elif part == "--count":
            if index + 1 >= len(parts):
                raise ValueError("--count requires a value.")
            parsed_count = validate_nonnegative_int(parts[index + 1], "count", maximum=1000)
            index += 2
        elif part == "--max-replacements":
            if index + 1 >= len(parts):
                raise ValueError("--max-replacements requires a value.")
            parsed_max_replacements = validate_positive_int(parts[index + 1], "max-replacements", maximum=1000)
            index += 2
        elif part.startswith("-"):
            raise ValueError(f"unknown option: {part}")
        else:
            positional.append(part)
            index += 1
    if len(positional) != 3:
        raise ValueError("expected path, pattern, and replacement.")
    parsed_path, parsed_pattern, parsed_replacement = positional
    if not parsed_path.strip():
        raise ValueError(f"{usage} requires a non-empty path.")
    if not parsed_pattern:
        raise ValueError(f"{usage} requires a non-empty pattern.")
    return {
        "path": parsed_path,
        "pattern": parsed_pattern,
        "replacement": decode_stdin_escapes(parsed_replacement),
        "count": parsed_count,
        "case_sensitive": parsed_case_sensitive,
        "multiline": parsed_multiline,
        "max_replacements": parsed_max_replacements,
    }


def validate_nonnegative_int(value: object, name: str, *, maximum: int) -> int:
    if isinstance(value, str):
        if not value.isdigit():
            raise ValueError(f"{name} must be a non-negative integer.")
        parsed = int(value)
    elif isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be a non-negative integer.")
    else:
        parsed = value
    if parsed < 0:
        raise ValueError(f"{name} must be a non-negative integer.")
    if parsed > maximum:
        raise ValueError(f"{name} must be at most {maximum}.")
    return parsed


def validate_positive_int(value: object, name: str, *, maximum: int) -> int:
    parsed = validate_nonnegative_int(value, name, maximum=maximum)
    if parsed < 1:
        raise ValueError(f"{name} must be a positive integer.")
    return parsed
