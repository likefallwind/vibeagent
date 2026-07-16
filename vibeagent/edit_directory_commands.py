from __future__ import annotations

from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action
from .edit_command_parsing import (
    parse_directory_transfer_list_argument,
    parse_required_path_list_argument,
    parse_required_single_path_argument,
    parse_source_destination_argument,
)
from .edit_path_commands import (
    format_file_transfer_list_report_text,
    format_file_transfer_report_text,
    format_path_action_report_text,
    format_path_list_report_text,
    serialize_file_transfer_list_report,
    serialize_file_transfer_report,
    serialize_path_action_report,
    serialize_path_list_report,
)
from .types import (
    CheckCopyDirectoriesAction,
    CheckCopyDirectoryAction,
    CheckDeleteEmptyDirectoriesAction,
    CheckDeleteEmptyDirectoryAction,
    CheckMoveDirectoriesAction,
    CheckMoveDirectoryAction,
    CopyDirectoriesAction,
    CopyDirectoryAction,
    DeleteEmptyDirectoriesAction,
    DeleteEmptyDirectoryAction,
    DirectoryTransfer,
    MoveDirectoriesAction,
    MoveDirectoryAction,
)
from .workspace_core import RunWorkspace


def _execute_action(*args: object, **kwargs: object) -> object:
    commands_module = sys.modules.get("vibeagent.commands")
    command_execute_action = getattr(commands_module, "execute_action", None) if commands_module is not None else None
    if command_execute_action is not None:
        return command_execute_action(*args, **kwargs)
    return _default_execute_action(*args, **kwargs)


def _local_workspace(root: Path, run_id: str) -> RunWorkspace:
    return RunWorkspace(root=root, run_id=run_id, session_dir=root / ".vibeagent" / "sessions" / run_id)


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
        return {
            "projectRoot": str(root),
            "kind": "check_move_dir",
            "ok": False,
            "source": source or "",
            "destination": destination or "",
            "message": f"Usage: /check-move-dir <source> <destination>\nError: {error}",
        }
    workspace = _local_workspace(root, "local-check-move-dir")
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
        return {
            "projectRoot": str(root),
            "kind": "move_dir",
            "ok": False,
            "source": source or "",
            "destination": destination or "",
            "message": f"Usage: /move-dir <source> <destination>\nError: {error}",
        }
    workspace = _local_workspace(root, "local-move-dir")
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
        return {
            "projectRoot": str(root),
            "kind": "check_move_dirs",
            "ok": False,
            "transfers": {"total": 0, "items": []},
            "message": f"Usage: /check-move-dirs <source> <destination>...\nError: {error}",
        }
    workspace = _local_workspace(root, "local-check-move-dirs")
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
        return {
            "projectRoot": str(root),
            "kind": "move_dirs",
            "ok": False,
            "transfers": {"total": 0, "items": []},
            "message": f"Usage: /move-dirs <source> <destination>...\nError: {error}",
        }
    workspace = _local_workspace(root, "local-move-dirs")
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
        return {
            "projectRoot": str(root),
            "kind": "check_copy_dir",
            "ok": False,
            "source": source or "",
            "destination": destination or "",
            "message": f"Usage: /check-copy-dir <source> <destination>\nError: {error}",
        }
    workspace = _local_workspace(root, "local-check-copy-dir")
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
        return {
            "projectRoot": str(root),
            "kind": "copy_dir",
            "ok": False,
            "source": source or "",
            "destination": destination or "",
            "message": f"Usage: /copy-dir <source> <destination>\nError: {error}",
        }
    workspace = _local_workspace(root, "local-copy-dir")
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
        return {
            "projectRoot": str(root),
            "kind": "check_copy_dirs",
            "ok": False,
            "transfers": {"total": 0, "items": []},
            "message": f"Usage: /check-copy-dirs <source> <destination>...\nError: {error}",
        }
    workspace = _local_workspace(root, "local-check-copy-dirs")
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
        return {
            "projectRoot": str(root),
            "kind": "copy_dirs",
            "ok": False,
            "transfers": {"total": 0, "items": []},
            "message": f"Usage: /copy-dirs <source> <destination>...\nError: {error}",
        }
    workspace = _local_workspace(root, "local-copy-dirs")
    observation = _execute_action(workspace, CopyDirectoriesAction(type="copy_dirs", transfers=parsed_transfers))
    return serialize_file_transfer_list_report(root, observation)


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
        return {
            "projectRoot": str(root),
            "kind": "check_delete_empty_dir",
            "ok": False,
            "path": path or "",
            "message": f"Usage: /check-rmdir <path>\nError: {error}",
        }
    workspace = _local_workspace(root, "local-check-rmdir")
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
        return {
            "projectRoot": str(root),
            "kind": "delete_empty_dir",
            "ok": False,
            "path": path or "",
            "message": f"Usage: /rmdir <path>\nError: {error}",
        }
    workspace = _local_workspace(root, "local-rmdir")
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
        return {
            "projectRoot": str(root),
            "kind": "check_delete_empty_dirs",
            "ok": False,
            "paths": {"total": 0, "items": []},
            "message": f"Usage: /check-rmdirs <path...>\nError: {error}",
        }
    workspace = _local_workspace(root, "local-check-rmdirs")
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
        return {
            "projectRoot": str(root),
            "kind": "delete_empty_dirs",
            "ok": False,
            "paths": {"total": 0, "items": []},
            "message": f"Usage: /rmdirs <path...>\nError: {error}",
        }
    workspace = _local_workspace(root, "local-rmdirs")
    observation = _execute_action(workspace, DeleteEmptyDirectoriesAction(type="delete_empty_dirs", paths=parsed_paths))
    return serialize_path_list_report(root, observation)

