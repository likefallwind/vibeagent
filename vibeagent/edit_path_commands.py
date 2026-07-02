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
from .edit_text_commands import format_line_edit_report_text, serialize_line_edit_report
from .types import (
    CheckCopyFileAction,
    CheckCopyFilesAction,
    CheckCreateDirectoriesAction,
    CheckCreateDirectoryAction,
    CheckDeleteFileAction,
    CheckDeleteFilesAction,
    CheckMoveFileAction,
    CheckMoveFilesAction,
    CopyFileAction,
    CopyFilesAction,
    CreateDirectoriesAction,
    CreateDirectoryAction,
    DeleteFileAction,
    DeleteFilesAction,
    MoveFileAction,
    MoveFileTransfer,
    MoveFilesAction,
)
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
        return {
            "projectRoot": str(root),
            "kind": "check_move_file",
            "ok": False,
            "source": source or "",
            "destination": destination or "",
            "message": f"Usage: /check-move <source> <destination>\nError: {error}",
        }
    workspace = RunWorkspace(root=root, run_id="local-check-move", session_dir=root / ".vibeagent" / "sessions" / "local-check-move")
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
        return {
            "projectRoot": str(root),
            "kind": "move_file",
            "ok": False,
            "source": source or "",
            "destination": destination or "",
            "message": f"Usage: /move <source> <destination>\nError: {error}",
        }
    workspace = RunWorkspace(root=root, run_id="local-move", session_dir=root / ".vibeagent" / "sessions" / "local-move")
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
        return {
            "projectRoot": str(root),
            "kind": "check_move_files",
            "ok": False,
            "transfers": {"total": 0, "items": []},
            "message": f"Usage: /check-move-files <source> <destination>...\nError: {error}",
        }
    workspace = RunWorkspace(root=root, run_id="local-check-move-files", session_dir=root / ".vibeagent" / "sessions" / "local-check-move-files")
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
        return {
            "projectRoot": str(root),
            "kind": "move_files",
            "ok": False,
            "transfers": {"total": 0, "items": []},
            "message": f"Usage: /move-files <source> <destination>...\nError: {error}",
        }
    workspace = RunWorkspace(root=root, run_id="local-move-files", session_dir=root / ".vibeagent" / "sessions" / "local-move-files")
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
        return {
            "projectRoot": str(root),
            "kind": "check_copy_file",
            "ok": False,
            "source": source or "",
            "destination": destination or "",
            "message": f"Usage: /check-copy <source> <destination>\nError: {error}",
        }
    workspace = RunWorkspace(root=root, run_id="local-check-copy", session_dir=root / ".vibeagent" / "sessions" / "local-check-copy")
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
        return {
            "projectRoot": str(root),
            "kind": "copy_file",
            "ok": False,
            "source": source or "",
            "destination": destination or "",
            "message": f"Usage: /copy <source> <destination>\nError: {error}",
        }
    workspace = RunWorkspace(root=root, run_id="local-copy", session_dir=root / ".vibeagent" / "sessions" / "local-copy")
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
        return {
            "projectRoot": str(root),
            "kind": "check_copy_files",
            "ok": False,
            "transfers": {"total": 0, "items": []},
            "message": f"Usage: /check-copy-files <source> <destination>...\nError: {error}",
        }
    workspace = RunWorkspace(root=root, run_id="local-check-copy-files", session_dir=root / ".vibeagent" / "sessions" / "local-check-copy-files")
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
        return {
            "projectRoot": str(root),
            "kind": "copy_files",
            "ok": False,
            "transfers": {"total": 0, "items": []},
            "message": f"Usage: /copy-files <source> <destination>...\nError: {error}",
        }
    workspace = RunWorkspace(root=root, run_id="local-copy-files", session_dir=root / ".vibeagent" / "sessions" / "local-copy-files")
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
        return {
            "projectRoot": str(root),
            "kind": "check_create_dir",
            "ok": False,
            "path": path or "",
            "message": f"Usage: /check-mkdir <path>\nError: {error}",
        }
    workspace = RunWorkspace(root=root, run_id="local-check-mkdir", session_dir=root / ".vibeagent" / "sessions" / "local-check-mkdir")
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
        return {
            "projectRoot": str(root),
            "kind": "create_dir",
            "ok": False,
            "path": path or "",
            "message": f"Usage: /mkdir <path>\nError: {error}",
        }
    workspace = RunWorkspace(root=root, run_id="local-mkdir", session_dir=root / ".vibeagent" / "sessions" / "local-mkdir")
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
        return {
            "projectRoot": str(root),
            "kind": "check_create_dirs",
            "ok": False,
            "paths": {"total": 0, "items": []},
            "message": f"Usage: /check-mkdirs <path...>\nError: {error}",
        }
    workspace = RunWorkspace(root=root, run_id="local-check-mkdirs", session_dir=root / ".vibeagent" / "sessions" / "local-check-mkdirs")
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
        return {
            "projectRoot": str(root),
            "kind": "create_dirs",
            "ok": False,
            "paths": {"total": 0, "items": []},
            "message": f"Usage: /mkdirs <path...>\nError: {error}",
        }
    workspace = RunWorkspace(root=root, run_id="local-mkdirs", session_dir=root / ".vibeagent" / "sessions" / "local-mkdirs")
    observation = _execute_action(workspace, CreateDirectoriesAction(type="create_dirs", paths=parsed_paths))
    return serialize_path_list_report(root, observation)


def format_path_action_observation(title: str, root: Path, observation: object) -> str:
    return format_path_action_report_text(title, serialize_path_action_report(root, observation))


def serialize_path_action_report(root: Path, observation: object) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "kind": str(getattr(observation, "kind", "") or ""),
        "ok": bool(getattr(observation, "ok", False)),
        "path": str(getattr(observation, "path", "") or ""),
        "message": str(getattr(observation, "message", "") or ""),
    }


def format_path_action_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    return "\n".join(
        [
            title,
            f"  projectRoot: {report.get('projectRoot') or '.'}",
            f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
            f"  path: {report.get('path') or ''}",
            f"  message: {message}",
        ]
    )


def format_path_list_observation(title: str, root: Path, observation: object, *, include_diff: bool = False) -> str:
    return format_path_list_report_text(title, serialize_path_list_report(root, observation), include_diff=include_diff)


def serialize_path_list_report(root: Path, observation: object) -> dict[str, object]:
    paths = [str(path) for path in list(getattr(observation, "paths", []))]
    diff = str(getattr(observation, "diff", "") or "")
    return {
        "projectRoot": str(root),
        "kind": str(getattr(observation, "kind", "") or ""),
        "ok": bool(getattr(observation, "ok", False)),
        "paths": {"total": len(paths), "items": paths},
        "message": str(getattr(observation, "message", "") or ""),
        "diff": {"text": diff, "lines": diff.splitlines(), "lineCount": len(diff.splitlines())},
    }


def format_path_list_report_text(title: str, report: dict[str, object], *, include_diff: bool = False) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    paths_report = report.get("paths") if isinstance(report.get("paths"), dict) else {}
    paths = [str(path) for path in paths_report.get("items", [])] if isinstance(paths_report.get("items"), list) else []
    lines = [
        title,
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  paths: {int(paths_report.get('total', len(paths)) or 0)}",
        f"  message: {message}",
    ]
    if paths:
        lines.append("  items:")
        for path in paths:
            lines.append(f"    - {path}")
    if include_diff:
        diff_report = report.get("diff") if isinstance(report.get("diff"), dict) else {}
        diff = str(diff_report.get("text") or "")
        if diff:
            lines.append("  diff:")
            for diff_line in diff.splitlines():
                lines.append(f"    {diff_line}")
    return "\n".join(lines)


def format_file_transfer_observation(title: str, root: Path, observation: object) -> str:
    return format_file_transfer_report_text(title, serialize_file_transfer_report(root, observation))


def serialize_file_transfer_report(root: Path, observation: object) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "kind": str(getattr(observation, "kind", "") or ""),
        "ok": bool(getattr(observation, "ok", False)),
        "source": str(getattr(observation, "source", "") or ""),
        "destination": str(getattr(observation, "destination", "") or ""),
        "message": str(getattr(observation, "message", "") or ""),
    }


def format_file_transfer_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    return "\n".join(
        [
            title,
            f"  projectRoot: {report.get('projectRoot') or '.'}",
            f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
            f"  source: {report.get('source') or ''}",
            f"  destination: {report.get('destination') or ''}",
            f"  message: {message}",
        ]
    )


def format_file_transfer_list_observation(title: str, root: Path, observation: object) -> str:
    return format_file_transfer_list_report_text(title, serialize_file_transfer_list_report(root, observation))


def serialize_file_transfer_list_report(root: Path, observation: object) -> dict[str, object]:
    transfer_items: list[dict[str, object]] = []
    for transfer in list(getattr(observation, "transfers", [])):
        transfer_items.append(
            {
                "source": str(getattr(transfer, "source", "") or ""),
                "destination": str(getattr(transfer, "destination", "") or ""),
            }
        )
    return {
        "projectRoot": str(root),
        "kind": str(getattr(observation, "kind", "") or ""),
        "ok": bool(getattr(observation, "ok", False)),
        "transfers": {"total": len(transfer_items), "items": transfer_items},
        "message": str(getattr(observation, "message", "") or ""),
    }


def format_file_transfer_list_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    transfers_report = report.get("transfers") if isinstance(report.get("transfers"), dict) else {}
    transfers = [item for item in transfers_report.get("items", []) if isinstance(item, dict)] if isinstance(transfers_report.get("items"), list) else []
    lines = [
        title,
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  transfers: {int(transfers_report.get('total', len(transfers)) or 0)}",
        f"  message: {message}",
    ]
    if transfers:
        lines.append("  items:")
        for transfer in transfers:
            lines.append(f"    - {transfer.get('source') or ''} -> {transfer.get('destination') or ''}")
    return "\n".join(lines)


