from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action
from .git_local_report_helpers import (
    format_git_commit_report_text,
    git_commit_observation_report as _git_commit_observation_report,
    git_commit_unexpected_report as _git_commit_unexpected_report,
    git_commit_usage_report as _git_commit_usage_report,
)
from .local_command_workspace import local_command_workspace
from .types import CheckGitCommitAction, GitCommitAction


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


def get_check_commit_text(project_root: str | Path = ".", argument: str | None = None) -> str:
    get_report = _git_command_function("get_check_commit_report", get_check_commit_report)
    format_report = _git_command_function("format_git_commit_report_text", format_git_commit_report_text)
    return format_report("Check commit", get_report(project_root, argument))


def get_check_commit_report(project_root: str | Path = ".", argument: str | None = None) -> dict[str, object]:
    message = (argument or "").strip()
    root = Path(project_root).resolve()
    if not message:
        return _git_commit_usage_report(root, "/check-commit <message>", "message is required.")

    workspace = local_command_workspace(root, "local-check-commit")
    observation = _execute_action(
        workspace,
        CheckGitCommitAction(type="check_git_commit", message=message),
    )
    if observation.kind != "check_git_commit":
        return _git_commit_unexpected_report(root, f"Unexpected observation: {observation.kind}")
    return _git_commit_observation_report(root, observation)


def get_commit_text(project_root: str | Path = ".", argument: str | None = None) -> str:
    get_report = _git_command_function("get_commit_report", get_commit_report)
    format_report = _git_command_function("format_git_commit_report_text", format_git_commit_report_text)
    return format_report("Commit", get_report(project_root, argument))


def get_commit_report(project_root: str | Path = ".", argument: str | None = None) -> dict[str, object]:
    message = (argument or "").strip()
    root = Path(project_root).resolve()
    if not message:
        return _git_commit_usage_report(root, "/commit <message>", "message is required.")

    workspace = local_command_workspace(root, "local-commit")
    observation = _execute_action(
        workspace,
        GitCommitAction(type="git_commit", message=message),
    )
    if observation.kind != "git_commit":
        return _git_commit_unexpected_report(root, f"Unexpected observation: {observation.kind}")
    return _git_commit_observation_report(root, observation)
