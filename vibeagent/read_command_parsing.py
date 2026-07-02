from __future__ import annotations

import shlex

from .command_parsing import parse_local_path_args
from .types import ReadFileContextItem, ReadFileRangeItem


def serialize_read_result(item: object) -> dict[str, object]:
    return {
        "path": str(getattr(item, "path", "")),
        "ok": bool(getattr(item, "ok", False)),
        "content": str(getattr(item, "content", "")),
        "totalBytes": getattr(item, "total_bytes", None),
        "maxBytes": getattr(item, "max_bytes", None),
        "truncated": bool(getattr(item, "truncated", False)),
        "showLineNumbers": bool(getattr(item, "show_line_numbers", False)),
        "message": str(getattr(item, "message", "")),
    }


def serialize_context_result(item: object) -> dict[str, object]:
    return {
        "path": str(getattr(item, "path", "")),
        "line": getattr(item, "line", None),
        "ok": bool(getattr(item, "ok", False)),
        "content": str(getattr(item, "content", "")),
        "startLine": getattr(item, "start_line", None),
        "endLine": getattr(item, "end_line", None),
        "contextLines": getattr(item, "context_lines", None),
        "targetLineExists": bool(getattr(item, "target_line_exists", False)),
        "lineCount": getattr(item, "line_count", 0),
        "totalLines": getattr(item, "total_lines", None),
        "maxBytes": getattr(item, "max_bytes", None),
        "truncated": bool(getattr(item, "truncated", False)),
        "message": str(getattr(item, "message", "")),
    }


def serialize_read_range_result(item: object) -> dict[str, object]:
    start_line = int(getattr(item, "start_line", 0))
    line_count = int(getattr(item, "line_count", 0))
    return {
        "path": str(getattr(item, "path", "")),
        "startLine": start_line,
        "lineCount": line_count,
        "endLine": start_line + line_count - 1 if line_count > 0 else None,
        "ok": bool(getattr(item, "ok", False)),
        "content": str(getattr(item, "content", "")),
        "totalBytes": getattr(item, "total_bytes", None),
        "maxBytes": getattr(item, "max_bytes", None),
        "truncated": bool(getattr(item, "truncated", False)),
        "message": str(getattr(item, "message", "")),
    }


def parse_tail_request(argument: str | None, line_count: int | None = None) -> tuple[str | None, int]:
    if line_count is not None:
        if line_count < 1:
            raise ValueError("lines must be at least 1.")
        if line_count > 1000:
            raise ValueError("lines must be at most 1000.")

    if argument is None or not argument.strip():
        return None, line_count or 80

    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if not parts:
        return None, line_count or 80
    if len(parts) > 2:
        raise ValueError("expected a path and optional line count.")
    if len(parts) == 2:
        if line_count is not None:
            raise ValueError("line count was provided twice.")
        try:
            parsed_count = int(parts[1])
        except ValueError as error:
            raise ValueError("lines must be an integer.") from error
        if parsed_count < 1:
            raise ValueError("lines must be at least 1.")
        if parsed_count > 1000:
            raise ValueError("lines must be at most 1000.")
        return parts[0], parsed_count
    return parts[0], line_count or 80


def parse_around_request(argument: str | None, context_lines: int | None = None) -> tuple[str | None, int | None, int]:
    if context_lines is not None:
        if context_lines < 0:
            raise ValueError("context-lines must be at least 0.")
        if context_lines > 500:
            raise ValueError("context-lines must be at most 500.")

    if argument is None or not argument.strip():
        return None, None, context_lines if context_lines is not None else 20

    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if not parts:
        return None, None, context_lines if context_lines is not None else 20
    if len(parts) not in {2, 3}:
        raise ValueError("expected a path, line, and optional context line count.")
    try:
        line = int(parts[1])
    except ValueError as error:
        raise ValueError("line must be an integer.") from error
    if line < 1:
        raise ValueError("line must be at least 1.")

    selected_context = context_lines
    if len(parts) == 3:
        if context_lines is not None:
            raise ValueError("context line count was provided twice.")
        try:
            selected_context = int(parts[2])
        except ValueError as error:
            raise ValueError("context-lines must be an integer.") from error
        if selected_context < 0:
            raise ValueError("context-lines must be at least 0.")
        if selected_context > 500:
            raise ValueError("context-lines must be at most 500.")
    return parts[0], line, selected_context if selected_context is not None else 20


def parse_around_many_argument(argument: str | list[str] | None) -> list[ReadFileContextItem]:
    if argument is None:
        return []
    if isinstance(argument, list):
        specs = [item.strip() for item in argument if item.strip()]
    else:
        try:
            specs = shlex.split(argument)
        except ValueError as error:
            raise ValueError(str(error)) from error
    if len(specs) > 20:
        raise ValueError("expected at most 20 contexts.")

    contexts: list[ReadFileContextItem] = []
    for spec in specs:
        path, line, context_lines = parse_around_many_spec(spec)
        contexts.append(ReadFileContextItem(path=path, line=line, context_lines=context_lines))
    return contexts


def parse_around_many_spec(spec: str) -> tuple[str, int, int]:
    parts = spec.rsplit(":", 2)
    if len(parts) < 2:
        raise ValueError(f"invalid context spec: {spec}")
    if len(parts) == 2:
        path, line_text = parts
        context_text = None
    else:
        path, line_text, context_text = parts
    if not path:
        raise ValueError(f"invalid context spec: {spec}")
    try:
        line = int(line_text)
    except ValueError as error:
        raise ValueError(f"invalid line in context spec: {spec}") from error
    if line < 1:
        raise ValueError("line must be at least 1.")
    if context_text is None or context_text == "":
        return path, line, 20
    try:
        context_lines = int(context_text)
    except ValueError as error:
        raise ValueError(f"invalid context line count in context spec: {spec}") from error
    if context_lines < 0:
        raise ValueError("context-lines must be at least 0.")
    if context_lines > 500:
        raise ValueError("context-lines must be at most 500.")
    return path, line, context_lines


def parse_read_ranges_argument(argument: str | list[str] | None) -> list[ReadFileRangeItem]:
    specs = parse_local_path_args(argument, max_paths=20)
    ranges: list[ReadFileRangeItem] = []
    for spec in specs:
        path, start_line, end_line = parse_read_range_spec(spec)
        ranges.append(ReadFileRangeItem(path=path, start_line=start_line, line_count=end_line - start_line + 1))
    return ranges


def parse_read_range_spec(spec: str) -> tuple[str, int, int]:
    parts = spec.rsplit(":", 2)
    if len(parts) < 2:
        raise ValueError(f"range must look like path:start[:end]: {spec}")
    path = parts[0].strip()
    if not path:
        raise ValueError(f"range path must be non-empty: {spec}")
    start_text = parts[1].strip()
    end_text = parts[2].strip() if len(parts) == 3 else start_text
    try:
        start_line = int(start_text)
    except ValueError as error:
        raise ValueError(f"invalid start line in range {spec}: {start_text}") from error
    try:
        end_line = int(end_text)
    except ValueError as error:
        raise ValueError(f"invalid end line in range {spec}: {end_text}") from error
    if start_line < 1:
        raise ValueError("start line must be at least 1.")
    if end_line < start_line:
        raise ValueError("end line must be greater than or equal to start line.")
    if end_line - start_line + 1 > 1000:
        raise ValueError("line range must contain at most 1000 lines.")
    return path, start_line, end_line


def parse_read_request(argument: str, line_range: str | None = None) -> tuple[str, int | None, int | None, str | None]:
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if not parts:
        raise ValueError("missing path.")
    if len(parts) > 2:
        raise ValueError("expected a path and optional start[:end] range.")
    if len(parts) == 2 and line_range:
        raise ValueError("line range was provided twice.")
    path = parts[0]
    selected_range = line_range or (parts[1] if len(parts) == 2 else None)
    if not selected_range:
        return path, None, None, None
    start_line, end_line = parse_read_line_range(selected_range)
    line_count = None if end_line is None else end_line - start_line + 1
    return path, start_line, line_count, selected_range


def parse_read_line_range(value: str) -> tuple[int, int | None]:
    raw = value.strip()
    if not raw:
        raise ValueError("line range must not be empty.")
    if ":" in raw:
        start_text, end_text = raw.split(":", 1)
    else:
        start_text, end_text = raw, ""
    try:
        start_line = int(start_text)
    except ValueError as error:
        raise ValueError(f"invalid start line: {start_text}") from error
    if start_line < 1:
        raise ValueError("start line must be at least 1.")
    if not end_text:
        return start_line, None
    try:
        end_line = int(end_text)
    except ValueError as error:
        raise ValueError(f"invalid end line: {end_text}") from error
    if end_line < start_line:
        raise ValueError("end line must be greater than or equal to start line.")
    if end_line - start_line + 1 > 1000:
        raise ValueError("line range must contain at most 1000 lines.")
    return start_line, end_line
