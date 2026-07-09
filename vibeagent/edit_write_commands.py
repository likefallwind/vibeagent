from __future__ import annotations

from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action
from .edit_command_parsing import parse_write_file_argument, parse_write_file_list_argument
from .edit_text_formatting import (
    format_line_edit_report_text,
    format_write_files_report_text,
    serialize_line_edit_report,
    serialize_write_files_report,
)
from .types import CheckWriteFileAction, CheckWriteFilesAction, WriteFileAction, WriteFileItem, WriteFilesAction
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


def get_check_write_file_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    content: str | None = None,
) -> str:
    return format_line_edit_report_text(
        "Check write:",
        get_check_write_file_report(project_root, argument, path=path, content=content),
    )


def get_check_write_file_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    content: str | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_path, parsed_content = parse_write_file_argument(
            argument,
            path=path,
            content=content,
            usage="/check-write <path> <text>",
        )
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "kind": "check_write_file",
            "ok": False,
            "path": path or "",
            "message": f"Usage: /check-write <path> <text>\nError: {error}",
            "diff": {"text": "", "lines": [], "lineCount": 0},
        }
    workspace = RunWorkspace(root=root, run_id="local-check-write", session_dir=root / ".vibeagent" / "sessions" / "local-check-write")
    observation = _execute_action(workspace, CheckWriteFileAction(type="check_write_file", path=parsed_path, content=parsed_content))
    return serialize_line_edit_report(root, observation)


def get_write_file_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    content: str | None = None,
) -> str:
    get_report = _commands_attr("get_write_file_report", get_write_file_report)
    formatter = _commands_attr("format_line_edit_report_text", format_line_edit_report_text)
    return formatter("Write:", get_report(project_root, argument, path=path, content=content))


def get_write_file_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    content: str | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_path, parsed_content = parse_write_file_argument(
            argument,
            path=path,
            content=content,
            usage="/write <path> <text>",
        )
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "kind": "write_file",
            "ok": False,
            "path": path or "",
            "message": f"Usage: /write <path> <text>\nError: {error}",
            "diff": {"text": "", "lines": [], "lineCount": 0},
        }
    workspace = RunWorkspace(root=root, run_id="local-write", session_dir=root / ".vibeagent" / "sessions" / "local-write")
    observation = _execute_action(workspace, WriteFileAction(type="write_file", path=parsed_path, content=parsed_content))
    return serialize_line_edit_report(root, observation)


def get_check_write_files_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    files: list[WriteFileItem] | list[str] | None = None,
) -> str:
    return format_write_files_report_text(
        "Check write files:",
        get_check_write_files_report(project_root, argument, files=files),
    )


def get_check_write_files_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    files: list[WriteFileItem] | list[str] | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_files = parse_write_file_list_argument(argument, files=files, usage="/check-write-files <path> <text>...")
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "kind": "check_write_files",
            "ok": False,
            "files": {"total": 0, "items": []},
            "message": f"Usage: /check-write-files <path> <text>...\nError: {error}",
        }
    workspace = RunWorkspace(root=root, run_id="local-check-write-files", session_dir=root / ".vibeagent" / "sessions" / "local-check-write-files")
    observation = _execute_action(workspace, CheckWriteFilesAction(type="check_write_files", files=parsed_files))
    return serialize_write_files_report(root, observation)


def get_write_files_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    files: list[WriteFileItem] | list[str] | None = None,
) -> str:
    get_report = _commands_attr("get_write_files_report", get_write_files_report)
    formatter = _commands_attr("format_write_files_report_text", format_write_files_report_text)
    return formatter("Write files:", get_report(project_root, argument, files=files))


def get_write_files_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    files: list[WriteFileItem] | list[str] | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_files = parse_write_file_list_argument(argument, files=files, usage="/write-files <path> <text>...")
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "kind": "write_files",
            "ok": False,
            "files": {"total": 0, "items": []},
            "message": f"Usage: /write-files <path> <text>...\nError: {error}",
        }
    workspace = RunWorkspace(root=root, run_id="local-write-files", session_dir=root / ".vibeagent" / "sessions" / "local-write-files")
    observation = _execute_action(workspace, WriteFilesAction(type="write_files", files=parsed_files))
    return serialize_write_files_report(root, observation)
