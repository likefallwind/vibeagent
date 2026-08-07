from __future__ import annotations

from typing import Any

from .action_parsing_helpers import ActionParseError, parse_optional_positive_int
from .types import ListFilesAction, ListTreeAction, RepoMapAction


READ_NAVIGATION_ACTION_TYPES = {"list_files", "list_tree", "repo_map"}


def parse_read_navigation_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type == "list_files":
        path = value.get("path")
        if path is not None and not isinstance(path, str):
            raise ActionParseError("list_files action path must be a string when provided.", raw)
        return ListFilesAction(type="list_files", path=path)

    if action_type == "list_tree":
        path = value.get("path")
        max_depth = value.get("max_depth", 3)
        max_entries = value.get("max_entries", 200)
        ignore = value.get("ignore", ())
        if path is not None and not isinstance(path, str):
            raise ActionParseError("list_tree action path must be a string when provided.", raw)
        if not isinstance(ignore, (list, tuple)):
            raise ActionParseError("list_tree action ignore must be a list of strings when provided.", raw)
        ignore_patterns = tuple(item.strip() for item in ignore if isinstance(item, str) and item.strip())
        if len(ignore_patterns) != len(ignore):
            raise ActionParseError("list_tree action ignore must be a list of non-empty strings.", raw)
        max_depth = parse_optional_positive_int(max_depth, "max_depth", raw, maximum=10) or 3
        max_entries = parse_optional_positive_int(max_entries, "max_entries", raw, maximum=1000) or 200
        return ListTreeAction(
            type="list_tree",
            path=path,
            max_depth=max_depth,
            max_entries=max_entries,
            ignore=ignore_patterns,
        )

    if action_type == "repo_map":
        path = value.get("path")
        max_depth = value.get("max_depth", 3)
        max_files = value.get("max_files", 80)
        max_symbols = value.get("max_symbols", 120)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("repo_map action path must be a string when provided.", raw)
        max_depth = parse_optional_positive_int(max_depth, "max_depth", raw, maximum=10) or 3
        max_files = parse_optional_positive_int(max_files, "max_files", raw, maximum=500) or 80
        max_symbols = parse_optional_positive_int(max_symbols, "max_symbols", raw, maximum=500) or 120
        return RepoMapAction(
            type="repo_map",
            path=path,
            max_depth=max_depth,
            max_files=max_files,
            max_symbols=max_symbols,
        )

    return None
