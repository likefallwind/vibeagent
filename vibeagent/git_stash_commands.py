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
    format_git_stash_apply_report_text,
    format_git_stash_apply_text,
    format_git_stash_drop_report_text,
    format_git_stash_drop_text,
    format_git_stash_report_text,
    format_git_stash_text,
)
from .git_stashes_commands import (
    format_stashes_report_text,
    get_stashes_report,
    get_stashes_text,
    parse_stashes_request,
)
from .types import (
    CheckGitStashAction,
    CheckGitStashApplyAction,
    CheckGitStashDropAction,
    GitStashAction,
    GitStashApplyAction,
    GitStashDropAction,
)
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

    workspace = RunWorkspace(root=root, run_id="local-check-stash-apply", session_dir=root / ".vibeagent" / "sessions" / "local-check-stash-apply")
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

    workspace = RunWorkspace(root=root, run_id="local-stash-apply", session_dir=root / ".vibeagent" / "sessions" / "local-stash-apply")
    observation = _execute_action(
        workspace,
        GitStashApplyAction(type="git_stash_apply", stash_ref=stash_ref),
    )
    if observation.kind != "git_stash_apply":
        return _git_stash_apply_unexpected_report(root, stash_ref, f"Unexpected observation: {observation.kind}", max_patch_chars)
    return _git_stash_apply_observation_report(root, observation, max_patch_chars)


def get_check_stash_drop_text(project_root: str | Path = ".", argument: str | None = None, max_patch_chars: int = 12_000) -> str:
    get_report = _git_command_function("get_check_stash_drop_report", get_check_stash_drop_report)
    format_report = _git_command_function("format_git_stash_drop_report_text", format_git_stash_drop_report_text)
    return format_report("Check stash drop", get_report(project_root, argument, max_patch_chars=max_patch_chars))


def get_check_stash_drop_report(project_root: str | Path = ".", argument: str | None = None, max_patch_chars: int = 12_000) -> dict[str, object]:
    _validate_git_stash_max_chars(max_patch_chars)
    root = Path(project_root).resolve()
    stash_ref = (argument or "").strip()
    if not stash_ref:
        return _git_stash_drop_usage_report(root, "/check-stash-drop <stash@{N}>", "stash ref is required.", max_patch_chars)

    workspace = RunWorkspace(root=root, run_id="local-check-stash-drop", session_dir=root / ".vibeagent" / "sessions" / "local-check-stash-drop")
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
        return _git_stash_drop_usage_report(root, "/stash-drop <stash@{N}>", "stash ref is required.", max_patch_chars)

    workspace = RunWorkspace(root=root, run_id="local-stash-drop", session_dir=root / ".vibeagent" / "sessions" / "local-stash-drop")
    observation = _execute_action(
        workspace,
        GitStashDropAction(type="git_stash_drop", stash_ref=stash_ref),
    )
    if observation.kind != "git_stash_drop":
        return _git_stash_drop_unexpected_report(root, stash_ref, f"Unexpected observation: {observation.kind}", max_patch_chars)
    return _git_stash_drop_observation_report(root, observation, max_patch_chars)


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
