from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import shlex
import sys

from .actions import execute_action as _default_execute_action
from .git_local_report_helpers import (
    format_git_switch_report_text,
    git_switch_unexpected_report as _git_switch_unexpected_report,
    git_switch_usage_report as _git_switch_usage_report,
)
from .local_command_workspace import local_command_workspace
from .types import CheckGitSwitchAction, GitSwitchAction


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


def get_check_switch_text(project_root: str | Path = ".", argument: str | None = None) -> str:
    get_report = _git_command_function("get_check_switch_report", get_check_switch_report)
    format_report = _git_command_function("format_git_switch_report_text", format_git_switch_report_text)
    return format_report("Check switch", get_report(project_root, argument))


def get_switch_text(project_root: str | Path = ".", argument: str | None = None) -> str:
    get_report = _git_command_function("get_switch_report", get_switch_report)
    format_report = _git_command_function("format_git_switch_report_text", format_git_switch_report_text)
    return format_report("Switch", get_report(project_root, argument))


def get_check_switch_report(project_root: str | Path = ".", argument: str | None = None) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        branch, create = parse_switch_argument(argument)
    except ValueError as error:
        return _git_switch_usage_report(root, "/check-switch [--create] <branch>", str(error))
    workspace = local_command_workspace(root, "local-check-switch")
    observation = _execute_action(
        workspace,
        CheckGitSwitchAction(type="check_git_switch", branch=branch, create=create),
    )
    if observation.kind != "check_git_switch":
        return _git_switch_unexpected_report(root, branch, create, f"Unexpected observation: {observation.kind}")
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "branch": observation.branch,
        "create": observation.create,
        "currentBefore": observation.current_before,
        "branchExists": observation.branch_exists,
        "worktreeClean": observation.worktree_clean,
        "statusText": observation.status,
        "message": observation.message,
    }


def get_switch_report(project_root: str | Path = ".", argument: str | None = None) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        branch, create = parse_switch_argument(argument)
    except ValueError as error:
        return _git_switch_usage_report(root, "/switch [--create] <branch>", str(error))
    workspace = local_command_workspace(root, "local-switch")
    observation = _execute_action(
        workspace,
        GitSwitchAction(type="git_switch", branch=branch, create=create),
    )
    if observation.kind != "git_switch":
        return _git_switch_unexpected_report(root, branch, create, f"Unexpected observation: {observation.kind}")
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "branch": observation.branch,
        "create": observation.create,
        "currentBefore": observation.current_before,
        "currentAfter": observation.current_after,
        "statusText": observation.status,
        "message": observation.message,
    }


def parse_switch_argument(argument: str | None) -> tuple[str, bool]:
    if not argument or not argument.strip():
        raise ValueError("branch is required.")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    create = False
    branches: list[str] = []
    for part in parts:
        if part in {"--create", "-c"}:
            create = True
        elif part.startswith("-"):
            raise ValueError(f"unsupported option: {part}")
        else:
            branches.append(part)
    if not branches:
        raise ValueError("branch is required.")
    if len(branches) > 1:
        raise ValueError("only one branch is allowed.")
    return branches[0], create
