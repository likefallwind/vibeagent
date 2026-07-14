from __future__ import annotations

from typing import Any

from .action_parsing_helpers import ActionParseError, parse_nonnegative_int, parse_optional_positive_int, parse_path_list
from .types import (
    CheckGitCommitAction,
    CheckGitFetchAction,
    CheckGitPullAction,
    CheckGitPushAction,
    CheckGitRestoreAction,
    CheckGitStageAction,
    CheckGitStashAction,
    CheckGitStashApplyAction,
    CheckGitStashDropAction,
    CheckGitSwitchAction,
    CheckGitUnstageAction,
    GitBranchesAction,
    GitChangesAction,
    GitCommitAction,
    GitConflictsAction,
    GitFetchAction,
    GitBlameAction,
    GitDiffAction,
    GitDiffContextsAction,
    GitDiffHunksAction,
    GitInfoAction,
    GitLogAction,
    GitPullAction,
    GitPushAction,
    GitRestoreAction,
    GitShowAction,
    GitStageAction,
    GitStashAction,
    GitStashApplyAction,
    GitStashDropAction,
    GitStashesAction,
    GitStatusAction,
    GitSwitchAction,
    GitUnstageAction,
)


GIT_ACTION_TYPES = {
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
    "check_git_fetch",
    "git_fetch",
    "check_git_pull",
    "git_pull",
    "check_git_push",
    "git_push",
    "check_git_switch",
    "git_switch",
    "check_git_stage",
    "git_stage",
    "check_git_unstage",
    "git_unstage",
    "check_git_restore",
    "git_restore",
    "git_stashes",
    "check_git_stash",
    "git_stash",
    "check_git_stash_apply",
    "git_stash_apply",
    "check_git_stash_drop",
    "git_stash_drop",
    "check_git_commit",
    "git_commit",
}


def parse_git_path_list(value: dict[str, Any], raw: str, action_name: str) -> list[str]:
    paths = value.get("paths")
    if paths is None and "path" in value:
        paths = value.get("path")
    if isinstance(paths, str):
        paths = [paths]
    return parse_path_list(paths, raw, action_name, maximum=100)


def parse_git_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in GIT_ACTION_TYPES:
        return None

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

    if action_type == "check_git_fetch":
        remote = value.get("remote")
        if remote is not None and not isinstance(remote, str):
            raise ActionParseError("check_git_fetch action remote must be a string when provided.", raw)
        if isinstance(remote, str) and not remote.strip():
            raise ActionParseError("check_git_fetch action remote must be non-empty when provided.", raw)
        return CheckGitFetchAction(type="check_git_fetch", remote=remote.strip() if isinstance(remote, str) else None)

    if action_type == "git_fetch":
        remote = value.get("remote")
        if remote is not None and not isinstance(remote, str):
            raise ActionParseError("git_fetch action remote must be a string when provided.", raw)
        if isinstance(remote, str) and not remote.strip():
            raise ActionParseError("git_fetch action remote must be non-empty when provided.", raw)
        return GitFetchAction(type="git_fetch", remote=remote.strip() if isinstance(remote, str) else None)

    if action_type == "check_git_pull":
        return CheckGitPullAction(type="check_git_pull")

    if action_type == "git_pull":
        return GitPullAction(type="git_pull")

    if action_type == "check_git_push":
        return CheckGitPushAction(type="check_git_push")

    if action_type == "git_push":
        return GitPushAction(type="git_push")

    if action_type == "check_git_switch":
        branch = value.get("branch")
        create = value.get("create", False)
        if not isinstance(branch, str) or not branch.strip():
            raise ActionParseError("check_git_switch action requires a non-empty branch.", raw)
        if type(create) is not bool:
            raise ActionParseError("check_git_switch action create must be a boolean when provided.", raw)
        return CheckGitSwitchAction(type="check_git_switch", branch=branch.strip(), create=create)

    if action_type == "git_switch":
        branch = value.get("branch")
        create = value.get("create", False)
        if not isinstance(branch, str) or not branch.strip():
            raise ActionParseError("git_switch action requires a non-empty branch.", raw)
        if type(create) is not bool:
            raise ActionParseError("git_switch action create must be a boolean when provided.", raw)
        return GitSwitchAction(type="git_switch", branch=branch.strip(), create=create)

    if action_type == "check_git_stage":
        return CheckGitStageAction(type="check_git_stage", paths=parse_git_path_list(value, raw, "check_git_stage"))

    if action_type == "git_stage":
        return GitStageAction(type="git_stage", paths=parse_git_path_list(value, raw, "git_stage"))

    if action_type == "check_git_unstage":
        return CheckGitUnstageAction(type="check_git_unstage", paths=parse_git_path_list(value, raw, "check_git_unstage"))

    if action_type == "git_unstage":
        return GitUnstageAction(type="git_unstage", paths=parse_git_path_list(value, raw, "git_unstage"))

    if action_type == "check_git_restore":
        return CheckGitRestoreAction(type="check_git_restore", paths=parse_git_path_list(value, raw, "check_git_restore"))

    if action_type == "git_restore":
        return GitRestoreAction(type="git_restore", paths=parse_git_path_list(value, raw, "git_restore"))

    if action_type == "git_stashes":
        max_entries = parse_optional_positive_int(value.get("max_entries", 20), "max_entries", raw, maximum=100) or 20
        return GitStashesAction(type="git_stashes", max_entries=max_entries)

    if action_type == "check_git_stash":
        message = value.get("message")
        include_untracked = value.get("include_untracked", False)
        if message is not None and not isinstance(message, str):
            raise ActionParseError("check_git_stash action message must be a string when provided.", raw)
        if not isinstance(include_untracked, bool):
            raise ActionParseError("check_git_stash action include_untracked must be a boolean when provided.", raw)
        return CheckGitStashAction(type="check_git_stash", message=message, include_untracked=include_untracked)

    if action_type == "git_stash":
        message = value.get("message")
        include_untracked = value.get("include_untracked", False)
        if message is not None and not isinstance(message, str):
            raise ActionParseError("git_stash action message must be a string when provided.", raw)
        if not isinstance(include_untracked, bool):
            raise ActionParseError("git_stash action include_untracked must be a boolean when provided.", raw)
        return GitStashAction(type="git_stash", message=message, include_untracked=include_untracked)

    if action_type == "check_git_stash_apply":
        stash_ref = value.get("stash_ref")
        if not isinstance(stash_ref, str) or not stash_ref.strip():
            raise ActionParseError("check_git_stash_apply action requires a non-empty stash_ref.", raw)
        return CheckGitStashApplyAction(type="check_git_stash_apply", stash_ref=stash_ref.strip())

    if action_type == "git_stash_apply":
        stash_ref = value.get("stash_ref")
        if not isinstance(stash_ref, str) or not stash_ref.strip():
            raise ActionParseError("git_stash_apply action requires a non-empty stash_ref.", raw)
        return GitStashApplyAction(type="git_stash_apply", stash_ref=stash_ref.strip())

    if action_type == "check_git_stash_drop":
        stash_ref = value.get("stash_ref")
        if not isinstance(stash_ref, str) or not stash_ref.strip():
            raise ActionParseError("check_git_stash_drop action requires a non-empty stash_ref.", raw)
        return CheckGitStashDropAction(type="check_git_stash_drop", stash_ref=stash_ref.strip())

    if action_type == "git_stash_drop":
        stash_ref = value.get("stash_ref")
        if not isinstance(stash_ref, str) or not stash_ref.strip():
            raise ActionParseError("git_stash_drop action requires a non-empty stash_ref.", raw)
        return GitStashDropAction(type="git_stash_drop", stash_ref=stash_ref.strip())

    if action_type == "check_git_commit":
        message = value.get("message")
        if not isinstance(message, str) or not message.strip():
            raise ActionParseError("check_git_commit action requires a non-empty string message.", raw)
        if len(message.strip()) > 500:
            raise ActionParseError("check_git_commit action message must be at most 500 characters.", raw)
        return CheckGitCommitAction(type="check_git_commit", message=message.strip())

    if action_type == "git_commit":
        message = value.get("message")
        if not isinstance(message, str) or not message.strip():
            raise ActionParseError("git_commit action requires a non-empty string message.", raw)
        if len(message.strip()) > 500:
            raise ActionParseError("git_commit action message must be at most 500 characters.", raw)
        return GitCommitAction(type="git_commit", message=message.strip())

    raise AssertionError(f"Unhandled git action type: {action_type!r}")
