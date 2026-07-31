from __future__ import annotations

from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action
from .edit_command_parsing import parse_file_transfer_list_argument, parse_source_destination_argument
from .edit_path_reports import (
    format_file_transfer_list_report_text,
    format_file_transfer_report_text,
    serialize_file_transfer_list_report,
    serialize_file_transfer_report,
)
from .edit_usage_report_helpers import (
    file_transfer_list_usage_report as _file_transfer_list_usage_report,
    file_transfer_usage_report as _file_transfer_usage_report,
)
from .local_command_workspace import local_command_workspace
from .types import (
    CheckCopyFileAction,
    CheckCopyFilesAction,
    CheckMoveFileAction,
    CheckMoveFilesAction,
    CopyFileAction,
    CopyFilesAction,
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
