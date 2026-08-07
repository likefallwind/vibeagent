from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import shlex
import sys

from .actions import execute_action as _default_execute_action
from .read_command_parsing import parse_read_request
from .git_show_commands import SHOW_USAGE, get_show_report, get_show_text, parse_show_request
from .git_history_report_helpers import (
    git_log_items as _git_log_items,
    git_output_payload as _git_output_payload,
    split_nonempty_lines as _split_nonempty_lines,
    usage_error as _usage_error,
)
from .git_read_report_helpers import format_blame_report_text, format_log_report_text, format_show_report_text
from .local_command_workspace import local_command_workspace
from .types import GitBlameAction, GitLogAction

LOG_USAGE = "Usage: /log [path] [count]"
BLAME_USAGE = "Usage: /blame <path> [start[:end]]"


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


def get_log_text(project_root: str | Path = ".", argument: str | None = None, max_count: int = 5) -> str:
    get_report = _git_command_function("get_log_report", get_log_report)
    format_report = _git_command_function("format_log_report_text", format_log_report_text)
    return format_report(get_report(project_root, argument, max_count=max_count))


def parse_log_request(argument: str | None, max_count: int = 5) -> tuple[str | None, int]:
    path: str | None = None
    selected_count = max_count
    if argument and argument.strip():
        try:
            parts = shlex.split(argument)
        except ValueError as error:
            raise ValueError(str(error)) from error
        if len(parts) > 2:
            raise ValueError("expected optional path and optional count.")
        if len(parts) == 1:
            if parts[0].isdigit():
                selected_count = int(parts[0])
            else:
                path = parts[0]
        elif len(parts) == 2:
            path = parts[0]
            if not parts[1].isdigit():
                raise ValueError(f"invalid count: {parts[1]}")
            selected_count = int(parts[1])
    if selected_count < 1:
        raise ValueError("count must be at least 1.")
    if selected_count > 50:
        raise ValueError("count must be at most 50.")
    return path, selected_count


def get_log_report(project_root: str | Path = ".", argument: str | None = None, max_count: int = 5) -> dict[str, object]:
    try:
        path, selected_count = parse_log_request(argument, max_count)
    except ValueError as error:
        return {
            "projectRoot": str(Path(project_root).resolve()),
            "ok": False,
            "path": ".",
            "maxCount": max_count,
            "commits": {"shown": 0, "items": []},
            "log": "",
            "message": _usage_error(LOG_USAGE, error),
        }

    root = Path(project_root).resolve()
    workspace = local_command_workspace(root, "local-log")
    observation = _execute_action(
        workspace,
        GitLogAction(type="git_log", path=path, max_count=selected_count),
    )
    if observation.kind != "git_log":
        return {
            "projectRoot": str(root),
            "ok": False,
            "path": path or ".",
            "maxCount": selected_count,
            "commits": {"shown": 0, "items": []},
            "log": "",
            "message": f"Unexpected observation: {observation.kind}",
        }
    items = _git_log_items(observation.log)
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "path": observation.path or ".",
        "maxCount": observation.max_count,
        "commits": {"shown": len(items), "items": items},
        "log": observation.log,
        "message": observation.message,
    }


def get_blame_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    line_range: str | None = None,
    max_output_chars: int = 12_000,
) -> str:
    get_report = _git_command_function("get_blame_report", get_blame_report)
    format_report = _git_command_function("format_blame_report_text", format_blame_report_text)
    return format_report(
        get_report(
            project_root,
            argument,
            line_range=line_range,
            max_output_chars=max_output_chars,
        )
    )


def get_blame_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    line_range: str | None = None,
    max_output_chars: int = 12_000,
) -> dict[str, object]:
    if max_output_chars < 1_000:
        return {
            "projectRoot": str(Path(project_root).resolve()),
            "ok": False,
            "path": "",
            "range": ".",
            "startLine": None,
            "lineCount": None,
            "output": _git_output_payload("", truncated=False, max_output_chars=max_output_chars),
            "message": _usage_error(BLAME_USAGE, "max_output_chars must be at least 1000."),
        }
    if max_output_chars > 50_000:
        return {
            "projectRoot": str(Path(project_root).resolve()),
            "ok": False,
            "path": "",
            "range": ".",
            "startLine": None,
            "lineCount": None,
            "output": _git_output_payload("", truncated=False, max_output_chars=max_output_chars),
            "message": _usage_error(BLAME_USAGE, "max_output_chars must be at most 50000."),
        }
    if argument is None or not argument.strip():
        return {
            "projectRoot": str(Path(project_root).resolve()),
            "ok": False,
            "path": "",
            "range": ".",
            "startLine": None,
            "lineCount": None,
            "output": _git_output_payload("", truncated=False, max_output_chars=max_output_chars),
            "message": BLAME_USAGE,
        }
    try:
        path, start_line, line_count, range_label = parse_read_request(argument, line_range)
    except ValueError as error:
        return {
            "projectRoot": str(Path(project_root).resolve()),
            "ok": False,
            "path": argument,
            "range": line_range or ".",
            "startLine": None,
            "lineCount": None,
            "output": _git_output_payload("", truncated=False, max_output_chars=max_output_chars),
            "message": _usage_error(BLAME_USAGE, error),
        }

    root = Path(project_root).resolve()
    workspace = local_command_workspace(root, "local-blame")
    observation = _execute_action(
        workspace,
        GitBlameAction(
            type="git_blame",
            path=path,
            start_line=start_line,
            line_count=line_count,
            max_output_chars=max_output_chars,
        ),
    )
    if observation.kind != "git_blame":
        return {
            "projectRoot": str(root),
            "ok": False,
            "path": path,
            "range": range_label or ".",
            "startLine": start_line,
            "lineCount": line_count,
            "output": _git_output_payload("", truncated=False, max_output_chars=max_output_chars),
            "message": f"Unexpected observation: {observation.kind}",
        }
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "path": observation.path,
        "range": range_label or ".",
        "startLine": observation.start_line,
        "lineCount": observation.line_count,
        "output": _git_output_payload(
            observation.blame,
            truncated=observation.truncated,
            max_output_chars=observation.max_output_chars,
        ),
        "message": observation.message,
    }
