from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action
from .command_parsing import parse_local_path_args
from .local_command_workspace import local_command_workspace
from .read_command_parsing import parse_read_ranges_argument, serialize_read_range_result, serialize_read_result
from .read_report_helpers import format_read_files_report_text, format_read_ranges_report_text
from .types import ReadFileRangesAction, ReadFilesAction


def _execute_action(*args: object, **kwargs: object) -> object:
    commands_module = sys.modules.get("vibeagent.read_commands")
    command_execute_action = getattr(commands_module, "execute_action", None) if commands_module is not None else None
    if command_execute_action is not None:
        return command_execute_action(*args, **kwargs)
    return _default_execute_action(*args, **kwargs)


def _read_command_function(name: str, default: Callable[..., object]) -> Callable[..., object]:
    commands_module = sys.modules.get("vibeagent.read_commands")
    candidate = getattr(commands_module, name, None) if commands_module is not None else None
    return candidate if callable(candidate) else default


def get_read_files_text(
    project_root: str | Path = ".",
    argument: str | list[str] | None = None,
    max_bytes_per_file: int = 20_000,
    show_line_numbers: bool = False,
) -> str:
    get_report = _read_command_function("get_read_files_report", get_read_files_report)
    format_report = _read_command_function("format_read_files_report_text", format_read_files_report_text)
    return format_report(
        get_report(
            project_root,
            argument,
            max_bytes_per_file=max_bytes_per_file,
            show_line_numbers=show_line_numbers,
        )
    )


def get_read_files_report(
    project_root: str | Path = ".",
    argument: str | list[str] | None = None,
    max_bytes_per_file: int = 20_000,
    show_line_numbers: bool = False,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    if max_bytes_per_file < 1_000:
        return _read_files_usage_report(
            root,
            max_bytes_per_file,
            show_line_numbers,
            "Usage: /read-files <path...>\nError: max_bytes_per_file must be at least 1000.",
        )
    if max_bytes_per_file > 200_000:
        return _read_files_usage_report(
            root,
            max_bytes_per_file,
            show_line_numbers,
            "Usage: /read-files <path...>\nError: max_bytes_per_file must be at most 200000.",
        )
    try:
        paths = parse_local_path_args(argument, max_paths=20)
    except ValueError as error:
        return _read_files_usage_report(
            root,
            max_bytes_per_file,
            show_line_numbers,
            f"Usage: /read-files <path...>\nError: {error}",
        )
    if not paths:
        return _read_files_usage_report(
            root,
            max_bytes_per_file,
            show_line_numbers,
            "Usage: /read-files <path...>",
        )

    workspace = local_command_workspace(root, "local-read-files")
    observation = _execute_action(
        workspace,
        ReadFilesAction(
            type="read_files",
            paths=paths,
            max_bytes_per_file=max_bytes_per_file,
            show_line_numbers=show_line_numbers,
        ),
    )
    if observation.kind != "read_files":
        return {
            "projectRoot": str(root),
            "ok": False,
            "files": {"ok": 0, "total": len(paths), "items": []},
            "maxBytesPerFile": max_bytes_per_file,
            "showLineNumbers": show_line_numbers,
            "message": f"Unexpected observation: {observation.kind}",
        }
    items = [serialize_read_result(item) for item in observation.files]
    ok_count = sum(1 for item in items if bool(item["ok"]))
    return {
        "projectRoot": str(root),
        "ok": ok_count == len(items),
        "files": {"ok": ok_count, "total": len(items), "items": items},
        "maxBytesPerFile": max_bytes_per_file,
        "showLineNumbers": show_line_numbers,
        "message": observation.message,
    }


def get_read_ranges_text(
    project_root: str | Path = ".",
    argument: str | list[str] | None = None,
    max_bytes_per_range: int = 20_000,
) -> str:
    get_report = _read_command_function("get_read_ranges_report", get_read_ranges_report)
    format_report = _read_command_function("format_read_ranges_report_text", format_read_ranges_report_text)
    return format_report(get_report(project_root, argument, max_bytes_per_range=max_bytes_per_range))


def get_read_ranges_report(
    project_root: str | Path = ".",
    argument: str | list[str] | None = None,
    max_bytes_per_range: int = 20_000,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    if max_bytes_per_range < 1_000:
        return _read_ranges_usage_report(
            root,
            max_bytes_per_range,
            "Usage: /read-ranges <path:start[:end]...>\nError: max_bytes_per_range must be at least 1000.",
        )
    if max_bytes_per_range > 200_000:
        return _read_ranges_usage_report(
            root,
            max_bytes_per_range,
            "Usage: /read-ranges <path:start[:end]...>\nError: max_bytes_per_range must be at most 200000.",
        )
    try:
        ranges = parse_read_ranges_argument(argument)
    except ValueError as error:
        return _read_ranges_usage_report(
            root,
            max_bytes_per_range,
            f"Usage: /read-ranges <path:start[:end]...>\nError: {error}",
        )
    if not ranges:
        return _read_ranges_usage_report(
            root,
            max_bytes_per_range,
            "Usage: /read-ranges <path:start[:end]...>",
        )

    workspace = local_command_workspace(root, "local-read-ranges")
    observation = _execute_action(
        workspace,
        ReadFileRangesAction(type="read_file_ranges", ranges=ranges, max_bytes_per_range=max_bytes_per_range),
    )
    if observation.kind != "read_file_ranges":
        return {
            "projectRoot": str(root),
            "ok": False,
            "ranges": {"ok": 0, "total": len(ranges), "items": []},
            "maxBytesPerRange": max_bytes_per_range,
            "message": f"Unexpected observation: {observation.kind}",
        }
    items = [serialize_read_range_result(item) for item in observation.ranges]
    ok_count = sum(1 for item in items if bool(item["ok"]))
    return {
        "projectRoot": str(root),
        "ok": ok_count == len(items),
        "ranges": {"ok": ok_count, "total": len(items), "items": items},
        "maxBytesPerRange": max_bytes_per_range,
        "message": observation.message,
    }


def _read_files_usage_report(
    root: Path,
    max_bytes_per_file: int,
    show_line_numbers: bool,
    message: str,
) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "files": {"ok": 0, "total": 0, "items": []},
        "maxBytesPerFile": max_bytes_per_file,
        "showLineNumbers": show_line_numbers,
        "message": message,
    }


def _read_ranges_usage_report(root: Path, max_bytes_per_range: int, message: str) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "ranges": {"ok": 0, "total": 0, "items": []},
        "maxBytesPerRange": max_bytes_per_range,
        "message": message,
    }
