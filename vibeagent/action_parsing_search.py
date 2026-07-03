from __future__ import annotations

from typing import Any

from .action_parsing_helpers import ActionParseError, parse_nonnegative_int, parse_optional_positive_int
from .types import FindFilesAction, GlobAction, SearchAction, SearchContextsAction


SEARCH_ACTION_TYPES = {
    "search",
    "search_contexts",
    "find_files",
    "glob",
}


def parse_search_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in SEARCH_ACTION_TYPES:
        return None

    if action_type == "search":
        query = value.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ActionParseError("search action requires a non-empty query.", raw)
        path = value.get("path")
        regex = value.get("regex", False)
        case_sensitive = value.get("case_sensitive", True)
        max_matches = value.get("max_matches", 80)
        context_lines = value.get("context_lines", 0)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("search action path must be a string when provided.", raw)
        if type(regex) is not bool:
            raise ActionParseError("search action regex must be a boolean when provided.", raw)
        if type(case_sensitive) is not bool:
            raise ActionParseError("search action case_sensitive must be a boolean when provided.", raw)
        max_matches = parse_optional_positive_int(max_matches, "max_matches", raw, maximum=500) or 80
        context_lines = parse_nonnegative_int(context_lines, "context_lines", raw, maximum=5)
        return SearchAction(
            type="search",
            query=query,
            path=path,
            regex=regex,
            case_sensitive=case_sensitive,
            max_matches=max_matches,
            context_lines=context_lines,
        )

    if action_type == "search_contexts":
        query = value.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ActionParseError("search_contexts action requires a non-empty query.", raw)
        path = value.get("path")
        regex = value.get("regex", False)
        case_sensitive = value.get("case_sensitive", True)
        max_matches = value.get("max_matches", 20)
        context_lines = value.get("context_lines", 3)
        max_bytes_per_context = value.get("max_bytes_per_context", 20_000)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("search_contexts action path must be a string when provided.", raw)
        if type(regex) is not bool:
            raise ActionParseError("search_contexts action regex must be a boolean when provided.", raw)
        if type(case_sensitive) is not bool:
            raise ActionParseError("search_contexts action case_sensitive must be a boolean when provided.", raw)
        max_matches = parse_optional_positive_int(max_matches, "max_matches", raw, maximum=100) or 20
        context_lines = parse_nonnegative_int(context_lines, "context_lines", raw, maximum=50)
        max_bytes_per_context = parse_optional_positive_int(max_bytes_per_context, "max_bytes_per_context", raw, maximum=200_000) or 20_000
        if max_bytes_per_context < 1000:
            raise ActionParseError("max_bytes_per_context must be at least 1000.", raw)
        return SearchContextsAction(
            type="search_contexts",
            query=query,
            path=path,
            regex=regex,
            case_sensitive=case_sensitive,
            max_matches=max_matches,
            context_lines=context_lines,
            max_bytes_per_context=max_bytes_per_context,
        )

    if action_type == "find_files":
        query = value.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ActionParseError("find_files action requires a non-empty query.", raw)
        normalized_query = query.strip()
        path = value.get("path")
        regex = value.get("regex", False)
        case_sensitive = value.get("case_sensitive", False)
        include_dirs = value.get("include_dirs", False)
        max_matches = value.get("max_matches", 100)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("find_files action path must be a string when provided.", raw)
        if type(regex) is not bool:
            raise ActionParseError("find_files action regex must be a boolean when provided.", raw)
        if type(case_sensitive) is not bool:
            raise ActionParseError("find_files action case_sensitive must be a boolean when provided.", raw)
        if type(include_dirs) is not bool:
            raise ActionParseError("find_files action include_dirs must be a boolean when provided.", raw)
        max_matches = parse_optional_positive_int(max_matches, "max_matches", raw, maximum=500) or 100
        return FindFilesAction(
            type="find_files",
            query=normalized_query,
            path=path,
            regex=regex,
            case_sensitive=case_sensitive,
            include_dirs=include_dirs,
            max_matches=max_matches,
        )

    if action_type == "glob":
        pattern = value.get("pattern")
        max_matches = value.get("max_matches", 200)
        include_dirs = value.get("include_dirs", False)
        if not isinstance(pattern, str) or not pattern.strip():
            raise ActionParseError("glob action requires a non-empty pattern.", raw)
        max_matches = parse_optional_positive_int(max_matches, "max_matches", raw, maximum=500) or 200
        if not isinstance(include_dirs, bool):
            raise ActionParseError("glob action include_dirs must be a boolean.", raw)
        return GlobAction(type="glob", pattern=pattern, max_matches=max_matches, include_dirs=include_dirs)

    raise AssertionError(f"Unhandled search action type: {action_type!r}")
