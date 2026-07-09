from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import shlex
import sys

from .actions import execute_action as _default_execute_action
from .git_stash_report_helpers import (
    _clip_report,
    _empty_clip_report,
    _validate_git_stash_max_chars,
    format_git_stash_report_text,
)
from .types import CheckGitStashAction, GitStashAction
from .workspace_core import RunWorkspace


def _execute_action(*args: object, **kwargs: object) -> object:
    commands_module = sys.modules.get("vibeagent.git_commands")
    command_execute_action = getattr(commands_module, "execute_action", None) if commands_module is not None else None
    if command_execute_action is not None:
        return command_execute_action(*args, **kwargs)
    return _default_execute_action(*args, **kwargs)


def _git_command_function(name: str, default: Callable[..., object]) -> Callable[..., object]:
    commands_module = sys.modules.get("vibeagent.git_commands")
    candidate = getattr(commands_module, name, None) if commands_module is not None else None
    return candidate if callable(candidate) else default


def get_check_stash_text(project_root: str | Path = ".", argument: str | None = None, max_diff_chars: int = 12_000) -> str:
    get_report = _git_command_function("get_check_stash_report", get_check_stash_report)
    format_report = _git_command_function("format_git_stash_report_text", format_git_stash_report_text)
    return format_report("Check stash", get_report(project_root, argument, max_diff_chars=max_diff_chars))


def get_check_stash_report(project_root: str | Path = ".", argument: str | None = None, max_diff_chars: int = 12_000) -> dict[str, object]:
    _validate_git_stash_max_chars(max_diff_chars)
    root = Path(project_root).resolve()
    try:
        message, include_untracked = parse_stash_argument(argument)
    except ValueError as error:
        return _git_stash_usage_report(root, "/check-stash [--include-untracked] [message]", str(error), max_diff_chars)

    workspace = RunWorkspace(root=root, run_id="local-check-stash", session_dir=root / ".vibeagent" / "sessions" / "local-check-stash")
    observation = _execute_action(
        workspace,
        CheckGitStashAction(type="check_git_stash", message=message, include_untracked=include_untracked),
    )
    if observation.kind != "check_git_stash":
        return _git_stash_unexpected_report(root, f"Unexpected observation: {observation.kind}", max_diff_chars)
    return _git_stash_observation_report(root, observation, "", max_diff_chars)


def get_stash_text(project_root: str | Path = ".", argument: str | None = None, max_diff_chars: int = 12_000) -> str:
    get_report = _git_command_function("get_stash_report", get_stash_report)
    format_report = _git_command_function("format_git_stash_report_text", format_git_stash_report_text)
    return format_report("Stash", get_report(project_root, argument, max_diff_chars=max_diff_chars))


def get_stash_report(project_root: str | Path = ".", argument: str | None = None, max_diff_chars: int = 12_000) -> dict[str, object]:
    _validate_git_stash_max_chars(max_diff_chars)
    root = Path(project_root).resolve()
    try:
        message, include_untracked = parse_stash_argument(argument)
    except ValueError as error:
        return _git_stash_usage_report(root, "/stash [--include-untracked] [message]", str(error), max_diff_chars)

    workspace = RunWorkspace(root=root, run_id="local-stash", session_dir=root / ".vibeagent" / "sessions" / "local-stash")
    observation = _execute_action(
        workspace,
        GitStashAction(type="git_stash", message=message, include_untracked=include_untracked),
    )
    if observation.kind != "git_stash":
        return _git_stash_unexpected_report(root, f"Unexpected observation: {observation.kind}", max_diff_chars)
    return _git_stash_observation_report(root, observation, observation.stash_ref, max_diff_chars)


def parse_stash_argument(argument: str | None) -> tuple[str | None, bool]:
    if not argument or not argument.strip():
        return None, False
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    include_untracked = False
    message_parts: list[str] = []
    for part in parts:
        if part in {"--include-untracked", "-u"}:
            include_untracked = True
        elif part.startswith("-"):
            raise ValueError(f"unsupported option: {part}")
        else:
            message_parts.append(part)
    message = " ".join(message_parts).strip() or None
    return message, include_untracked


def _git_stash_usage_report(root: Path, usage: str, error: str, max_diff_chars: int) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "messageText": "",
        "includeUntracked": False,
        "stashRef": "",
        "statusText": "",
        "diff": _empty_clip_report(max_diff_chars),
        "message": f"Usage: {usage}\nError: {error}",
    }


def _git_stash_unexpected_report(root: Path, message: str, max_diff_chars: int) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "messageText": "",
        "includeUntracked": False,
        "stashRef": "",
        "statusText": "",
        "diff": _empty_clip_report(max_diff_chars),
        "message": message,
    }


def _git_stash_observation_report(root: Path, observation: object, stash_ref: str, max_diff_chars: int) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": bool(getattr(observation, "ok")),
        "messageText": str(getattr(observation, "message_text")),
        "includeUntracked": bool(getattr(observation, "include_untracked")),
        "stashRef": stash_ref,
        "statusText": str(getattr(observation, "status")),
        "diff": _clip_report(str(getattr(observation, "diff")), max_diff_chars),
        "message": str(getattr(observation, "message")),
    }
