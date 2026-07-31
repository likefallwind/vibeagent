from __future__ import annotations

from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action
from .edit_command_parsing import (
    parse_required_path_list_argument,
    parse_required_single_path_argument,
)
from .edit_delete_commands import (
    get_check_delete_file_report,
    get_check_delete_file_text,
    get_check_delete_files_report,
    get_check_delete_files_text,
    get_delete_file_report,
    get_delete_file_text,
    get_delete_files_report,
    get_delete_files_text,
)
from .edit_path_reports import (
    format_file_transfer_list_observation,
    format_file_transfer_list_report_text,
    format_file_transfer_observation,
    format_file_transfer_report_text,
    format_path_action_observation,
    format_path_action_report_text,
    format_path_list_observation,
    format_path_list_report_text,
    serialize_file_transfer_list_report,
    serialize_file_transfer_report,
    serialize_path_action_report,
    serialize_path_list_report,
)
from .edit_transfer_commands import (
    get_check_copy_file_report,
    get_check_copy_file_text,
    get_check_copy_files_report,
    get_check_copy_files_text,
    get_check_move_file_report,
    get_check_move_file_text,
    get_check_move_files_report,
    get_check_move_files_text,
    get_copy_file_report,
    get_copy_file_text,
    get_copy_files_report,
    get_copy_files_text,
    get_move_file_report,
    get_move_file_text,
    get_move_files_report,
    get_move_files_text,
)
from .edit_usage_report_helpers import (
    file_transfer_list_usage_report as _file_transfer_list_usage_report,
    file_transfer_usage_report as _file_transfer_usage_report,
    path_action_usage_report as _path_action_usage_report,
    path_list_usage_report as _path_list_usage_report,
)
from .local_command_workspace import local_command_workspace
from .types import (
    CheckCreateDirectoriesAction,
    CheckCreateDirectoryAction,
    CreateDirectoriesAction,
    CreateDirectoryAction,
)


def _execute_action(*args: object, **kwargs: object) -> object:
    commands_module = sys.modules.get("vibeagent.commands")
    command_execute_action = getattr(commands_module, "execute_action", None) if commands_module is not None else None
    if command_execute_action is not None:
        return command_execute_action(*args, **kwargs)
    return _default_execute_action(*args, **kwargs)


def get_check_create_dir_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
) -> str:
    return format_path_action_report_text(
        "Check mkdir:",
        get_check_create_dir_report(project_root, argument, path=path),
    )


def get_check_create_dir_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_path = parse_required_single_path_argument(argument, path=path, usage="/check-mkdir <path>")
    except ValueError as error:
        return _path_action_usage_report(root, "check_create_dir", "/check-mkdir <path>", error, path=path)
    workspace = local_command_workspace(root, "local-check-mkdir")
    observation = _execute_action(workspace, CheckCreateDirectoryAction(type="check_create_dir", path=parsed_path))
    return serialize_path_action_report(root, observation)


def get_create_dir_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
) -> str:
    return format_path_action_report_text(
        "Mkdir:",
        get_create_dir_report(project_root, argument, path=path),
    )


def get_create_dir_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_path = parse_required_single_path_argument(argument, path=path, usage="/mkdir <path>")
    except ValueError as error:
        return _path_action_usage_report(root, "create_dir", "/mkdir <path>", error, path=path)
    workspace = local_command_workspace(root, "local-mkdir")
    observation = _execute_action(workspace, CreateDirectoryAction(type="create_dir", path=parsed_path))
    return serialize_path_action_report(root, observation)


def get_check_create_dirs_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    paths: list[str] | None = None,
) -> str:
    return format_path_list_report_text(
        "Check mkdirs:",
        get_check_create_dirs_report(project_root, argument, paths=paths),
    )


def get_check_create_dirs_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    paths: list[str] | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_paths = parse_required_path_list_argument(argument, paths=paths, usage="/check-mkdirs <path...>")
    except ValueError as error:
        return _path_list_usage_report(root, "check_create_dirs", "/check-mkdirs <path...>", error)
    workspace = local_command_workspace(root, "local-check-mkdirs")
    observation = _execute_action(workspace, CheckCreateDirectoriesAction(type="check_create_dirs", paths=parsed_paths))
    return serialize_path_list_report(root, observation)


def get_create_dirs_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    paths: list[str] | None = None,
) -> str:
    return format_path_list_report_text(
        "Mkdirs:",
        get_create_dirs_report(project_root, argument, paths=paths),
    )


def get_create_dirs_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    paths: list[str] | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_paths = parse_required_path_list_argument(argument, paths=paths, usage="/mkdirs <path...>")
    except ValueError as error:
        return _path_list_usage_report(root, "create_dirs", "/mkdirs <path...>", error)
    workspace = local_command_workspace(root, "local-mkdirs")
    observation = _execute_action(workspace, CreateDirectoriesAction(type="create_dirs", paths=parsed_paths))
    return serialize_path_list_report(root, observation)
