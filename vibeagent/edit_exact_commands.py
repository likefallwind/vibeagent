from __future__ import annotations

from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action
from .edit_command_parsing import parse_edit_file_argument, parse_multi_edit_file_argument
from .edit_text_formatting import format_line_edit_report_text, serialize_line_edit_report
from .types import CheckEditFileAction, CheckMultiEditAction, EditFileAction, EditOperation, MultiEditAction
from .workspace_core import RunWorkspace


def _execute_action(*args: object, **kwargs: object) -> object:
    commands_module = sys.modules.get("vibeagent.commands")
    command_execute_action = getattr(commands_module, "execute_action", None) if commands_module is not None else None
    if command_execute_action is not None:
        return command_execute_action(*args, **kwargs)
    return _default_execute_action(*args, **kwargs)


def _commands_attr(name: str, default: object) -> object:
    commands_module = sys.modules.get("vibeagent.commands")
    if commands_module is None:
        return default
    return getattr(commands_module, name, default)


def get_check_edit_file_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    old: str | None = None,
    new: str | None = None,
) -> str:
    return format_line_edit_report_text(
        "Check edit:",
        get_check_edit_file_report(project_root, argument, path=path, old=old, new=new),
    )


def get_check_edit_file_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    old: str | None = None,
    new: str | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_path, parsed_old, parsed_new = parse_edit_file_argument(
            argument,
            path=path,
            old=old,
            new=new,
            usage="/check-edit <path> <old> <new>",
        )
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "kind": "check_edit_file",
            "ok": False,
            "path": path or "",
            "message": f"Usage: /check-edit <path> <old> <new>\nError: {error}",
            "diff": {"text": "", "lines": [], "lineCount": 0},
        }
    workspace = RunWorkspace(root=root, run_id="local-check-edit", session_dir=root / ".vibeagent" / "sessions" / "local-check-edit")
    observation = _execute_action(workspace, CheckEditFileAction(type="check_edit_file", path=parsed_path, old=parsed_old, new=parsed_new))
    return serialize_line_edit_report(root, observation)


def get_edit_file_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    old: str | None = None,
    new: str | None = None,
) -> str:
    get_report = _commands_attr("get_edit_file_report", get_edit_file_report)
    formatter = _commands_attr("format_line_edit_report_text", format_line_edit_report_text)
    return formatter("Edit:", get_report(project_root, argument, path=path, old=old, new=new))


def get_edit_file_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    old: str | None = None,
    new: str | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_path, parsed_old, parsed_new = parse_edit_file_argument(
            argument,
            path=path,
            old=old,
            new=new,
            usage="/edit <path> <old> <new>",
        )
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "kind": "edit_file",
            "ok": False,
            "path": path or "",
            "message": f"Usage: /edit <path> <old> <new>\nError: {error}",
            "diff": {"text": "", "lines": [], "lineCount": 0},
        }
    workspace = RunWorkspace(root=root, run_id="local-edit", session_dir=root / ".vibeagent" / "sessions" / "local-edit")
    observation = _execute_action(workspace, EditFileAction(type="edit_file", path=parsed_path, old=parsed_old, new=parsed_new))
    return serialize_line_edit_report(root, observation)


def get_check_multi_edit_file_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    edits: list[EditOperation] | list[str] | None = None,
) -> str:
    return format_line_edit_report_text(
        "Check multi edit:",
        get_check_multi_edit_file_report(project_root, argument, path=path, edits=edits),
    )


def get_check_multi_edit_file_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    edits: list[EditOperation] | list[str] | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_path, parsed_edits = parse_multi_edit_file_argument(
            argument,
            path=path,
            edits=edits,
            usage="/check-multi-edit <path> <old> <new>...",
        )
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "kind": "check_multi_edit_file",
            "ok": False,
            "path": path or "",
            "message": f"Usage: /check-multi-edit <path> <old> <new>...\nError: {error}",
            "diff": {"text": "", "lines": [], "lineCount": 0},
        }
    workspace = RunWorkspace(root=root, run_id="local-check-multi-edit", session_dir=root / ".vibeagent" / "sessions" / "local-check-multi-edit")
    observation = _execute_action(workspace, CheckMultiEditAction(type="check_multi_edit_file", path=parsed_path, edits=parsed_edits))
    return serialize_line_edit_report(root, observation)


def get_multi_edit_file_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    edits: list[EditOperation] | list[str] | None = None,
) -> str:
    get_report = _commands_attr("get_multi_edit_file_report", get_multi_edit_file_report)
    formatter = _commands_attr("format_line_edit_report_text", format_line_edit_report_text)
    return formatter("Multi edit:", get_report(project_root, argument, path=path, edits=edits))


def get_multi_edit_file_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    edits: list[EditOperation] | list[str] | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_path, parsed_edits = parse_multi_edit_file_argument(
            argument,
            path=path,
            edits=edits,
            usage="/multi-edit <path> <old> <new>...",
        )
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "kind": "multi_edit_file",
            "ok": False,
            "path": path or "",
            "message": f"Usage: /multi-edit <path> <old> <new>...\nError: {error}",
            "diff": {"text": "", "lines": [], "lineCount": 0},
        }
    workspace = RunWorkspace(root=root, run_id="local-multi-edit", session_dir=root / ".vibeagent" / "sessions" / "local-multi-edit")
    observation = _execute_action(workspace, MultiEditAction(type="multi_edit_file", path=parsed_path, edits=parsed_edits))
    return serialize_line_edit_report(root, observation)
