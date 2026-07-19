from __future__ import annotations

from typing import Any

from .action_parsing_scalars import ActionParseError, parse_nonnegative_int, parse_optional_positive_int
from .types import ReadFileContextItem, ReadFileRangeItem


def parse_read_file_contexts(value: Any, raw: str) -> list[ReadFileContextItem]:
    if not isinstance(value, list) or not value:
        raise ActionParseError("read_file_contexts action requires a non-empty contexts list.", raw)
    if len(value) > 20:
        raise ActionParseError("read_file_contexts action contexts must contain at most 20 items.", raw)

    contexts: list[ReadFileContextItem] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ActionParseError(f"read_file_contexts context {index} must be an object.", raw)
        path = item.get("path")
        if not isinstance(path, str) or not path.strip():
            raise ActionParseError(f"read_file_contexts context {index} requires a non-empty path.", raw)
        line = parse_optional_positive_int(item.get("line"), f"read_file_contexts context {index} line", raw, maximum=None)
        if line is None:
            raise ActionParseError(f"read_file_contexts context {index} requires line.", raw)
        context_lines = parse_nonnegative_int(
            item.get("context_lines", 20),
            f"read_file_contexts context {index} context_lines",
            raw,
            maximum=500,
        )
        contexts.append(ReadFileContextItem(path=path.strip(), line=line, context_lines=context_lines))
    return contexts


def parse_read_file_ranges(value: Any, raw: str) -> list[ReadFileRangeItem]:
    if not isinstance(value, list) or not value:
        raise ActionParseError("read_file_ranges action requires a non-empty ranges list.", raw)
    if len(value) > 20:
        raise ActionParseError("read_file_ranges action ranges must contain at most 20 items.", raw)

    ranges: list[ReadFileRangeItem] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ActionParseError(f"read_file_ranges range {index} must be an object.", raw)
        path = item.get("path")
        if not isinstance(path, str) or not path.strip():
            raise ActionParseError(f"read_file_ranges range {index} requires a non-empty path.", raw)
        start_line = parse_optional_positive_int(item.get("start_line"), f"read_file_ranges range {index} start_line", raw, maximum=None)
        if start_line is None:
            raise ActionParseError(f"read_file_ranges range {index} requires start_line.", raw)
        line_count = parse_optional_positive_int(item.get("line_count", 120), f"read_file_ranges range {index} line_count", raw, maximum=1000) or 120
        ranges.append(ReadFileRangeItem(path=path.strip(), start_line=start_line, line_count=line_count))
    return ranges
