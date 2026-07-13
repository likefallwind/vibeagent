from __future__ import annotations

from typing import Any

from .action_parsing_helpers import ActionParseError, parse_optional_nonnegative_int, parse_optional_positive_int


def parse_string_field(value: Any, raw: str, message: str) -> str:
    if not isinstance(value, str):
        raise ActionParseError(message, raw)
    return value


def parse_line_range(value: dict[str, Any], raw: str, action_type: str) -> tuple[str, int, int, str]:
    path = parse_string_field(value.get("path"), raw, f"{action_type} action requires a string path.")
    start_line = parse_optional_positive_int(value.get("start_line"), "start_line", raw, maximum=None)
    end_line = parse_optional_positive_int(value.get("end_line"), "end_line", raw, maximum=None)
    if start_line is None:
        raise ActionParseError(f"{action_type} action requires start_line.", raw)
    if end_line is None:
        raise ActionParseError(f"{action_type} action requires end_line.", raw)
    if end_line < start_line:
        raise ActionParseError("end_line must be greater than or equal to start_line.", raw)
    content = parse_string_field(value.get("content"), raw, f"{action_type} action requires string content.")
    return path, start_line, end_line, content


def parse_insert(value: dict[str, Any], raw: str, action_type: str) -> tuple[str, int, str]:
    path = parse_string_field(value.get("path"), raw, f"{action_type} action requires a string path.")
    line = parse_optional_positive_int(value.get("line"), "line", raw, maximum=None)
    if line is None:
        raise ActionParseError(f"{action_type} action requires line.", raw)
    content = value.get("content")
    if not isinstance(content, str) or content == "":
        raise ActionParseError(f"{action_type} action requires non-empty string content.", raw)
    return path, line, content


def parse_regex_replace(value: dict[str, Any], raw: str, action_type: str) -> tuple[str, str, str, int, bool, bool, int]:
    path = parse_string_field(value.get("path"), raw, f"{action_type} action requires a string path.")
    pattern = value.get("pattern")
    replacement = value.get("replacement")
    if not isinstance(pattern, str) or pattern == "":
        raise ActionParseError(f"{action_type} action requires a non-empty string pattern.", raw)
    if not isinstance(replacement, str):
        raise ActionParseError(f"{action_type} action requires string replacement.", raw)
    count = parse_optional_nonnegative_int(value.get("count", 0), "count", raw, maximum=1000)
    max_replacements = parse_optional_positive_int(value.get("max_replacements", 100), "max_replacements", raw, maximum=1000)
    case_sensitive = value.get("case_sensitive", True)
    multiline = value.get("multiline", False)
    if type(case_sensitive) is not bool:
        raise ActionParseError(f"{action_type} action case_sensitive must be a boolean.", raw)
    if type(multiline) is not bool:
        raise ActionParseError(f"{action_type} action multiline must be a boolean.", raw)
    return (
        path,
        pattern,
        replacement,
        count if count is not None else 0,
        case_sensitive,
        multiline,
        max_replacements if max_replacements is not None else 100,
    )


def parse_transfer(value: dict[str, Any], raw: str, action_type: str) -> tuple[str, str]:
    source = parse_string_field(value.get("source"), raw, f"{action_type} action requires string source.")
    destination = parse_string_field(value.get("destination"), raw, f"{action_type} action requires string destination.")
    return source, destination
