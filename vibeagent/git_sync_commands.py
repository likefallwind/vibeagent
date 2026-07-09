from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import shlex
import sys

from .actions import execute_action as _default_execute_action
from .git_sync_report_helpers import (
    format_git_fetch_preview_text,
    format_git_fetch_report_text,
    format_git_fetch_text,
    format_git_pull_push_preview_text,
    format_git_pull_report_text,
    format_git_pull_text,
    format_git_push_report_text,
    format_git_push_text,
    format_git_sync_preview_report_text,
    git_fetch_unexpected_report as _git_fetch_unexpected_report,
    git_fetch_usage_report as _git_fetch_usage_report,
    git_sync_preview_observation_report as _git_sync_preview_observation_report,
    git_sync_unexpected_report as _git_sync_unexpected_report,
)
from .types import CheckGitFetchAction, CheckGitPullAction, CheckGitPushAction, GitFetchAction, GitPullAction, GitPushAction
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


def get_check_fetch_text(project_root: str | Path = ".", argument: str | None = None) -> str:
    get_report = _git_command_function("get_check_fetch_report", get_check_fetch_report)
    format_report = _git_command_function("format_git_fetch_report_text", format_git_fetch_report_text)
    return format_report("Check fetch", get_report(project_root, argument))


def get_check_fetch_report(project_root: str | Path = ".", argument: str | None = None) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        remote = parse_optional_remote_argument(argument)
    except ValueError as error:
        return _git_fetch_usage_report(root, "/check-fetch [remote]", str(error))
    workspace = RunWorkspace(root=root, run_id="local-check-fetch", session_dir=root / ".vibeagent" / "sessions" / "local-check-fetch")
    observation = _execute_action(workspace, CheckGitFetchAction(type="check_git_fetch", remote=remote))
    if observation.kind != "check_git_fetch":
        return _git_fetch_unexpected_report(root, f"Unexpected observation: {observation.kind}")
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "remote": observation.remote,
        "remoteUrl": observation.remote_url,
        "branch": observation.branch,
        "upstream": observation.upstream,
        "ahead": observation.ahead,
        "behind": observation.behind,
        "message": observation.message,
    }


def get_fetch_text(project_root: str | Path = ".", argument: str | None = None) -> str:
    get_report = _git_command_function("get_fetch_report", get_fetch_report)
    format_report = _git_command_function("format_git_fetch_report_text", format_git_fetch_report_text)
    return format_report("Fetch", get_report(project_root, argument))


def get_fetch_report(project_root: str | Path = ".", argument: str | None = None) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        remote = parse_optional_remote_argument(argument)
    except ValueError as error:
        return _git_fetch_usage_report(root, "/fetch [remote]", str(error))
    workspace = RunWorkspace(root=root, run_id="local-fetch", session_dir=root / ".vibeagent" / "sessions" / "local-fetch")
    observation = _execute_action(workspace, GitFetchAction(type="git_fetch", remote=remote))
    if observation.kind != "git_fetch":
        return _git_fetch_unexpected_report(root, f"Unexpected observation: {observation.kind}")
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "remote": observation.remote,
        "remoteUrl": observation.remote_url,
        "branch": observation.branch,
        "upstream": observation.upstream,
        "aheadBefore": observation.ahead_before,
        "behindBefore": observation.behind_before,
        "aheadAfter": observation.ahead_after,
        "behindAfter": observation.behind_after,
        "message": observation.message,
    }


def get_check_pull_text(project_root: str | Path = ".") -> str:
    get_report = _git_command_function("get_check_pull_report", get_check_pull_report)
    format_report = _git_command_function("format_git_sync_preview_report_text", format_git_sync_preview_report_text)
    return format_report("Check pull", get_report(project_root))


def get_check_pull_report(project_root: str | Path = ".") -> dict[str, object]:
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-check-pull", session_dir=root / ".vibeagent" / "sessions" / "local-check-pull")
    observation = _execute_action(workspace, CheckGitPullAction(type="check_git_pull"))
    if observation.kind != "check_git_pull":
        return _git_sync_unexpected_report(root, f"Unexpected observation: {observation.kind}")
    return _git_sync_preview_observation_report(root, observation)


def get_pull_text(project_root: str | Path = ".") -> str:
    get_report = _git_command_function("get_pull_report", get_pull_report)
    format_report = _git_command_function("format_git_pull_report_text", format_git_pull_report_text)
    return format_report("Pull", get_report(project_root))


def get_pull_report(project_root: str | Path = ".") -> dict[str, object]:
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-pull", session_dir=root / ".vibeagent" / "sessions" / "local-pull")
    observation = _execute_action(workspace, GitPullAction(type="git_pull"))
    if observation.kind != "git_pull":
        return _git_sync_unexpected_report(root, f"Unexpected observation: {observation.kind}")
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "remote": observation.remote,
        "branch": observation.branch,
        "currentBefore": observation.current_before,
        "currentAfter": observation.current_after,
        "upstream": observation.upstream,
        "aheadBefore": observation.ahead_before,
        "behindBefore": observation.behind_before,
        "aheadAfter": observation.ahead_after,
        "behindAfter": observation.behind_after,
        "statusText": observation.status,
        "message": observation.message,
    }


def get_check_push_text(project_root: str | Path = ".") -> str:
    get_report = _git_command_function("get_check_push_report", get_check_push_report)
    format_report = _git_command_function("format_git_sync_preview_report_text", format_git_sync_preview_report_text)
    return format_report("Check push", get_report(project_root))


def get_check_push_report(project_root: str | Path = ".") -> dict[str, object]:
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-check-push", session_dir=root / ".vibeagent" / "sessions" / "local-check-push")
    observation = _execute_action(workspace, CheckGitPushAction(type="check_git_push"))
    if observation.kind != "check_git_push":
        return _git_sync_unexpected_report(root, f"Unexpected observation: {observation.kind}")
    return _git_sync_preview_observation_report(root, observation)


def get_push_text(project_root: str | Path = ".") -> str:
    get_report = _git_command_function("get_push_report", get_push_report)
    format_report = _git_command_function("format_git_push_report_text", format_git_push_report_text)
    return format_report("Push", get_report(project_root))


def get_push_report(project_root: str | Path = ".") -> dict[str, object]:
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-push", session_dir=root / ".vibeagent" / "sessions" / "local-push")
    observation = _execute_action(workspace, GitPushAction(type="git_push"))
    if observation.kind != "git_push":
        return _git_sync_unexpected_report(root, f"Unexpected observation: {observation.kind}")
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "remote": observation.remote,
        "branch": observation.branch,
        "current": observation.current,
        "upstream": observation.upstream,
        "aheadBefore": observation.ahead_before,
        "behindBefore": observation.behind_before,
        "statusText": observation.status,
        "message": observation.message,
    }


def parse_optional_remote_argument(argument: str | None) -> str | None:
    if not argument or not argument.strip():
        return None
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if len(parts) != 1:
        raise ValueError("expected at most one remote name.")
    remote = parts[0].strip()
    if not remote:
        raise ValueError("remote name must be non-empty.")
    return remote
