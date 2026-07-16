from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action
from .git_stash_report_helpers import (
    _clip_report,
    _empty_clip_report,
    _validate_git_stash_max_chars,
    format_git_stash_apply_report_text,
)
from .local_command_workspace import local_command_workspace
from .types import CheckGitStashApplyAction, GitStashApplyAction


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


def get_check_stash_apply_text(project_root: str | Path = ".", argument: str | None = None, max_patch_chars: int = 12_000) -> str:
    get_report = _git_command_function("get_check_stash_apply_report", get_check_stash_apply_report)
    format_report = _git_command_function("format_git_stash_apply_report_text", format_git_stash_apply_report_text)
    return format_report("Check stash apply", get_report(project_root, argument, max_patch_chars=max_patch_chars))


def get_check_stash_apply_report(project_root: str | Path = ".", argument: str | None = None, max_patch_chars: int = 12_000) -> dict[str, object]:
    _validate_git_stash_max_chars(max_patch_chars)
    root = Path(project_root).resolve()
    stash_ref = (argument or "").strip()
    if not stash_ref:
        return _git_stash_apply_usage_report(root, "/check-stash-apply <stash@{N}>", "stash ref is required.", max_patch_chars)

    workspace = local_command_workspace(root, "local-check-stash-apply")
    observation = _execute_action(
        workspace,
        CheckGitStashApplyAction(type="check_git_stash_apply", stash_ref=stash_ref),
    )
    if observation.kind != "check_git_stash_apply":
        return _git_stash_apply_unexpected_report(root, stash_ref, f"Unexpected observation: {observation.kind}", max_patch_chars)
    return _git_stash_apply_observation_report(root, observation, max_patch_chars)


def get_stash_apply_text(project_root: str | Path = ".", argument: str | None = None, max_patch_chars: int = 12_000) -> str:
    get_report = _git_command_function("get_stash_apply_report", get_stash_apply_report)
    format_report = _git_command_function("format_git_stash_apply_report_text", format_git_stash_apply_report_text)
    return format_report("Stash apply", get_report(project_root, argument, max_patch_chars=max_patch_chars))


def get_stash_apply_report(project_root: str | Path = ".", argument: str | None = None, max_patch_chars: int = 12_000) -> dict[str, object]:
    _validate_git_stash_max_chars(max_patch_chars)
    root = Path(project_root).resolve()
    stash_ref = (argument or "").strip()
    if not stash_ref:
        return _git_stash_apply_usage_report(root, "/stash-apply <stash@{N}>", "stash ref is required.", max_patch_chars)

    workspace = local_command_workspace(root, "local-stash-apply")
    observation = _execute_action(
        workspace,
        GitStashApplyAction(type="git_stash_apply", stash_ref=stash_ref),
    )
    if observation.kind != "git_stash_apply":
        return _git_stash_apply_unexpected_report(root, stash_ref, f"Unexpected observation: {observation.kind}", max_patch_chars)
    return _git_stash_apply_observation_report(root, observation, max_patch_chars)


def _git_stash_apply_usage_report(root: Path, usage: str, error: str, max_patch_chars: int) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "stashRef": "",
        "patch": _empty_clip_report(max_patch_chars),
        "statusText": "",
        "message": f"Usage: {usage}\nError: {error}",
    }


def _git_stash_apply_unexpected_report(root: Path, stash_ref: str, message: str, max_patch_chars: int) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "stashRef": stash_ref,
        "patch": _empty_clip_report(max_patch_chars),
        "statusText": "",
        "message": message,
    }


def _git_stash_apply_observation_report(root: Path, observation: object, max_patch_chars: int) -> dict[str, object]:
    report: dict[str, object] = {
        "projectRoot": str(root),
        "ok": bool(getattr(observation, "ok")),
        "stashRef": str(getattr(observation, "stash_ref")),
        "patch": _clip_report(str(getattr(observation, "patch")), max_patch_chars),
        "statusText": str(getattr(observation, "status")),
        "message": str(getattr(observation, "message")),
    }
    if hasattr(observation, "worktree_clean"):
        report["worktreeClean"] = bool(getattr(observation, "worktree_clean"))
    return report
