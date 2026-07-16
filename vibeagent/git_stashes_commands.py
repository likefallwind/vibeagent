from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import shlex
import sys

from .actions import execute_action as _default_execute_action
from .local_command_workspace import local_command_workspace
from .types import GitStashesAction

STASHES_USAGE = "Usage: /stashes [count]"


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


def _usage_error(usage: str, error: object) -> str:
    return f"{usage}\nError: {error}"


def get_stashes_report(project_root: str | Path = ".", argument: str | None = None, max_entries: int = 20) -> dict[str, object]:
    try:
        selected_max = parse_stashes_request(argument, max_entries)
    except ValueError as error:
        return {
            "projectRoot": str(Path(project_root).resolve()),
            "ok": False,
            "maxEntries": max_entries,
            "entries": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "message": _usage_error(STASHES_USAGE, error),
        }

    root = Path(project_root).resolve()
    workspace = local_command_workspace(root, "local-stashes")
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
