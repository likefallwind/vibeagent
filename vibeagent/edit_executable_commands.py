from __future__ import annotations

from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action
from .edit_command_parsing import parse_executable_argument
from .local_command_workspace import local_command_workspace
from .types import CheckSetExecutableAction, SetExecutableAction


def _execute_action(*args: object, **kwargs: object) -> object:
    commands_module = sys.modules.get("vibeagent.commands")
    command_execute_action = getattr(commands_module, "execute_action", None) if commands_module is not None else None
    if command_execute_action is not None:
        return command_execute_action(*args, **kwargs)
    return _default_execute_action(*args, **kwargs)


def get_check_set_executable_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    executable: bool | str | None = None,
) -> str:
    return format_executable_report_text(
        "Check executable:",
        get_check_set_executable_report(project_root, argument, path=path, executable=executable),
    )


def get_check_set_executable_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    executable: bool | str | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_path, parsed_executable = parse_executable_argument(
            argument,
            path=path,
            executable=executable,
            usage="/check-executable <path> [true|false]",
        )
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "kind": "check_set_executable",
            "ok": False,
            "path": path or "",
            "executable": executable if isinstance(executable, bool) else False,
            "modeBefore": "",
            "modeAfter": "",
            "message": f"Usage: /check-executable <path> [true|false]\nError: {error}",
        }
    workspace = local_command_workspace(root, "local-check-executable")
    observation = _execute_action(workspace, CheckSetExecutableAction(type="check_set_executable", path=parsed_path, executable=parsed_executable))
    return serialize_executable_report(root, observation)


def get_set_executable_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    executable: bool | str | None = None,
) -> str:
    return format_executable_report_text(
        "Set executable:",
        get_set_executable_report(project_root, argument, path=path, executable=executable),
    )


def get_set_executable_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    executable: bool | str | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_path, parsed_executable = parse_executable_argument(
            argument,
            path=path,
            executable=executable,
            usage="/set-executable <path> [true|false]",
        )
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "kind": "set_executable",
            "ok": False,
            "path": path or "",
            "executable": executable if isinstance(executable, bool) else False,
            "modeBefore": "",
            "modeAfter": "",
            "message": f"Usage: /set-executable <path> [true|false]\nError: {error}",
        }
    workspace = local_command_workspace(root, "local-set-executable")
    observation = _execute_action(workspace, SetExecutableAction(type="set_executable", path=parsed_path, executable=parsed_executable))
    return serialize_executable_report(root, observation)


def format_executable_observation(title: str, root: Path, observation: object) -> str:
    return format_executable_report_text(title, serialize_executable_report(root, observation))


def serialize_executable_report(root: Path, observation: object) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "kind": str(getattr(observation, "kind", "") or ""),
        "ok": bool(getattr(observation, "ok", False)),
        "path": str(getattr(observation, "path", "") or ""),
        "executable": bool(getattr(observation, "executable", False)),
        "modeBefore": str(getattr(observation, "mode_before", "") or ""),
        "modeAfter": str(getattr(observation, "mode_after", "") or ""),
        "message": str(getattr(observation, "message", "") or ""),
    }


def format_executable_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    return "\n".join(
        [
            title,
            f"  projectRoot: {report.get('projectRoot') or '.'}",
            f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
            f"  path: {report.get('path') or ''}",
            f"  executable: {'yes' if bool(report.get('executable')) else 'no'}",
            f"  modeBefore: {report.get('modeBefore') or ''}",
            f"  modeAfter: {report.get('modeAfter') or ''}",
            f"  message: {message}",
        ]
    )
