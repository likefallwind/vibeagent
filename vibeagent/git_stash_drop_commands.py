from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action
from .git_stash_report_helpers import (
    _clip_report,
    _empty_clip_report,
    _validate_git_stash_max_chars,
    format_git_stash_drop_report_text,
)
from .local_command_workspace import local_command_workspace
from .types import CheckGitStashDropAction, GitStashDropAction

CHECK_STASH_DROP_USAGE = "/check-stash-drop <stash@{N}>"
STASH_DROP_USAGE = "/stash-drop <stash@{N}>"
STASH_REF_REQUIRED_ERROR = "stash ref is required."


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


def get_check_stash_drop_text(project_root: str | Path = ".", argument: str | None = None, max_patch_chars: int = 12_000) -> str:
    get_report = _git_command_function("get_check_stash_drop_report", get_check_stash_drop_report)
    format_report = _git_command_function("format_git_stash_drop_report_text", format_git_stash_drop_report_text)
    return format_report("Check stash drop", get_report(project_root, argument, max_patch_chars=max_patch_chars))


def get_check_stash_drop_report(project_root: str | Path = ".", argument: str | None = None, max_patch_chars: int = 12_000) -> dict[str, object]:
    _validate_git_stash_max_chars(max_patch_chars)
    root = Path(project_root).resolve()
    stash_ref = (argument or "").strip()
    if not stash_ref:
        return _git_stash_drop_usage_report(root, CHECK_STASH_DROP_USAGE, STASH_REF_REQUIRED_ERROR, max_patch_chars)

    workspace = local_command_workspace(root, "local-check-stash-drop")
    observation = _execute_action(
        workspace,
        CheckGitStashDropAction(type="check_git_stash_drop", stash_ref=stash_ref),
    )
    if observation.kind != "check_git_stash_drop":
        return _git_stash_drop_unexpected_report(root, stash_ref, f"Unexpected observation: {observation.kind}", max_patch_chars)
    return _git_stash_drop_observation_report(root, observation, max_patch_chars)


def get_stash_drop_text(project_root: str | Path = ".", argument: str | None = None, max_patch_chars: int = 12_000) -> str:
    get_report = _git_command_function("get_stash_drop_report", get_stash_drop_report)
    format_report = _git_command_function("format_git_stash_drop_report_text", format_git_stash_drop_report_text)
    return format_report("Stash drop", get_report(project_root, argument, max_patch_chars=max_patch_chars))


def get_stash_drop_report(project_root: str | Path = ".", argument: str | None = None, max_patch_chars: int = 12_000) -> dict[str, object]:
    _validate_git_stash_max_chars(max_patch_chars)
    root = Path(project_root).resolve()
    stash_ref = (argument or "").strip()
    if not stash_ref:
        return _git_stash_drop_usage_report(root, STASH_DROP_USAGE, STASH_REF_REQUIRED_ERROR, max_patch_chars)

    workspace = local_command_workspace(root, "local-stash-drop")
    observation = _execute_action(
        workspace,
        GitStashDropAction(type="git_stash_drop", stash_ref=stash_ref),
    )
    if observation.kind != "git_stash_drop":
        return _git_stash_drop_unexpected_report(root, stash_ref, f"Unexpected observation: {observation.kind}", max_patch_chars)
    return _git_stash_drop_observation_report(root, observation, max_patch_chars)


def _git_stash_drop_usage_report(root: Path, usage: str, error: str, max_patch_chars: int) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "stashRef": "",
        "summary": "",
        "patch": _empty_clip_report(max_patch_chars),
        "message": f"Usage: {usage}\nError: {error}",
    }


def _git_stash_drop_unexpected_report(root: Path, stash_ref: str, message: str, max_patch_chars: int) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "stashRef": stash_ref,
        "summary": "",
        "patch": _empty_clip_report(max_patch_chars),
        "message": message,
    }


def _git_stash_drop_observation_report(root: Path, observation: object, max_patch_chars: int) -> dict[str, object]:
    report: dict[str, object] = {
        "projectRoot": str(root),
        "ok": bool(getattr(observation, "ok")),
        "stashRef": str(getattr(observation, "stash_ref")),
        "summary": str(getattr(observation, "summary")),
        "patch": _clip_report(str(getattr(observation, "patch")), max_patch_chars),
        "message": str(getattr(observation, "message")),
    }
    if hasattr(observation, "remaining_total"):
        report["remainingTotal"] = int(getattr(observation, "remaining_total"))
    return report
