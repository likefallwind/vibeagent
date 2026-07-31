from __future__ import annotations

from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action
from .edit_command_parsing import (
    parse_required_path_list_argument,
    parse_required_single_path_argument,
)
from .edit_path_commands import (
    _path_action_usage_report,
    _path_list_usage_report,
    format_path_action_report_text,
    format_path_list_report_text,
    serialize_path_action_report,
    serialize_path_list_report,
)
from .edit_directory_transfer_commands import (
    get_check_copy_dir_report,
    get_check_copy_dir_text,
    get_check_copy_dirs_report,
    get_check_copy_dirs_text,
    get_check_move_dir_report,
    get_check_move_dir_text,
    get_check_move_dirs_report,
    get_check_move_dirs_text,
    get_copy_dir_report,
    get_copy_dir_text,
    get_copy_dirs_report,
    get_copy_dirs_text,
    get_move_dir_report,
    get_move_dir_text,
    get_move_dirs_report,
    get_move_dirs_text,
)
from .local_command_workspace import local_command_workspace
from .types import (
    CheckDeleteEmptyDirectoriesAction,
    CheckDeleteEmptyDirectoryAction,
    DeleteEmptyDirectoriesAction,
    DeleteEmptyDirectoryAction,
)


def _execute_action(*args: object, **kwargs: object) -> object:
    commands_module = sys.modules.get("vibeagent.commands")
    command_execute_action = getattr(commands_module, "execute_action", None) if commands_module is not None else None
    if command_execute_action is not None:
        return command_execute_action(*args, **kwargs)
    return _default_execute_action(*args, **kwargs)


def get_check_delete_empty_dir_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
) -> str:
    return format_path_action_report_text(
        "Check rmdir:",
        get_check_delete_empty_dir_report(project_root, argument, path=path),
    )


def get_check_delete_empty_dir_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_path = parse_required_single_path_argument(argument, path=path, usage="/check-rmdir <path>")
    except ValueError as error:
        return _path_action_usage_report(root, "check_delete_empty_dir", "/check-rmdir <path>", error, path=path)
    workspace = local_command_workspace(root, "local-check-rmdir")
    observation = _execute_action(workspace, CheckDeleteEmptyDirectoryAction(type="check_delete_empty_dir", path=parsed_path))
    return serialize_path_action_report(root, observation)


def get_delete_empty_dir_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
) -> str:
    return format_path_action_report_text(
        "Rmdir:",
        get_delete_empty_dir_report(project_root, argument, path=path),
    )


def get_delete_empty_dir_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_path = parse_required_single_path_argument(argument, path=path, usage="/rmdir <path>")
    except ValueError as error:
        return _path_action_usage_report(root, "delete_empty_dir", "/rmdir <path>", error, path=path)
    workspace = local_command_workspace(root, "local-rmdir")
    observation = _execute_action(workspace, DeleteEmptyDirectoryAction(type="delete_empty_dir", path=parsed_path))
    return serialize_path_action_report(root, observation)


def get_check_delete_empty_dirs_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    paths: list[str] | None = None,
) -> str:
    return format_path_list_report_text(
        "Check rmdirs:",
        get_check_delete_empty_dirs_report(project_root, argument, paths=paths),
    )


def get_check_delete_empty_dirs_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    paths: list[str] | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_paths = parse_required_path_list_argument(argument, paths=paths, usage="/check-rmdirs <path...>")
    except ValueError as error:
        return _path_list_usage_report(root, "check_delete_empty_dirs", "/check-rmdirs <path...>", error)
    workspace = local_command_workspace(root, "local-check-rmdirs")
    observation = _execute_action(workspace, CheckDeleteEmptyDirectoriesAction(type="check_delete_empty_dirs", paths=parsed_paths))
    return serialize_path_list_report(root, observation)


def get_delete_empty_dirs_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    paths: list[str] | None = None,
) -> str:
    return format_path_list_report_text(
        "Rmdirs:",
        get_delete_empty_dirs_report(project_root, argument, paths=paths),
    )


def get_delete_empty_dirs_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    paths: list[str] | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_paths = parse_required_path_list_argument(argument, paths=paths, usage="/rmdirs <path...>")
    except ValueError as error:
        return _path_list_usage_report(root, "delete_empty_dirs", "/rmdirs <path...>", error)
    workspace = local_command_workspace(root, "local-rmdirs")
    observation = _execute_action(workspace, DeleteEmptyDirectoriesAction(type="delete_empty_dirs", paths=parsed_paths))
    return serialize_path_list_report(root, observation)
