from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import shlex
import sys

from .actions import execute_action as _default_execute_action
from .read_command_parsing import parse_read_request
from .git_read_report_helpers import format_blame_report_text, format_log_report_text, format_show_report_text
from .local_command_workspace import local_command_workspace
from .types import GitBlameAction, GitLogAction, GitShowAction

LOG_USAGE = "Usage: /log [path] [count]"
SHOW_USAGE = "Usage: /show [rev] [path]"
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


def _split_nonempty_lines(value: str) -> list[str]:
    return [line for line in value.splitlines() if line.strip()]


def _usage_error(usage: str, error: object) -> str:
    return f"{usage}\nError: {error}"


def _git_output_payload(output: str, *, truncated: bool, max_output_chars: int) -> dict[str, object]:
    lines = output.splitlines()
    return {
        "text": output,
        "chars": len(output),
        "lines": len(lines),
        "truncated": truncated,
        "maxOutputChars": max_output_chars,
    }


def _git_log_items(log: str) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for line in _split_nonempty_lines(log):
        short_hash, _, subject = line.partition(" ")
        items.append(
            {
                "hash": short_hash,
                "subject": subject,
                "raw": line,
            }
        )
    return items


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


def get_show_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    rev: str | None = None,
    path: str | None = None,
    max_output_chars: int = 12_000,
) -> str:
    get_report = _git_command_function("get_show_report", get_show_report)
    format_report = _git_command_function("format_show_report_text", format_show_report_text)
    return format_report(
        get_report(
            project_root,
            argument,
            rev=rev,
            path=path,
            max_output_chars=max_output_chars,
        )
    )


def parse_show_request(argument: str | None = None, rev: str | None = None, path: str | None = None) -> tuple[str, str | None]:
    if argument and argument.strip():
        if rev is not None or path is not None:
            raise ValueError("show argument cannot be combined with explicit rev or path.")
        try:
            parts = shlex.split(argument)
        except ValueError as error:
            raise ValueError(str(error)) from error
        if len(parts) > 2:
            raise ValueError("expected optional rev and optional path.")
        if not parts:
            return "HEAD", None
        if len(parts) == 1:
            return parts[0], None
        return parts[0], parts[1]

    selected_rev = (rev or "HEAD").strip()
    if not selected_rev:
        raise ValueError("rev must be a non-empty string.")
    selected_path = path.strip() if path else None
    return selected_rev, selected_path


def get_show_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    rev: str | None = None,
    path: str | None = None,
    max_output_chars: int = 12_000,
) -> dict[str, object]:
    if max_output_chars < 1_000:
        return {
            "projectRoot": str(Path(project_root).resolve()),
            "ok": False,
            "rev": rev or "HEAD",
            "path": path or ".",
            "output": _git_output_payload("", truncated=False, max_output_chars=max_output_chars),
            "message": _usage_error(SHOW_USAGE, "max_output_chars must be at least 1000."),
        }
    if max_output_chars > 50_000:
        return {
            "projectRoot": str(Path(project_root).resolve()),
            "ok": False,
            "rev": rev or "HEAD",
            "path": path or ".",
            "output": _git_output_payload("", truncated=False, max_output_chars=max_output_chars),
            "message": _usage_error(SHOW_USAGE, "max_output_chars must be at most 50000."),
        }
    try:
        selected_rev, selected_path = parse_show_request(argument, rev, path)
    except ValueError as error:
        return {
            "projectRoot": str(Path(project_root).resolve()),
            "ok": False,
            "rev": rev or "HEAD",
            "path": path or ".",
            "output": _git_output_payload("", truncated=False, max_output_chars=max_output_chars),
            "message": _usage_error(SHOW_USAGE, error),
        }

    root = Path(project_root).resolve()
    workspace = local_command_workspace(root, "local-show")
    observation = _execute_action(
        workspace,
        GitShowAction(type="git_show", rev=selected_rev, path=selected_path, max_output_chars=max_output_chars),
    )
    if observation.kind != "git_show":
        return {
            "projectRoot": str(root),
            "ok": False,
            "rev": selected_rev,
            "path": selected_path or ".",
            "output": _git_output_payload("", truncated=False, max_output_chars=max_output_chars),
            "message": f"Unexpected observation: {observation.kind}",
        }
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "rev": observation.rev,
        "path": observation.path or ".",
        "output": _git_output_payload(
            observation.output,
            truncated=observation.truncated,
            max_output_chars=observation.max_output_chars,
        ),
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
