from __future__ import annotations

from typing import Any

from .action_parsing_git_fields import (
    parse_git_branch_create,
    parse_git_commit_message,
    parse_git_path_list,
    parse_git_stash_options,
    parse_git_stash_ref,
    parse_optional_git_remote,
)
from .action_parsing_helpers import ActionParseError, parse_optional_positive_int
from .action_parsing_git_read import GIT_READ_ACTION_TYPES, parse_git_read_action
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
    EnterWorktreeAction,
    ExitWorktreeAction,
    GitCommitAction,
    GitFetchAction,
    GitPullAction,
    GitPushAction,
    GitRestoreAction,
    GitStageAction,
    GitStashAction,
    GitStashApplyAction,
    GitStashDropAction,
    GitStashesAction,
    GitSwitchAction,
    GitUnstageAction,
)


GIT_ACTION_TYPES = GIT_READ_ACTION_TYPES | {
    "enter_worktree",
    "exit_worktree",
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


def parse_git_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in GIT_ACTION_TYPES:
        return None

    if action_type == "enter_worktree":
        name = value.get("name")
        path = value.get("path")
        if name is not None and (not isinstance(name, str) or not name.strip()):
            raise ActionParseError("EnterWorktree name must be a non-empty string.", raw)
        if path is not None and (not isinstance(path, str) or not path.strip()):
            raise ActionParseError("EnterWorktree path must be a non-empty string.", raw)
        if name is not None and path is not None:
            raise ActionParseError("EnterWorktree accepts name or path, not both.", raw)
        return EnterWorktreeAction(
            type="enter_worktree",
            name=name.strip() if isinstance(name, str) else None,
            path=path.strip() if isinstance(path, str) else None,
        )

    if action_type == "exit_worktree":
        return ExitWorktreeAction(type="exit_worktree")

    read_action = parse_git_read_action(action_type, value, raw)
    if read_action is not None:
        return read_action

    if action_type == "check_git_fetch":
        return CheckGitFetchAction(
            type="check_git_fetch",
            remote=parse_optional_git_remote(value, raw, "check_git_fetch"),
        )

    if action_type == "git_fetch":
        return GitFetchAction(
            type="git_fetch",
            remote=parse_optional_git_remote(value, raw, "git_fetch"),
        )

    if action_type == "check_git_pull":
        return CheckGitPullAction(type="check_git_pull")

    if action_type == "git_pull":
        return GitPullAction(type="git_pull")

    if action_type == "check_git_push":
        return CheckGitPushAction(type="check_git_push")

    if action_type == "git_push":
        return GitPushAction(type="git_push")

    if action_type == "check_git_switch":
        branch, create = parse_git_branch_create(value, raw, "check_git_switch")
        return CheckGitSwitchAction(type="check_git_switch", branch=branch.strip(), create=create)

    if action_type == "git_switch":
        branch, create = parse_git_branch_create(value, raw, "git_switch")
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
        message, include_untracked = parse_git_stash_options(value, raw, "check_git_stash")
        return CheckGitStashAction(type="check_git_stash", message=message, include_untracked=include_untracked)

    if action_type == "git_stash":
        message, include_untracked = parse_git_stash_options(value, raw, "git_stash")
        return GitStashAction(type="git_stash", message=message, include_untracked=include_untracked)

    if action_type == "check_git_stash_apply":
        return CheckGitStashApplyAction(
            type="check_git_stash_apply",
            stash_ref=parse_git_stash_ref(value, raw, "check_git_stash_apply"),
        )

    if action_type == "git_stash_apply":
        return GitStashApplyAction(
            type="git_stash_apply",
            stash_ref=parse_git_stash_ref(value, raw, "git_stash_apply"),
        )

    if action_type == "check_git_stash_drop":
        return CheckGitStashDropAction(
            type="check_git_stash_drop",
            stash_ref=parse_git_stash_ref(value, raw, "check_git_stash_drop"),
        )

    if action_type == "git_stash_drop":
        return GitStashDropAction(
            type="git_stash_drop",
            stash_ref=parse_git_stash_ref(value, raw, "git_stash_drop"),
        )

    if action_type == "check_git_commit":
        return CheckGitCommitAction(
            type="check_git_commit",
            message=parse_git_commit_message(value, raw, "check_git_commit"),
        )

    if action_type == "git_commit":
        return GitCommitAction(
            type="git_commit",
            message=parse_git_commit_message(value, raw, "git_commit"),
        )

    raise AssertionError(f"Unhandled git action type: {action_type!r}")
