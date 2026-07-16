from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action
from .command_parsing import parse_local_path_args
from .git_local_report_helpers import (
    format_git_restore_report_text,
    git_restore_observation_report as _git_restore_observation_report,
    git_restore_unexpected_report as _git_restore_unexpected_report,
    git_restore_usage_report as _git_restore_usage_report,
    validate_git_restore_max_diff_chars as _validate_git_restore_max_diff_chars,
)
from .local_command_workspace import local_command_workspace
from .types import CheckGitRestoreAction, GitRestoreAction


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


def get_check_restore_text(project_root: str | Path = ".", argument: str | list[str] | None = None, max_diff_chars: int = 12_000) -> str:
    get_report = _git_command_function("get_check_restore_report", get_check_restore_report)
    format_report = _git_command_function("format_git_restore_report_text", format_git_restore_report_text)
    return format_report("Check restore", get_report(project_root, argument, max_diff_chars=max_diff_chars))


def get_check_restore_report(project_root: str | Path = ".", argument: str | list[str] | None = None, max_diff_chars: int = 12_000) -> dict[str, object]:
    _validate_git_restore_max_diff_chars(max_diff_chars)
    usage = "/check-restore <path...>"
    root = Path(project_root).resolve()
    try:
        paths = parse_local_path_args(argument, max_paths=100)
    except ValueError as error:
        return _git_restore_usage_report(root, usage, str(error), max_diff_chars)
    if not paths:
        return _git_restore_usage_report(root, usage, "path is required.", max_diff_chars)

    workspace = local_command_workspace(root, "local-check-restore")
    observation = _execute_action(
        workspace,
        CheckGitRestoreAction(type="check_git_restore", paths=paths),
    )
    if observation.kind != "check_git_restore":
        return _git_restore_unexpected_report(root, paths, f"Unexpected observation: {observation.kind}", max_diff_chars)
    return _git_restore_observation_report(root, observation, max_diff_chars)


def get_restore_text(project_root: str | Path = ".", argument: str | list[str] | None = None, max_diff_chars: int = 12_000) -> str:
    get_report = _git_command_function("get_restore_report", get_restore_report)
    format_report = _git_command_function("format_git_restore_report_text", format_git_restore_report_text)
    return format_report("Restore", get_report(project_root, argument, max_diff_chars=max_diff_chars))


def get_restore_report(project_root: str | Path = ".", argument: str | list[str] | None = None, max_diff_chars: int = 12_000) -> dict[str, object]:
    _validate_git_restore_max_diff_chars(max_diff_chars)
    usage = "/restore <path...>"
    root = Path(project_root).resolve()
    try:
        paths = parse_local_path_args(argument, max_paths=100)
    except ValueError as error:
        return _git_restore_usage_report(root, usage, str(error), max_diff_chars)
    if not paths:
        return _git_restore_usage_report(root, usage, "path is required.", max_diff_chars)

    workspace = local_command_workspace(root, "local-restore")
    observation = _execute_action(
        workspace,
        GitRestoreAction(type="git_restore", paths=paths),
    )
    if observation.kind != "git_restore":
        return _git_restore_unexpected_report(root, paths, f"Unexpected observation: {observation.kind}", max_diff_chars)
    return _git_restore_observation_report(root, observation, max_diff_chars)
