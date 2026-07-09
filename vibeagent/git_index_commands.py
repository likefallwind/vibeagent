from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action
from .command_parsing import parse_local_path_args
from .git_local_report_helpers import (
    format_git_index_report_text,
    git_index_observation_report as _git_index_observation_report,
    git_index_unexpected_report as _git_index_unexpected_report,
    git_index_usage_report as _git_index_usage_report,
)
from .types import CheckGitStageAction, CheckGitUnstageAction, GitStageAction, GitUnstageAction
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


def get_check_stage_text(project_root: str | Path = ".", argument: str | list[str] | None = None) -> str:
    get_report = _git_command_function("get_check_stage_report", get_check_stage_report)
    format_report = _git_command_function("format_git_index_report_text", format_git_index_report_text)
    return format_report("Check stage", get_report(project_root, argument))


def get_check_stage_report(project_root: str | Path = ".", argument: str | list[str] | None = None) -> dict[str, object]:
    usage = "/check-stage <path...>"
    root = Path(project_root).resolve()
    try:
        paths = parse_local_path_args(argument, max_paths=100)
    except ValueError as error:
        return _git_index_usage_report(root, usage, str(error))
    if not paths:
        return _git_index_usage_report(root, usage, "path is required.")

    workspace = RunWorkspace(root=root, run_id="local-check-stage", session_dir=root / ".vibeagent" / "sessions" / "local-check-stage")
    observation = _execute_action(
        workspace,
        CheckGitStageAction(type="check_git_stage", paths=paths),
    )
    if observation.kind != "check_git_stage":
        return _git_index_unexpected_report(root, paths, f"Unexpected observation: {observation.kind}")
    return _git_index_observation_report(root, observation)


def get_stage_text(project_root: str | Path = ".", argument: str | list[str] | None = None) -> str:
    get_report = _git_command_function("get_stage_report", get_stage_report)
    format_report = _git_command_function("format_git_index_report_text", format_git_index_report_text)
    return format_report("Stage", get_report(project_root, argument))


def get_stage_report(project_root: str | Path = ".", argument: str | list[str] | None = None) -> dict[str, object]:
    usage = "/stage <path...>"
    root = Path(project_root).resolve()
    try:
        paths = parse_local_path_args(argument, max_paths=100)
    except ValueError as error:
        return _git_index_usage_report(root, usage, str(error))
    if not paths:
        return _git_index_usage_report(root, usage, "path is required.")

    workspace = RunWorkspace(root=root, run_id="local-stage", session_dir=root / ".vibeagent" / "sessions" / "local-stage")
    observation = _execute_action(
        workspace,
        GitStageAction(type="git_stage", paths=paths),
    )
    if observation.kind != "git_stage":
        return _git_index_unexpected_report(root, paths, f"Unexpected observation: {observation.kind}")
    return _git_index_observation_report(root, observation)


def get_check_unstage_text(project_root: str | Path = ".", argument: str | list[str] | None = None) -> str:
    get_report = _git_command_function("get_check_unstage_report", get_check_unstage_report)
    format_report = _git_command_function("format_git_index_report_text", format_git_index_report_text)
    return format_report("Check unstage", get_report(project_root, argument))


def get_check_unstage_report(project_root: str | Path = ".", argument: str | list[str] | None = None) -> dict[str, object]:
    usage = "/check-unstage <path...>"
    root = Path(project_root).resolve()
    try:
        paths = parse_local_path_args(argument, max_paths=100)
    except ValueError as error:
        return _git_index_usage_report(root, usage, str(error))
    if not paths:
        return _git_index_usage_report(root, usage, "path is required.")

    workspace = RunWorkspace(root=root, run_id="local-check-unstage", session_dir=root / ".vibeagent" / "sessions" / "local-check-unstage")
    observation = _execute_action(
        workspace,
        CheckGitUnstageAction(type="check_git_unstage", paths=paths),
    )
    if observation.kind != "check_git_unstage":
        return _git_index_unexpected_report(root, paths, f"Unexpected observation: {observation.kind}")
    return _git_index_observation_report(root, observation)


def get_unstage_text(project_root: str | Path = ".", argument: str | list[str] | None = None) -> str:
    get_report = _git_command_function("get_unstage_report", get_unstage_report)
    format_report = _git_command_function("format_git_index_report_text", format_git_index_report_text)
    return format_report("Unstage", get_report(project_root, argument))


def get_unstage_report(project_root: str | Path = ".", argument: str | list[str] | None = None) -> dict[str, object]:
    usage = "/unstage <path...>"
    root = Path(project_root).resolve()
    try:
        paths = parse_local_path_args(argument, max_paths=100)
    except ValueError as error:
        return _git_index_usage_report(root, usage, str(error))
    if not paths:
        return _git_index_usage_report(root, usage, "path is required.")

    workspace = RunWorkspace(root=root, run_id="local-unstage", session_dir=root / ".vibeagent" / "sessions" / "local-unstage")
    observation = _execute_action(
        workspace,
        GitUnstageAction(type="git_unstage", paths=paths),
    )
    if observation.kind != "git_unstage":
        return _git_index_unexpected_report(root, paths, f"Unexpected observation: {observation.kind}")
    return _git_index_observation_report(root, observation)
