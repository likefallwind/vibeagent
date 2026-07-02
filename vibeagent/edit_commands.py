from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action
from .command_parsing import parse_optional_single_path_argument
from .edit_command_parsing import (
    parse_append_file_argument,
    parse_directory_transfer_list_argument,
    parse_edit_file_argument,
    parse_executable_argument,
    parse_file_transfer_list_argument,
    parse_insert_lines_argument,
    parse_json_patch_argument,
    parse_json_patch_operations,
    parse_json_remove_argument,
    parse_json_set_argument,
    parse_line_number,
    parse_multi_edit_file_argument,
    parse_optional_bool,
    parse_patch_argument,
    parse_patches_argument,
    parse_regex_replace_argument,
    parse_replace_lines_argument,
    parse_required_path_list_argument,
    parse_required_single_path_argument,
    parse_source_destination_argument,
    parse_write_file_argument,
    parse_write_file_list_argument,
    read_patch_argument_value,
    validate_line_number,
    validate_line_range,
    validate_nonnegative_int,
    validate_positive_int,
)
from .edit_json_commands import (
    format_json_patch_observation,
    format_json_patch_report_text,
    format_json_pointer_observation,
    format_json_pointer_report_text,
    get_check_json_patch_report,
    get_check_json_patch_text,
    get_check_json_remove_report,
    get_check_json_remove_text,
    get_check_json_set_report,
    get_check_json_set_text,
    get_json_patch_report,
    get_json_patch_text,
    get_json_remove_report,
    get_json_remove_text,
    get_json_set_report,
    get_json_set_text,
    serialize_json_patch_report,
    serialize_json_pointer_report,
)
from .edit_directory_commands import (
    get_check_copy_dir_report,
    get_check_copy_dir_text,
    get_check_copy_dirs_report,
    get_check_copy_dirs_text,
    get_check_delete_empty_dir_report,
    get_check_delete_empty_dir_text,
    get_check_delete_empty_dirs_report,
    get_check_delete_empty_dirs_text,
    get_check_move_dir_report,
    get_check_move_dir_text,
    get_check_move_dirs_report,
    get_check_move_dirs_text,
    get_copy_dir_report,
    get_copy_dir_text,
    get_copy_dirs_report,
    get_copy_dirs_text,
    get_delete_empty_dir_report,
    get_delete_empty_dir_text,
    get_delete_empty_dirs_report,
    get_delete_empty_dirs_text,
    get_move_dir_report,
    get_move_dir_text,
    get_move_dirs_report,
    get_move_dirs_text,
)
from .edit_path_commands import (
    format_file_transfer_list_observation,
    format_file_transfer_list_report_text,
    format_file_transfer_observation,
    format_file_transfer_report_text,
    format_path_action_observation,
    format_path_action_report_text,
    format_path_list_observation,
    format_path_list_report_text,
    get_check_copy_file_report,
    get_check_copy_file_text,
    get_check_copy_files_report,
    get_check_copy_files_text,
    get_check_create_dir_report,
    get_check_create_dir_text,
    get_check_create_dirs_report,
    get_check_create_dirs_text,
    get_check_delete_file_report,
    get_check_delete_file_text,
    get_check_delete_files_report,
    get_check_delete_files_text,
    get_check_move_file_report,
    get_check_move_file_text,
    get_check_move_files_report,
    get_check_move_files_text,
    get_copy_file_report,
    get_copy_file_text,
    get_copy_files_report,
    get_copy_files_text,
    get_create_dir_report,
    get_create_dir_text,
    get_create_dirs_report,
    get_create_dirs_text,
    get_delete_file_report,
    get_delete_file_text,
    get_delete_files_report,
    get_delete_files_text,
    get_move_file_report,
    get_move_file_text,
    get_move_files_report,
    get_move_files_text,
    serialize_file_transfer_list_report,
    serialize_file_transfer_report,
    serialize_path_action_report,
    serialize_path_list_report,
)
from .edit_text_commands import (
    format_line_edit_observation,
    format_line_edit_report_text,
    format_write_files_observation,
    format_write_files_report_text,
    get_append_file_report,
    get_append_file_text,
    get_check_append_file_report,
    get_check_append_file_text,
    get_check_insert_lines_report,
    get_check_insert_lines_text,
    get_check_replace_lines_report,
    get_check_replace_lines_text,
    get_check_write_file_report,
    get_check_write_file_text,
    get_check_write_files_report,
    get_check_write_files_text,
    get_insert_lines_report,
    get_insert_lines_text,
    get_replace_lines_report,
    get_replace_lines_text,
    get_write_file_report,
    get_write_file_text,
    get_write_files_report,
    get_write_files_text,
    serialize_line_edit_report,
    serialize_write_files_report,
)
from .types import (
    CheckEditFileAction,
    CheckMultiEditAction,
    ConfigCheckAction,
    EditFileAction,
    EditOperation,
    MultiEditAction,
)
from .workspace_core import RunWorkspace


def _plain_data(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, list):
        return [_plain_data(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _plain_data(item) for key, item in value.items()}
    return value


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


def get_config_check_text(project_root: str | Path = ".", argument: str | None = None, max_files: int = 200) -> str:
    return format_config_check_report_text(get_config_check_report(project_root, argument, max_files=max_files))


def get_config_check_report(project_root: str | Path = ".", argument: str | None = None, max_files: int = 200) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        path = parse_optional_single_path_argument(argument)
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "ok": False,
            "path": argument or ".",
            "files": {"shown": 0, "total": 0, "items": []},
            "truncated": False,
            "message": f"Usage: /config-check [path]\nError: {error}",
        }
    workspace = RunWorkspace(root=root, run_id="local-config-check", session_dir=root / ".vibeagent" / "sessions" / "local-config-check")
    observation = _execute_action(workspace, ConfigCheckAction(type="config_check", path=path, max_files=max_files))
    if observation.kind != "config_check":
        return {
            "projectRoot": str(root),
            "ok": False,
            "path": path or ".",
            "files": {"shown": 0, "total": 0, "items": []},
            "truncated": False,
            "message": f"Unexpected observation: {observation.kind}",
        }

    files = [_plain_data(item) for item in observation.files]
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "path": observation.path or ".",
        "files": {
            "shown": len(files),
            "total": observation.total,
            "items": files,
        },
        "truncated": observation.truncated,
        "message": observation.message,
    }


def format_config_check_report_text(report: dict[str, object]) -> str:
    files = report.get("files") if isinstance(report.get("files"), dict) else {}
    items = [item for item in files.get("items", []) if isinstance(item, dict)] if isinstance(files.get("items"), list) else []
    lines = [
        "Config check:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  path: {report.get('path') or '.'}",
        f"  files: {int(files.get('shown', len(items)) or 0)}/{int(files.get('total', len(items)) or 0)}",
        f"  truncated: {'yes' if bool(report.get('truncated')) else 'no'}",
        f"  message: {report.get('message') or ''}",
    ]
    if items:
        lines.append("  items:")
        for item in items:
            line = item.get("line") if isinstance(item.get("line"), int) else None
            column = item.get("column") if isinstance(item.get("column"), int) else None
            location = format_check_location(line, column)
            status = "ok" if bool(item.get("ok")) else "failed"
            lines.append(f"    - {item.get('path')} ({item.get('format')}): {status}{location} - {item.get('message')}")
    else:
        lines.append("  items: none")
    return "\n".join(lines)


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


from .edit_patch_commands import (
    format_executable_observation,
    format_executable_report_text,
    format_patch_observation,
    format_patch_report_text,
    format_patches_observation,
    format_patches_report_text,
    format_regex_replace_observation,
    format_regex_replace_report_text,
    get_check_patch_report,
    get_check_patch_text,
    get_check_patches_report,
    get_check_patches_text,
    get_check_regex_replace_report,
    get_check_regex_replace_text,
    get_check_set_executable_report,
    get_check_set_executable_text,
    get_patch_report,
    get_patch_text,
    get_patches_report,
    get_patches_text,
    get_regex_replace_report,
    get_regex_replace_text,
    get_set_executable_report,
    get_set_executable_text,
    serialize_executable_report,
    serialize_patch_report,
    serialize_patches_report,
    serialize_regex_replace_report,
)


def format_check_location(line: int | None, column: int | None) -> str:
    if line is None:
        return ""
    if column is None:
        return f" at line {line}"
    return f" at line {line}, column {column}"
