from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .cli_git_read_local_flags import run_git_read_local_flag
from .cli_git_remote_local_flags import run_git_remote_local_flag
from .cli_git_stash_local_flags import run_git_stash_local_flag
from .cli_git_worktree_local_flags import run_git_worktree_local_flag


def run_git_local_flag(
    args: argparse.Namespace,
    project_root: Path | None,
    commands: dict[str, Any],
) -> tuple[str, dict[str, object]] | None:
    root = project_root or "."
    read_result = run_git_read_local_flag(args, project_root, commands)
    if read_result is not None:
        return read_result
    remote_result = run_git_remote_local_flag(args, project_root, commands)
    if remote_result is not None:
        return remote_result
    stash_result = run_git_stash_local_flag(args, project_root, commands)
    if stash_result is not None:
        return stash_result
    return run_git_worktree_local_flag(args, project_root, commands)


def run_interactive_git_command(command: Any, commands: dict[str, Any]) -> str | None:
    if command.type == "git_status":
        return commands["get_git_status_text"]()
    if command.type == "git_conflicts":
        return commands["get_git_conflicts_text"](argument=command.argument)
    if command.type == "git_info":
        return commands["get_git_info_text"]()
    if command.type == "branches":
        return commands["get_branches_text"]()
    if command.type == "log":
        return commands["get_log_text"](argument=command.argument)
    if command.type == "show":
        return commands["get_show_text"](argument=command.argument)
    if command.type == "blame":
        return commands["get_blame_text"](argument=command.argument)
    if command.type == "stashes":
        return commands["get_stashes_text"](argument=command.argument)
    if command.type == "check_fetch":
        return commands["get_check_fetch_text"](argument=command.argument)
    if command.type == "fetch":
        return commands["get_fetch_text"](argument=command.argument)
    if command.type == "check_pull":
        return commands["get_check_pull_text"]()
    if command.type == "pull":
        return commands["get_pull_text"]()
    if command.type == "check_push":
        return commands["get_check_push_text"]()
    if command.type == "push":
        return commands["get_push_text"]()
    if command.type == "check_stash":
        return commands["get_check_stash_text"](argument=command.argument)
    if command.type == "stash":
        return commands["get_stash_text"](argument=command.argument)
    if command.type == "check_stash_apply":
        return commands["get_check_stash_apply_text"](argument=command.argument)
    if command.type == "stash_apply":
        return commands["get_stash_apply_text"](argument=command.argument)
    if command.type == "check_stash_drop":
        return commands["get_check_stash_drop_text"](argument=command.argument)
    if command.type == "stash_drop":
        return commands["get_stash_drop_text"](argument=command.argument)
    if command.type == "check_stage":
        return commands["get_check_stage_text"](argument=command.argument)
    if command.type == "stage":
        return commands["get_stage_text"](argument=command.argument)
    if command.type == "check_unstage":
        return commands["get_check_unstage_text"](argument=command.argument)
    if command.type == "unstage":
        return commands["get_unstage_text"](argument=command.argument)
    if command.type == "check_commit":
        return commands["get_check_commit_text"](argument=command.argument)
    if command.type == "commit":
        return commands["get_commit_text"](argument=command.argument)
    if command.type == "check_restore":
        return commands["get_check_restore_text"](argument=command.argument)
    if command.type == "restore":
        return commands["get_restore_text"](argument=command.argument)
    if command.type == "check_switch":
        return commands["get_check_switch_text"](argument=command.argument)
    if command.type == "switch":
        return commands["get_switch_text"](argument=command.argument)
    return None
