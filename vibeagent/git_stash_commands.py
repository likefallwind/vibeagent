from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import shlex
import sys

from .actions import execute_action as _default_execute_action
from .git_read_commands import _indent_block, clip_with_flag
from .types import (
    CheckGitStashAction,
    CheckGitStashApplyAction,
    CheckGitStashDropAction,
    GitStashAction,
    GitStashApplyAction,
    GitStashDropAction,
    GitStashesAction,
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


def get_stashes_report(project_root: str | Path = ".", argument: str | None = None, max_entries: int = 20) -> dict[str, object]:
    try:
        selected_max = parse_stashes_request(argument, max_entries)
    except ValueError as error:
        return {
            "projectRoot": str(Path(project_root).resolve()),
            "ok": False,
            "maxEntries": max_entries,
            "entries": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "message": f"Usage: /stashes [count]\nError: {error}",
        }

    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-stashes", session_dir=root / ".vibeagent" / "sessions" / "local-stashes")
    observation = _execute_action(
        workspace,
        GitStashesAction(type="git_stashes", max_entries=selected_max),
    )
    if observation.kind != "git_stashes":
        return {
            "projectRoot": str(root),
            "ok": False,
            "maxEntries": selected_max,
            "entries": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "message": f"Unexpected observation: {observation.kind}",
        }
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "maxEntries": selected_max,
        "entries": {
            "shown": len(observation.entries),
            "total": observation.total,
            "truncated": observation.truncated,
            "items": [
                {"name": entry.name, "summary": entry.summary}
                for entry in observation.entries
            ],
        },
        "message": observation.message,
    }


def format_stashes_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    entries = report.get("entries") if isinstance(report.get("entries"), dict) else {}
    items = entries.get("items") if isinstance(entries, dict) and isinstance(entries.get("items"), list) else []
    lines = [
        "Stashes:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  entries: {entries.get('shown', 0)}/{entries.get('total', 0)}",
        f"  maxEntries: {report.get('maxEntries', 0)}",
        f"  truncated: {'yes' if bool(entries.get('truncated')) else 'no'}",
    ]
    if items:
        lines.append("  items:")
        for entry in items:
            if isinstance(entry, dict):
                lines.append(f"    - {entry.get('name')}: {entry.get('summary')}")
    else:
        lines.append("  items: none")
    lines.append(f"  message: {message}")
    return "\n".join(lines)


def get_stashes_text(project_root: str | Path = ".", argument: str | None = None, max_entries: int = 20) -> str:
    get_report = _git_command_function("get_stashes_report", get_stashes_report)
    format_report = _git_command_function("format_stashes_report_text", format_stashes_report_text)
    return format_report(get_report(project_root, argument, max_entries=max_entries))


def parse_stashes_request(argument: str | None, max_entries: int = 20) -> int:
    selected = max_entries
    if argument and argument.strip():
        try:
            parts = shlex.split(argument)
        except ValueError as error:
            raise ValueError(str(error)) from error
        if len(parts) > 1:
            raise ValueError("expected optional count.")
        if not parts[0].isdigit():
            raise ValueError(f"invalid count: {parts[0]}")
        selected = int(parts[0])
    if selected < 1:
        raise ValueError("count must be at least 1.")
    if selected > 100:
        raise ValueError("count must be at most 100.")
    return selected


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


def format_git_stash_text(
    title: str,
    root: Path,
    ok: bool,
    message_text: str,
    include_untracked: bool,
    stash_ref: str,
    status: str,
    diff: str,
    message: str,
    max_diff_chars: int,
) -> str:
    _validate_git_stash_max_chars(max_diff_chars)
    diff_text, diff_truncated = clip_with_flag(diff, max_diff_chars)
    report = {
        "projectRoot": str(root),
        "ok": ok,
        "messageText": message_text,
        "includeUntracked": include_untracked,
        "stashRef": stash_ref,
        "statusText": status,
        "diff": {"text": diff_text, "chars": len(diff), "truncated": diff_truncated, "maxChars": max_diff_chars},
        "message": message,
    }
    return format_git_stash_report_text(title, report)


def _validate_git_stash_max_chars(max_chars: int) -> None:
    if max_chars < 100:
        raise ValueError("max_chars must be at least 100.")
    if max_chars > 200_000:
        raise ValueError("max_chars must be at most 200000.")


def _empty_clip_report(max_chars: int) -> dict[str, object]:
    return {"text": "", "chars": 0, "truncated": False, "maxChars": max_chars}


def _clip_report(value: str, max_chars: int) -> dict[str, object]:
    text, truncated = clip_with_flag(value, max_chars)
    return {"text": text, "chars": len(value), "truncated": truncated, "maxChars": max_chars}


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


def format_git_stash_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    diff = report.get("diff") if isinstance(report.get("diff"), dict) else {}
    diff_text = str(diff.get("text") or "")
    status = str(report.get("statusText") or "")
    lines = [
        f"{title}:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  messageText: {report.get('messageText') or '.'}",
        f"  includeUntracked: {'yes' if bool(report.get('includeUntracked')) else 'no'}",
    ]
    if report.get("stashRef"):
        lines.append(f"  stashRef: {report.get('stashRef')}")
    if status.strip():
        lines.append("  status:")
        lines.append(_indent_block(status.strip(), spaces=4))
    else:
        lines.append("  status: none")
    lines.append(f"  diffChars: {diff.get('chars', 0)}")
    lines.append(f"  diffTruncated: {'yes' if bool(diff.get('truncated')) else 'no'}")
    lines.append(f"  message: {message}")
    if diff_text:
        lines.append("")
        lines.append(diff_text)
    return "\n".join(lines)


def format_git_stash_apply_text(
    title: str,
    root: Path,
    ok: bool,
    stash_ref: str,
    worktree_clean: bool | None,
    patch: str,
    status: str,
    message: str,
    max_patch_chars: int,
) -> str:
    _validate_git_stash_max_chars(max_patch_chars)
    patch_text, patch_truncated = clip_with_flag(patch, max_patch_chars)
    report: dict[str, object] = {
        "projectRoot": str(root),
        "ok": ok,
        "stashRef": stash_ref,
        "patch": {"text": patch_text, "chars": len(patch), "truncated": patch_truncated, "maxChars": max_patch_chars},
        "statusText": status,
        "message": message,
    }
    if worktree_clean is not None:
        report["worktreeClean"] = worktree_clean
    return format_git_stash_apply_report_text(title, report)


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


def format_git_stash_apply_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    patch = report.get("patch") if isinstance(report.get("patch"), dict) else {}
    patch_text = str(patch.get("text") or "")
    status = str(report.get("statusText") or "")
    lines = [
        f"{title}:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  stashRef: {report.get('stashRef') or '.'}",
    ]
    if "worktreeClean" in report:
        lines.append(f"  worktreeClean: {'yes' if bool(report.get('worktreeClean')) else 'no'}")
    if status.strip():
        lines.append("  status:")
        lines.append(_indent_block(status.strip(), spaces=4))
    else:
        lines.append("  status: none")
    lines.append(f"  patchChars: {patch.get('chars', 0)}")
    lines.append(f"  patchTruncated: {'yes' if bool(patch.get('truncated')) else 'no'}")
    lines.append(f"  message: {message}")
    if patch_text:
        lines.append("")
        lines.append(patch_text)
    return "\n".join(lines)


def format_git_stash_drop_text(
    title: str,
    root: Path,
    ok: bool,
    stash_ref: str,
    summary: str,
    patch: str,
    remaining_total: int | None,
    message: str,
    max_patch_chars: int,
) -> str:
    _validate_git_stash_max_chars(max_patch_chars)
    patch_text, patch_truncated = clip_with_flag(patch, max_patch_chars)
    report: dict[str, object] = {
        "projectRoot": str(root),
        "ok": ok,
        "stashRef": stash_ref,
        "summary": summary,
        "patch": {"text": patch_text, "chars": len(patch), "truncated": patch_truncated, "maxChars": max_patch_chars},
        "message": message,
    }
    if remaining_total is not None:
        report["remainingTotal"] = remaining_total
    return format_git_stash_drop_report_text(title, report)


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


def format_git_stash_drop_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    patch = report.get("patch") if isinstance(report.get("patch"), dict) else {}
    patch_text = str(patch.get("text") or "")
    lines = [
        f"{title}:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  stashRef: {report.get('stashRef') or '.'}",
        f"  summary: {report.get('summary') or '.'}",
    ]
    if "remainingTotal" in report:
        lines.append(f"  remainingTotal: {report.get('remainingTotal')}")
    lines.append(f"  patchChars: {patch.get('chars', 0)}")
    lines.append(f"  patchTruncated: {'yes' if bool(patch.get('truncated')) else 'no'}")
    lines.append(f"  message: {message}")
    if patch_text:
        lines.append("")
        lines.append(patch_text)
    return "\n".join(lines)
