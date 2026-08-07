from __future__ import annotations

from typing import Any

from .action_parsing_helpers import ActionParseError, parse_nonnegative_int, parse_optional_positive_int
from .types import (
    GitBlameAction,
    GitBranchesAction,
    GitChangesAction,
    GitConflictsAction,
    GitDiffAction,
    GitDiffContextsAction,
    GitDiffHunksAction,
    GitInfoAction,
    GitLogAction,
    GitShowAction,
    GitStatusAction,
)


GIT_READ_ACTION_TYPES = {
    "git_status",
    "git_conflicts",
    "git_info",
    "git_changes",
    "git_branches",
    "git_diff",
    "git_diff_hunks",
    "git_diff_contexts",
    "git_log",
    "git_show",
    "git_blame",
}


def parse_git_read_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type == "git_status":
        return GitStatusAction(type="git_status")

    if action_type == "git_conflicts":
        path = value.get("path")
        if path is not None and not isinstance(path, str):
            raise ActionParseError("git_conflicts action path must be a string when provided.", raw)
        max_markers = parse_optional_positive_int(value.get("max_markers", 200), "max_markers", raw, maximum=1000) or 200
        max_files = parse_optional_positive_int(value.get("max_files", 5000), "max_files", raw, maximum=10000) or 5000
        return GitConflictsAction(
            type="git_conflicts",
            path=path,
            max_markers=max_markers,
            max_files=max_files,
        )

    if action_type == "git_info":
        return GitInfoAction(type="git_info")

    if action_type == "git_changes":
        return GitChangesAction(type="git_changes")

    if action_type == "git_branches":
        max_branches = parse_optional_positive_int(value.get("max_branches", 100), "max_branches", raw, maximum=500) or 100
        return GitBranchesAction(type="git_branches", max_branches=max_branches)

    if action_type == "git_diff":
        path = value.get("path")
        staged = value.get("staged", False)
        max_output_chars = value.get("max_output_chars", 12000)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("git_diff action path must be a string when provided.", raw)
        if type(staged) is not bool:
            raise ActionParseError("git_diff action staged must be a boolean when provided.", raw)
        max_output_chars = parse_optional_positive_int(max_output_chars, "max_output_chars", raw, maximum=50000) or 12000
        if max_output_chars < 1000:
            raise ActionParseError("max_output_chars must be at least 1000.", raw)
        return GitDiffAction(type="git_diff", path=path, staged=staged, max_output_chars=max_output_chars)

    if action_type == "git_diff_hunks":
        path = value.get("path")
        staged = value.get("staged", False)
        max_hunks = value.get("max_hunks", 80)
        max_lines_per_hunk = value.get("max_lines_per_hunk", 80)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("git_diff_hunks action path must be a string when provided.", raw)
        if type(staged) is not bool:
            raise ActionParseError("git_diff_hunks action staged must be a boolean when provided.", raw)
        max_hunks = parse_optional_positive_int(max_hunks, "max_hunks", raw, maximum=500) or 80
        max_lines_per_hunk = parse_optional_positive_int(max_lines_per_hunk, "max_lines_per_hunk", raw, maximum=500) or 80
        return GitDiffHunksAction(
            type="git_diff_hunks",
            path=path,
            staged=staged,
            max_hunks=max_hunks,
            max_lines_per_hunk=max_lines_per_hunk,
        )

    if action_type == "git_diff_contexts":
        path = value.get("path")
        staged = value.get("staged", False)
        context_lines = value.get("context_lines", 5)
        max_hunks = value.get("max_hunks", 80)
        max_bytes_per_context = value.get("max_bytes_per_context", 20_000)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("git_diff_contexts action path must be a string when provided.", raw)
        if type(staged) is not bool:
            raise ActionParseError("git_diff_contexts action staged must be a boolean when provided.", raw)
        context_lines = parse_nonnegative_int(context_lines, "context_lines", raw, maximum=50)
        max_hunks = parse_optional_positive_int(max_hunks, "max_hunks", raw, maximum=500) or 80
        max_bytes_per_context = parse_optional_positive_int(max_bytes_per_context, "max_bytes_per_context", raw, maximum=200000) or 20_000
        if max_bytes_per_context < 1000:
            raise ActionParseError("max_bytes_per_context must be at least 1000.", raw)
        return GitDiffContextsAction(
            type="git_diff_contexts",
            path=path,
            staged=staged,
            context_lines=context_lines,
            max_hunks=max_hunks,
            max_bytes_per_context=max_bytes_per_context,
        )

    if action_type == "git_log":
        path = value.get("path")
        max_count = value.get("max_count", 5)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("git_log action path must be a string when provided.", raw)
        max_count = parse_optional_positive_int(max_count, "max_count", raw, maximum=50) or 5
        return GitLogAction(type="git_log", path=path, max_count=max_count)

    if action_type == "git_show":
        rev = value.get("rev", "HEAD")
        path = value.get("path")
        max_output_chars = value.get("max_output_chars", 12000)
        if not isinstance(rev, str) or not rev.strip():
            raise ActionParseError("git_show action rev must be a non-empty string.", raw)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("git_show action path must be a string when provided.", raw)
        max_output_chars = parse_optional_positive_int(max_output_chars, "max_output_chars", raw, maximum=50000) or 12000
        if max_output_chars < 1000:
            raise ActionParseError("max_output_chars must be at least 1000.", raw)
        return GitShowAction(type="git_show", rev=rev.strip(), path=path, max_output_chars=max_output_chars)

    if action_type == "git_blame":
        path = value.get("path")
        start_line = value.get("start_line")
        line_count = value.get("line_count")
        max_output_chars = value.get("max_output_chars", 12000)
        if not isinstance(path, str) or not path.strip():
            raise ActionParseError("git_blame action path must be a non-empty string.", raw)
        if start_line is not None:
            start_line = parse_optional_positive_int(start_line, "start_line", raw, maximum=None)
        if line_count is not None:
            line_count = parse_optional_positive_int(line_count, "line_count", raw, maximum=1000)
        max_output_chars = parse_optional_positive_int(max_output_chars, "max_output_chars", raw, maximum=50000) or 12000
        if max_output_chars < 1000:
            raise ActionParseError("max_output_chars must be at least 1000.", raw)
        return GitBlameAction(
            type="git_blame",
            path=path.strip(),
            start_line=start_line,
            line_count=line_count,
            max_output_chars=max_output_chars,
        )

    return None
