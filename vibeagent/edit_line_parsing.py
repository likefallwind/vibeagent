from __future__ import annotations

import shlex

from .process_commands import decode_stdin_escapes


def parse_replace_lines_argument(
    argument: str | None,
    *,
    path: str | None = None,
    start_line: int | None = None,
    end_line: int | None = None,
    content: str | None = None,
    usage: str,
) -> tuple[str, int, int, str]:
    if any(value is not None for value in (path, start_line, end_line, content)):
        if not path or not path.strip():
            raise ValueError(f"{usage} requires a non-empty path.")
        if start_line is None or end_line is None:
            raise ValueError(f"{usage} requires start and end line numbers.")
        if content is None:
            raise ValueError(f"{usage} requires text.")
        return path.strip(), validate_line_number(start_line, "start"), validate_line_range(start_line, end_line), decode_stdin_escapes(content)

    if not argument or not argument.strip():
        raise ValueError(f"{usage} requires path, start, end, and text.")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if len(parts) != 4:
        raise ValueError("expected path, start, end, and text.")
    parsed_path, raw_start, raw_end, raw_content = parts
    if not parsed_path.strip():
        raise ValueError(f"{usage} requires a non-empty path.")
    parsed_start = parse_line_number(raw_start, "start")
    parsed_end = parse_line_number(raw_end, "end")
    if parsed_end < parsed_start:
        raise ValueError("end must be greater than or equal to start.")
    return parsed_path, parsed_start, parsed_end, decode_stdin_escapes(raw_content)


def parse_insert_lines_argument(
    argument: str | None,
    *,
    path: str | None = None,
    line: int | None = None,
    content: str | None = None,
    usage: str,
) -> tuple[str, int, str]:
    if any(value is not None for value in (path, line, content)):
        if not path or not path.strip():
            raise ValueError(f"{usage} requires a non-empty path.")
        if line is None:
            raise ValueError(f"{usage} requires a line number.")
        parsed_content = decode_stdin_escapes(content or "")
        if parsed_content == "":
            raise ValueError(f"{usage} requires non-empty text.")
        return path.strip(), validate_line_number(line, "line"), parsed_content

    if not argument or not argument.strip():
        raise ValueError(f"{usage} requires path, line, and text.")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if len(parts) != 3:
        raise ValueError("expected path, line, and text.")
    parsed_path, raw_line, raw_content = parts
    if not parsed_path.strip():
        raise ValueError(f"{usage} requires a non-empty path.")
    parsed_content = decode_stdin_escapes(raw_content)
    if parsed_content == "":
        raise ValueError(f"{usage} requires non-empty text.")
    return parsed_path, parse_line_number(raw_line, "line"), parsed_content


def parse_append_file_argument(
    argument: str | None,
    *,
    path: str | None = None,
    content: str | None = None,
    usage: str,
) -> tuple[str, str]:
    if path is not None or content is not None:
        if not path or not path.strip():
            raise ValueError(f"{usage} requires a non-empty path.")
        parsed_content = decode_stdin_escapes(content or "")
        if parsed_content == "":
            raise ValueError(f"{usage} requires non-empty text.")
        return path.strip(), parsed_content

    if not argument or not argument.strip():
        raise ValueError(f"{usage} requires path and text.")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if len(parts) != 2:
        raise ValueError("expected path and text.")
    parsed_path, raw_content = parts
    if not parsed_path.strip():
        raise ValueError(f"{usage} requires a non-empty path.")
    parsed_content = decode_stdin_escapes(raw_content)
    if parsed_content == "":
        raise ValueError(f"{usage} requires non-empty text.")
    return parsed_path, parsed_content


def parse_line_number(value: str, name: str) -> int:
    if not value.isdigit():
        raise ValueError(f"{name} must be a positive integer.")
    return validate_line_number(int(value), name)


def validate_line_number(value: object, name: str) -> int:
    if isinstance(value, str):
        return parse_line_number(value, name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be a positive integer.")
    if value < 1:
        raise ValueError(f"{name} must be a positive integer.")
    return value


def validate_line_range(start_line: object, end_line: object) -> int:
    parsed_start = validate_line_number(start_line, "start")
    parsed_end = validate_line_number(end_line, "end")
    if parsed_end < parsed_start:
        raise ValueError("end must be greater than or equal to start.")
    return parsed_end
