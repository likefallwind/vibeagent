from __future__ import annotations

from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action
from .edit_command_parsing import parse_required_path_list_argument, parse_required_single_path_argument
from .edit_path_reports import format_path_list_report_text, serialize_path_list_report
from .edit_text_commands import format_line_edit_report_text, serialize_line_edit_report
from .types import CheckDeleteFileAction, CheckDeleteFilesAction, DeleteFileAction, DeleteFilesAction
from .workspace_core import RunWorkspace


def _execute_action(*args: object, **kwargs: object) -> object:
    commands_module = sys.modules.get("vibeagent.commands")
    command_execute_action = getattr(commands_module, "execute_action", None) if commands_module is not None else None
    if command_execute_action is not None:
        return command_execute_action(*args, **kwargs)
    return _default_execute_action(*args, **kwargs)


def get_check_delete_file_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
) -> str:
    return format_line_edit_report_text(
        "Check delete:",
        get_check_delete_file_report(project_root, argument, path=path),
    )


def get_check_delete_file_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_path = parse_required_single_path_argument(
            argument,
            path=path,
            usage="/check-delete <path>",
        )
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "kind": "check_delete_file",
            "ok": False,
            "path": path or "",
            "message": f"Usage: /check-delete <path>\nError: {error}",
            "diff": {"text": "", "lines": [], "lineCount": 0},
        }
    workspace = RunWorkspace(root=root, run_id="local-check-delete", session_dir=root / ".vibeagent" / "sessions" / "local-check-delete")
    observation = _execute_action(workspace, CheckDeleteFileAction(type="check_delete_file", path=parsed_path))
    return serialize_line_edit_report(root, observation)


def get_delete_file_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
) -> str:
    return format_line_edit_report_text(
        "Delete:",
        get_delete_file_report(project_root, argument, path=path),
    )


def get_delete_file_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_path = parse_required_single_path_argument(
            argument,
            path=path,
            usage="/delete <path>",
        )
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "kind": "delete_file",
            "ok": False,
            "path": path or "",
            "message": f"Usage: /delete <path>\nError: {error}",
            "diff": {"text": "", "lines": [], "lineCount": 0},
        }
    workspace = RunWorkspace(root=root, run_id="local-delete", session_dir=root / ".vibeagent" / "sessions" / "local-delete")
    observation = _execute_action(workspace, DeleteFileAction(type="delete_file", path=parsed_path))
    return serialize_line_edit_report(root, observation)


def get_check_delete_files_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    paths: list[str] | None = None,
) -> str:
    return format_path_list_report_text(
        "Check delete files:",
        get_check_delete_files_report(project_root, argument, paths=paths),
        include_diff=True,
    )


def get_check_delete_files_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    paths: list[str] | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_paths = parse_required_path_list_argument(argument, paths=paths, usage="/check-delete-files <path...>")
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "kind": "check_delete_files",
            "ok": False,
            "paths": {"total": 0, "items": []},
            "message": f"Usage: /check-delete-files <path...>\nError: {error}",
            "diff": {"text": "", "lines": [], "lineCount": 0},
        }
    workspace = RunWorkspace(root=root, run_id="local-check-delete-files", session_dir=root / ".vibeagent" / "sessions" / "local-check-delete-files")
    observation = _execute_action(workspace, CheckDeleteFilesAction(type="check_delete_files", paths=parsed_paths))
    return serialize_path_list_report(root, observation)


def get_delete_files_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    paths: list[str] | None = None,
) -> str:
    return format_path_list_report_text(
        "Delete files:",
        get_delete_files_report(project_root, argument, paths=paths),
        include_diff=True,
    )


def get_delete_files_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    paths: list[str] | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_paths = parse_required_path_list_argument(argument, paths=paths, usage="/delete-files <path...>")
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "kind": "delete_files",
            "ok": False,
            "paths": {"total": 0, "items": []},
            "message": f"Usage: /delete-files <path...>\nError: {error}",
            "diff": {"text": "", "lines": [], "lineCount": 0},
        }
    workspace = RunWorkspace(root=root, run_id="local-delete-files", session_dir=root / ".vibeagent" / "sessions" / "local-delete-files")
    observation = _execute_action(workspace, DeleteFilesAction(type="delete_files", paths=parsed_paths))
    return serialize_path_list_report(root, observation)
