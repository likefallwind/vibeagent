from __future__ import annotations

from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action
from .edit_command_parsing import (
    parse_file_transfer_list_argument,
    parse_required_path_list_argument,
    parse_required_single_path_argument,
    parse_source_destination_argument,
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
from .edit_usage_report_helpers import (
    file_transfer_list_usage_report as _file_transfer_list_usage_report,
    file_transfer_usage_report as _file_transfer_usage_report,
    path_action_usage_report as _path_action_usage_report,
    path_list_usage_report as _path_list_usage_report,
)
from .local_command_workspace import local_command_workspace
from .types import (
    CheckCopyFileAction,
    CheckCopyFilesAction,
    CheckCreateDirectoriesAction,
    CheckCreateDirectoryAction,
    CheckMoveFileAction,
    CheckMoveFilesAction,
    CopyFileAction,
    CopyFilesAction,
    CreateDirectoriesAction,
    CreateDirectoryAction,
    MoveFileAction,
    MoveFileTransfer,
    MoveFilesAction,
)


def _execute_action(*args: object, **kwargs: object) -> object:
    commands_module = sys.modules.get("vibeagent.commands")
    command_execute_action = getattr(commands_module, "execute_action", None) if commands_module is not None else None
    if command_execute_action is not None:
        return command_execute_action(*args, **kwargs)
    return _default_execute_action(*args, **kwargs)


def get_check_move_file_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    source: str | None = None,
    destination: str | None = None,
) -> str:
    return format_file_transfer_report_text(
        "Check move:",
        get_check_move_file_report(project_root, argument, source=source, destination=destination),
    )


def get_check_move_file_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    source: str | None = None,
    destination: str | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_source, parsed_destination = parse_source_destination_argument(
            argument,
            source=source,
            destination=destination,
            usage="/check-move <source> <destination>",
        )
    except ValueError as error:
        return _file_transfer_usage_report(root, "check_move_file", "/check-move <source> <destination>", error, source=source, destination=destination)
    workspace = local_command_workspace(root, "local-check-move")
    observation = _execute_action(workspace, CheckMoveFileAction(type="check_move_file", source=parsed_source, destination=parsed_destination))
    return serialize_file_transfer_report(root, observation)


def get_move_file_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    source: str | None = None,
    destination: str | None = None,
) -> str:
    return format_file_transfer_report_text(
        "Move:",
        get_move_file_report(project_root, argument, source=source, destination=destination),
    )


def get_move_file_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    source: str | None = None,
    destination: str | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_source, parsed_destination = parse_source_destination_argument(
            argument,
            source=source,
            destination=destination,
            usage="/move <source> <destination>",
        )
    except ValueError as error:
        return _file_transfer_usage_report(root, "move_file", "/move <source> <destination>", error, source=source, destination=destination)
    workspace = local_command_workspace(root, "local-move")
    observation = _execute_action(workspace, MoveFileAction(type="move_file", source=parsed_source, destination=parsed_destination))
    return serialize_file_transfer_report(root, observation)


def get_check_move_files_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    transfers: list[MoveFileTransfer] | None = None,
) -> str:
    return format_file_transfer_list_report_text(
        "Check move files:",
        get_check_move_files_report(project_root, argument, transfers=transfers),
    )


def get_check_move_files_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    transfers: list[MoveFileTransfer] | list[str] | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_transfers = parse_file_transfer_list_argument(argument, transfers=transfers, usage="/check-move-files <source> <destination>...")
    except ValueError as error:
        return _file_transfer_list_usage_report(root, "check_move_files", "/check-move-files <source> <destination>...", error)
    workspace = local_command_workspace(root, "local-check-move-files")
    observation = _execute_action(workspace, CheckMoveFilesAction(type="check_move_files", transfers=parsed_transfers))
    return serialize_file_transfer_list_report(root, observation)


def get_move_files_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    transfers: list[MoveFileTransfer] | None = None,
) -> str:
    return format_file_transfer_list_report_text(
        "Move files:",
        get_move_files_report(project_root, argument, transfers=transfers),
    )


def get_move_files_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    transfers: list[MoveFileTransfer] | list[str] | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_transfers = parse_file_transfer_list_argument(argument, transfers=transfers, usage="/move-files <source> <destination>...")
    except ValueError as error:
        return _file_transfer_list_usage_report(root, "move_files", "/move-files <source> <destination>...", error)
    workspace = local_command_workspace(root, "local-move-files")
    observation = _execute_action(workspace, MoveFilesAction(type="move_files", transfers=parsed_transfers))
    return serialize_file_transfer_list_report(root, observation)


def get_check_copy_file_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    source: str | None = None,
    destination: str | None = None,
) -> str:
    return format_file_transfer_report_text(
        "Check copy:",
        get_check_copy_file_report(project_root, argument, source=source, destination=destination),
    )


def get_check_copy_file_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    source: str | None = None,
    destination: str | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_source, parsed_destination = parse_source_destination_argument(
            argument,
            source=source,
            destination=destination,
            usage="/check-copy <source> <destination>",
        )
    except ValueError as error:
        return _file_transfer_usage_report(root, "check_copy_file", "/check-copy <source> <destination>", error, source=source, destination=destination)
    workspace = local_command_workspace(root, "local-check-copy")
    observation = _execute_action(workspace, CheckCopyFileAction(type="check_copy_file", source=parsed_source, destination=parsed_destination))
    return serialize_file_transfer_report(root, observation)


def get_copy_file_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    source: str | None = None,
    destination: str | None = None,
) -> str:
    return format_file_transfer_report_text(
        "Copy:",
        get_copy_file_report(project_root, argument, source=source, destination=destination),
    )


def get_copy_file_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    source: str | None = None,
    destination: str | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_source, parsed_destination = parse_source_destination_argument(
            argument,
            source=source,
            destination=destination,
            usage="/copy <source> <destination>",
        )
    except ValueError as error:
        return _file_transfer_usage_report(root, "copy_file", "/copy <source> <destination>", error, source=source, destination=destination)
    workspace = local_command_workspace(root, "local-copy")
    observation = _execute_action(workspace, CopyFileAction(type="copy_file", source=parsed_source, destination=parsed_destination))
    return serialize_file_transfer_report(root, observation)


def get_check_copy_files_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    transfers: list[MoveFileTransfer] | None = None,
) -> str:
    return format_file_transfer_list_report_text(
        "Check copy files:",
        get_check_copy_files_report(project_root, argument, transfers=transfers),
    )


def get_check_copy_files_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    transfers: list[MoveFileTransfer] | list[str] | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_transfers = parse_file_transfer_list_argument(argument, transfers=transfers, usage="/check-copy-files <source> <destination>...")
    except ValueError as error:
        return _file_transfer_list_usage_report(root, "check_copy_files", "/check-copy-files <source> <destination>...", error)
    workspace = local_command_workspace(root, "local-check-copy-files")
    observation = _execute_action(workspace, CheckCopyFilesAction(type="check_copy_files", transfers=parsed_transfers))
    return serialize_file_transfer_list_report(root, observation)


def get_copy_files_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    transfers: list[MoveFileTransfer] | None = None,
) -> str:
    return format_file_transfer_list_report_text(
        "Copy files:",
        get_copy_files_report(project_root, argument, transfers=transfers),
    )


def get_copy_files_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    transfers: list[MoveFileTransfer] | list[str] | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_transfers = parse_file_transfer_list_argument(argument, transfers=transfers, usage="/copy-files <source> <destination>...")
    except ValueError as error:
        return _file_transfer_list_usage_report(root, "copy_files", "/copy-files <source> <destination>...", error)
    workspace = local_command_workspace(root, "local-copy-files")
    observation = _execute_action(workspace, CopyFilesAction(type="copy_files", transfers=parsed_transfers))
    return serialize_file_transfer_list_report(root, observation)


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
