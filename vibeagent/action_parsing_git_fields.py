from __future__ import annotations

from typing import Any

from .action_parsing_helpers import ActionParseError, parse_path_list


def parse_git_path_list(value: dict[str, Any], raw: str, action_name: str) -> list[str]:
    paths = value.get("paths")
    if paths is None and "path" in value:
        paths = value.get("path")
    if isinstance(paths, str):
        paths = [paths]
    return parse_path_list(paths, raw, action_name, maximum=100)


def parse_optional_git_remote(value: dict[str, Any], raw: str, action_name: str) -> str | None:
    remote = value.get("remote")
    if remote is not None and not isinstance(remote, str):
        raise ActionParseError(f"{action_name} action remote must be a string when provided.", raw)
    if isinstance(remote, str) and not remote.strip():
        raise ActionParseError(f"{action_name} action remote must be non-empty when provided.", raw)
    return remote.strip() if isinstance(remote, str) else None


def parse_git_branch_create(value: dict[str, Any], raw: str, action_name: str) -> tuple[str, bool]:
    branch = value.get("branch")
    create = value.get("create", False)
    if not isinstance(branch, str) or not branch.strip():
        raise ActionParseError(f"{action_name} action requires a non-empty branch.", raw)
    if type(create) is not bool:
        raise ActionParseError(f"{action_name} action create must be a boolean when provided.", raw)
    return branch.strip(), create


def parse_git_stash_options(value: dict[str, Any], raw: str, action_name: str) -> tuple[str | None, bool]:
    message = value.get("message")
    include_untracked = value.get("include_untracked", False)
    if message is not None and not isinstance(message, str):
        raise ActionParseError(f"{action_name} action message must be a string when provided.", raw)
    if not isinstance(include_untracked, bool):
        raise ActionParseError(f"{action_name} action include_untracked must be a boolean when provided.", raw)
    return message, include_untracked


def parse_git_stash_ref(value: dict[str, Any], raw: str, action_name: str) -> str:
    stash_ref = value.get("stash_ref")
    if not isinstance(stash_ref, str) or not stash_ref.strip():
        raise ActionParseError(f"{action_name} action requires a non-empty stash_ref.", raw)
    return stash_ref.strip()


def parse_git_commit_message(value: dict[str, Any], raw: str, action_name: str) -> str:
    message = value.get("message")
    if not isinstance(message, str) or not message.strip():
        raise ActionParseError(f"{action_name} action requires a non-empty string message.", raw)
    if len(message.strip()) > 500:
        raise ActionParseError(f"{action_name} action message must be at most 500 characters.", raw)
    return message.strip()
