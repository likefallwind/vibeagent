from __future__ import annotations

from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action
from .edit_command_parsing import (
    parse_append_file_argument,
    parse_insert_lines_argument,
    parse_replace_lines_argument,
)
from .edit_text_formatting import (
    format_line_edit_observation,
    format_line_edit_report_text,
    format_write_files_observation,
    format_write_files_report_text,
    serialize_line_edit_report,
    serialize_write_files_report,
)
from .edit_write_commands import (
    get_check_write_file_report,
    get_check_write_file_text,
    get_check_write_files_report,
    get_check_write_files_text,
    get_write_file_report,
    get_write_file_text,
    get_write_files_report,
    get_write_files_text,
)
from .types import (
    AppendFileAction,
    CheckAppendFileAction,
    CheckInsertLinesAction,
    CheckReplaceLinesAction,
    InsertLinesAction,
    ReplaceLinesAction,
)
from .workspace_core import RunWorkspace


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


def get_check_replace_lines_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    start_line: int | None = None,
    end_line: int | None = None,
    content: str | None = None,
) -> str:
    get_report = _commands_attr("get_check_replace_lines_report", get_check_replace_lines_report)
    formatter = _commands_attr("format_line_edit_report_text", format_line_edit_report_text)
    return formatter(
        "Check replace lines:",
        get_report(project_root, argument, path=path, start_line=start_line, end_line=end_line, content=content),
    )

def get_check_replace_lines_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    start_line: int | None = None,
    end_line: int | None = None,
    content: str | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_path, parsed_start, parsed_end, parsed_content = parse_replace_lines_argument(
            argument,
            path=path,
            start_line=start_line,
            end_line=end_line,
            content=content,
            usage="/check-replace-lines <path> <start> <end> <text>",
        )
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "kind": "check_replace_lines",
            "ok": False,
            "path": path or "",
            "startLine": None,
            "endLine": None,
            "message": f"Usage: /check-replace-lines <path> <start> <end> <text>\nError: {error}",
            "diff": {"text": "", "lines": [], "lineCount": 0},
        }
    workspace = RunWorkspace(root=root, run_id="local-check-replace-lines", session_dir=root / ".vibeagent" / "sessions" / "local-check-replace-lines")
    observation = _execute_action(
        workspace,
        CheckReplaceLinesAction(type="check_replace_lines", path=parsed_path, start_line=parsed_start, end_line=parsed_end, content=parsed_content),
    )
    return serialize_line_edit_report(root, observation)


def get_replace_lines_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    start_line: int | None = None,
    end_line: int | None = None,
    content: str | None = None,
) -> str:
    get_report = _commands_attr("get_replace_lines_report", get_replace_lines_report)
    formatter = _commands_attr("format_line_edit_report_text", format_line_edit_report_text)
    return formatter(
        "Replace lines:",
        get_report(project_root, argument, path=path, start_line=start_line, end_line=end_line, content=content),
    )

def get_replace_lines_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    start_line: int | None = None,
    end_line: int | None = None,
    content: str | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_path, parsed_start, parsed_end, parsed_content = parse_replace_lines_argument(
            argument,
            path=path,
            start_line=start_line,
            end_line=end_line,
            content=content,
            usage="/replace-lines <path> <start> <end> <text>",
        )
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "kind": "replace_lines",
            "ok": False,
            "path": path or "",
            "startLine": None,
            "endLine": None,
            "message": f"Usage: /replace-lines <path> <start> <end> <text>\nError: {error}",
            "diff": {"text": "", "lines": [], "lineCount": 0},
        }
    workspace = RunWorkspace(root=root, run_id="local-replace-lines", session_dir=root / ".vibeagent" / "sessions" / "local-replace-lines")
    observation = _execute_action(
        workspace,
        ReplaceLinesAction(type="replace_lines", path=parsed_path, start_line=parsed_start, end_line=parsed_end, content=parsed_content),
    )
    return serialize_line_edit_report(root, observation)


def get_check_insert_lines_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    line: int | None = None,
    content: str | None = None,
) -> str:
    return format_line_edit_report_text(
        "Check insert lines:",
        get_check_insert_lines_report(project_root, argument, path=path, line=line, content=content),
    )


def get_check_insert_lines_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    line: int | None = None,
    content: str | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_path, parsed_line, parsed_content = parse_insert_lines_argument(
            argument,
            path=path,
            line=line,
            content=content,
            usage="/check-insert-lines <path> <line> <text>",
        )
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "kind": "check_insert_lines",
            "ok": False,
            "path": path or "",
            "line": None,
            "message": f"Usage: /check-insert-lines <path> <line> <text>\nError: {error}",
            "diff": {"text": "", "lines": [], "lineCount": 0},
        }
    workspace = RunWorkspace(root=root, run_id="local-check-insert-lines", session_dir=root / ".vibeagent" / "sessions" / "local-check-insert-lines")
    observation = _execute_action(workspace, CheckInsertLinesAction(type="check_insert_lines", path=parsed_path, line=parsed_line, content=parsed_content))
    return serialize_line_edit_report(root, observation)


def get_insert_lines_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    line: int | None = None,
    content: str | None = None,
) -> str:
    get_report = _commands_attr("get_insert_lines_report", get_insert_lines_report)
    formatter = _commands_attr("format_line_edit_report_text", format_line_edit_report_text)
    return formatter("Insert lines:", get_report(project_root, argument, path=path, line=line, content=content))

def get_insert_lines_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    line: int | None = None,
    content: str | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_path, parsed_line, parsed_content = parse_insert_lines_argument(
            argument,
            path=path,
            line=line,
            content=content,
            usage="/insert-lines <path> <line> <text>",
        )
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "kind": "insert_lines",
            "ok": False,
            "path": path or "",
            "line": None,
            "message": f"Usage: /insert-lines <path> <line> <text>\nError: {error}",
            "diff": {"text": "", "lines": [], "lineCount": 0},
        }
    workspace = RunWorkspace(root=root, run_id="local-insert-lines", session_dir=root / ".vibeagent" / "sessions" / "local-insert-lines")
    observation = _execute_action(workspace, InsertLinesAction(type="insert_lines", path=parsed_path, line=parsed_line, content=parsed_content))
    return serialize_line_edit_report(root, observation)


def get_check_append_file_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    content: str | None = None,
) -> str:
    return format_line_edit_report_text(
        "Check append:",
        get_check_append_file_report(project_root, argument, path=path, content=content),
    )


def get_check_append_file_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    content: str | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_path, parsed_content = parse_append_file_argument(
            argument,
            path=path,
            content=content,
            usage="/check-append <path> <text>",
        )
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "kind": "check_append_file",
            "ok": False,
            "path": path or "",
            "message": f"Usage: /check-append <path> <text>\nError: {error}",
            "diff": {"text": "", "lines": [], "lineCount": 0},
        }
    workspace = RunWorkspace(root=root, run_id="local-check-append", session_dir=root / ".vibeagent" / "sessions" / "local-check-append")
    observation = _execute_action(workspace, CheckAppendFileAction(type="check_append_file", path=parsed_path, content=parsed_content))
    return serialize_line_edit_report(root, observation)


def get_append_file_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    content: str | None = None,
) -> str:
    get_report = _commands_attr("get_append_file_report", get_append_file_report)
    formatter = _commands_attr("format_line_edit_report_text", format_line_edit_report_text)
    return formatter("Append:", get_report(project_root, argument, path=path, content=content))

def get_append_file_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    content: str | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_path, parsed_content = parse_append_file_argument(
            argument,
            path=path,
            content=content,
            usage="/append <path> <text>",
        )
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "kind": "append_file",
            "ok": False,
            "path": path or "",
            "message": f"Usage: /append <path> <text>\nError: {error}",
            "diff": {"text": "", "lines": [], "lineCount": 0},
        }
    workspace = RunWorkspace(root=root, run_id="local-append", session_dir=root / ".vibeagent" / "sessions" / "local-append")
    observation = _execute_action(workspace, AppendFileAction(type="append_file", path=parsed_path, content=parsed_content))
    return serialize_line_edit_report(root, observation)

