from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import shlex
import sys

from .actions import execute_action as _default_execute_action
from .git_history_report_helpers import git_output_payload as _git_output_payload
from .git_history_report_helpers import usage_error as _usage_error
from .git_read_report_helpers import format_show_report_text
from .local_command_workspace import local_command_workspace
from .types import GitShowAction

SHOW_USAGE = "Usage: /show [rev] [path]"


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
