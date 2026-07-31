from __future__ import annotations

from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action
from .edit_command_parsing import parse_directory_transfer_list_argument, parse_source_destination_argument
from .edit_path_commands import (
    _file_transfer_list_usage_report,
    _file_transfer_usage_report,
    format_file_transfer_list_report_text,
    format_file_transfer_report_text,
    serialize_file_transfer_list_report,
    serialize_file_transfer_report,
)
from .local_command_workspace import local_command_workspace
from .types import (
    CheckCopyDirectoriesAction,
    CheckCopyDirectoryAction,
    CheckMoveDirectoriesAction,
    CheckMoveDirectoryAction,
    CopyDirectoriesAction,
    CopyDirectoryAction,
    DirectoryTransfer,
    MoveDirectoriesAction,
    MoveDirectoryAction,
)


def _execute_action(*args: object, **kwargs: object) -> object:
    commands_module = sys.modules.get("vibeagent.commands")
    command_execute_action = getattr(commands_module, "execute_action", None) if commands_module is not None else None
    if command_execute_action is not None:
        return command_execute_action(*args, **kwargs)
    return _default_execute_action(*args, **kwargs)


def get_check_move_dir_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    source: str | None = None,
    destination: str | None = None,
) -> str:
    return format_file_transfer_report_text(
        "Check move dir:",
        get_check_move_dir_report(project_root, argument, source=source, destination=destination),
    )


def get_check_move_dir_report(
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
            usage="/check-move-dir <source> <destination>",
        )
    except ValueError as error:
        return _file_transfer_usage_report(root, "check_move_dir", "/check-move-dir <source> <destination>", error, source=source, destination=destination)
    workspace = local_command_workspace(root, "local-check-move-dir")
    observation = _execute_action(workspace, CheckMoveDirectoryAction(type="check_move_dir", source=parsed_source, destination=parsed_destination))
    return serialize_file_transfer_report(root, observation)


def get_move_dir_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    source: str | None = None,
    destination: str | None = None,
) -> str:
    return format_file_transfer_report_text(
        "Move dir:",
        get_move_dir_report(project_root, argument, source=source, destination=destination),
    )


def get_move_dir_report(
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
            usage="/move-dir <source> <destination>",
        )
    except ValueError as error:
        return _file_transfer_usage_report(root, "move_dir", "/move-dir <source> <destination>", error, source=source, destination=destination)
    workspace = local_command_workspace(root, "local-move-dir")
    observation = _execute_action(workspace, MoveDirectoryAction(type="move_dir", source=parsed_source, destination=parsed_destination))
    return serialize_file_transfer_report(root, observation)


def get_check_move_dirs_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    transfers: list[DirectoryTransfer] | list[str] | None = None,
) -> str:
    return format_file_transfer_list_report_text(
        "Check move dirs:",
        get_check_move_dirs_report(project_root, argument, transfers=transfers),
    )


def get_check_move_dirs_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    transfers: list[DirectoryTransfer] | list[str] | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_transfers = parse_directory_transfer_list_argument(argument, transfers=transfers, usage="/check-move-dirs <source> <destination>...")
    except ValueError as error:
        return _file_transfer_list_usage_report(root, "check_move_dirs", "/check-move-dirs <source> <destination>...", error)
    workspace = local_command_workspace(root, "local-check-move-dirs")
    observation = _execute_action(workspace, CheckMoveDirectoriesAction(type="check_move_dirs", transfers=parsed_transfers))
    return serialize_file_transfer_list_report(root, observation)


def get_move_dirs_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    transfers: list[DirectoryTransfer] | list[str] | None = None,
) -> str:
    return format_file_transfer_list_report_text(
        "Move dirs:",
        get_move_dirs_report(project_root, argument, transfers=transfers),
    )


def get_move_dirs_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    transfers: list[DirectoryTransfer] | list[str] | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_transfers = parse_directory_transfer_list_argument(argument, transfers=transfers, usage="/move-dirs <source> <destination>...")
    except ValueError as error:
        return _file_transfer_list_usage_report(root, "move_dirs", "/move-dirs <source> <destination>...", error)
    workspace = local_command_workspace(root, "local-move-dirs")
    observation = _execute_action(workspace, MoveDirectoriesAction(type="move_dirs", transfers=parsed_transfers))
    return serialize_file_transfer_list_report(root, observation)


def get_check_copy_dir_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    source: str | None = None,
    destination: str | None = None,
) -> str:
    return format_file_transfer_report_text(
        "Check copy dir:",
        get_check_copy_dir_report(project_root, argument, source=source, destination=destination),
    )


def get_check_copy_dir_report(
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
            usage="/check-copy-dir <source> <destination>",
        )
    except ValueError as error:
        return _file_transfer_usage_report(root, "check_copy_dir", "/check-copy-dir <source> <destination>", error, source=source, destination=destination)
    workspace = local_command_workspace(root, "local-check-copy-dir")
    observation = _execute_action(workspace, CheckCopyDirectoryAction(type="check_copy_dir", source=parsed_source, destination=parsed_destination))
    return serialize_file_transfer_report(root, observation)


def get_copy_dir_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    source: str | None = None,
    destination: str | None = None,
) -> str:
    return format_file_transfer_report_text(
        "Copy dir:",
        get_copy_dir_report(project_root, argument, source=source, destination=destination),
    )


def get_copy_dir_report(
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
            usage="/copy-dir <source> <destination>",
        )
    except ValueError as error:
        return _file_transfer_usage_report(root, "copy_dir", "/copy-dir <source> <destination>", error, source=source, destination=destination)
    workspace = local_command_workspace(root, "local-copy-dir")
    observation = _execute_action(workspace, CopyDirectoryAction(type="copy_dir", source=parsed_source, destination=parsed_destination))
    return serialize_file_transfer_report(root, observation)


def get_check_copy_dirs_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    transfers: list[DirectoryTransfer] | list[str] | None = None,
) -> str:
    return format_file_transfer_list_report_text(
        "Check copy dirs:",
        get_check_copy_dirs_report(project_root, argument, transfers=transfers),
    )


def get_check_copy_dirs_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    transfers: list[DirectoryTransfer] | list[str] | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_transfers = parse_directory_transfer_list_argument(argument, transfers=transfers, usage="/check-copy-dirs <source> <destination>...")
    except ValueError as error:
        return _file_transfer_list_usage_report(root, "check_copy_dirs", "/check-copy-dirs <source> <destination>...", error)
    workspace = local_command_workspace(root, "local-check-copy-dirs")
    observation = _execute_action(workspace, CheckCopyDirectoriesAction(type="check_copy_dirs", transfers=parsed_transfers))
    return serialize_file_transfer_list_report(root, observation)


def get_copy_dirs_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    transfers: list[DirectoryTransfer] | list[str] | None = None,
) -> str:
    return format_file_transfer_list_report_text(
        "Copy dirs:",
        get_copy_dirs_report(project_root, argument, transfers=transfers),
    )


def get_copy_dirs_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    transfers: list[DirectoryTransfer] | list[str] | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_transfers = parse_directory_transfer_list_argument(argument, transfers=transfers, usage="/copy-dirs <source> <destination>...")
    except ValueError as error:
        return _file_transfer_list_usage_report(root, "copy_dirs", "/copy-dirs <source> <destination>...", error)
    workspace = local_command_workspace(root, "local-copy-dirs")
    observation = _execute_action(workspace, CopyDirectoriesAction(type="copy_dirs", transfers=parsed_transfers))
    return serialize_file_transfer_list_report(root, observation)
