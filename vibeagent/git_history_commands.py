from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action
from .read_command_parsing import parse_read_request
from .git_log_commands import LOG_USAGE, get_log_report, get_log_text, parse_log_request
from .git_show_commands import SHOW_USAGE, get_show_report, get_show_text, parse_show_request
from .git_history_report_helpers import (
    git_log_items as _git_log_items,
    git_output_payload as _git_output_payload,
    split_nonempty_lines as _split_nonempty_lines,
    usage_error as _usage_error,
)
from .git_read_report_helpers import format_blame_report_text, format_log_report_text, format_show_report_text
from .local_command_workspace import local_command_workspace
from .types import GitBlameAction

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
