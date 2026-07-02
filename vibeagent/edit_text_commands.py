from __future__ import annotations

from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action
from .edit_command_parsing import (
    parse_append_file_argument,
    parse_insert_lines_argument,
    parse_replace_lines_argument,
    parse_write_file_argument,
    parse_write_file_list_argument,
)
from .types import (
    AppendFileAction,
    CheckAppendFileAction,
    CheckInsertLinesAction,
    CheckReplaceLinesAction,
    CheckWriteFileAction,
    CheckWriteFilesAction,
    InsertLinesAction,
    ReplaceLinesAction,
    WriteFileAction,
    WriteFileItem,
    WriteFilesAction,
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


def get_check_write_file_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    content: str | None = None,
) -> str:
    return format_line_edit_report_text(
        "Check write:",
        get_check_write_file_report(project_root, argument, path=path, content=content),
    )


def get_check_write_file_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    content: str | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_path, parsed_content = parse_write_file_argument(
            argument,
            path=path,
            content=content,
            usage="/check-write <path> <text>",
        )
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "kind": "check_write_file",
            "ok": False,
            "path": path or "",
            "message": f"Usage: /check-write <path> <text>\nError: {error}",
            "diff": {"text": "", "lines": [], "lineCount": 0},
        }
    workspace = RunWorkspace(root=root, run_id="local-check-write", session_dir=root / ".vibeagent" / "sessions" / "local-check-write")
    observation = _execute_action(workspace, CheckWriteFileAction(type="check_write_file", path=parsed_path, content=parsed_content))
    return serialize_line_edit_report(root, observation)


def get_write_file_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    content: str | None = None,
) -> str:
    get_report = _commands_attr("get_write_file_report", get_write_file_report)
    formatter = _commands_attr("format_line_edit_report_text", format_line_edit_report_text)
    return formatter("Write:", get_report(project_root, argument, path=path, content=content))

def get_write_file_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    content: str | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_path, parsed_content = parse_write_file_argument(
            argument,
            path=path,
            content=content,
            usage="/write <path> <text>",
        )
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "kind": "write_file",
            "ok": False,
            "path": path or "",
            "message": f"Usage: /write <path> <text>\nError: {error}",
            "diff": {"text": "", "lines": [], "lineCount": 0},
        }
    workspace = RunWorkspace(root=root, run_id="local-write", session_dir=root / ".vibeagent" / "sessions" / "local-write")
    observation = _execute_action(workspace, WriteFileAction(type="write_file", path=parsed_path, content=parsed_content))
    return serialize_line_edit_report(root, observation)


def get_check_write_files_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    files: list[WriteFileItem] | list[str] | None = None,
) -> str:
    return format_write_files_report_text(
        "Check write files:",
        get_check_write_files_report(project_root, argument, files=files),
    )


def get_check_write_files_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    files: list[WriteFileItem] | list[str] | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_files = parse_write_file_list_argument(argument, files=files, usage="/check-write-files <path> <text>...")
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "kind": "check_write_files",
            "ok": False,
            "files": {"total": 0, "items": []},
            "message": f"Usage: /check-write-files <path> <text>...\nError: {error}",
        }
    workspace = RunWorkspace(root=root, run_id="local-check-write-files", session_dir=root / ".vibeagent" / "sessions" / "local-check-write-files")
    observation = _execute_action(workspace, CheckWriteFilesAction(type="check_write_files", files=parsed_files))
    return serialize_write_files_report(root, observation)


def get_write_files_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    files: list[WriteFileItem] | list[str] | None = None,
) -> str:
    get_report = _commands_attr("get_write_files_report", get_write_files_report)
    formatter = _commands_attr("format_write_files_report_text", format_write_files_report_text)
    return formatter("Write files:", get_report(project_root, argument, files=files))

def get_write_files_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    files: list[WriteFileItem] | list[str] | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_files = parse_write_file_list_argument(argument, files=files, usage="/write-files <path> <text>...")
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "kind": "write_files",
            "ok": False,
            "files": {"total": 0, "items": []},
            "message": f"Usage: /write-files <path> <text>...\nError: {error}",
        }
    workspace = RunWorkspace(root=root, run_id="local-write-files", session_dir=root / ".vibeagent" / "sessions" / "local-write-files")
    observation = _execute_action(workspace, WriteFilesAction(type="write_files", files=parsed_files))
    return serialize_write_files_report(root, observation)


def format_write_files_observation(title: str, root: Path, observation: object) -> str:
    return format_write_files_report_text(title, serialize_write_files_report(root, observation))


def serialize_write_files_report(root: Path, observation: object) -> dict[str, object]:
    file_reports: list[dict[str, object]] = []
    for file in list(getattr(observation, "files", [])):
        diff = str(getattr(file, "diff", "") or "")
        file_reports.append(
            {
                "path": str(getattr(file, "path", "") or ""),
                "ok": bool(getattr(file, "ok", False)),
                "message": str(getattr(file, "message", "") or ""),
                "diff": {"text": diff, "lines": diff.splitlines(), "lineCount": len(diff.splitlines())},
            }
        )
    return {
        "projectRoot": str(root),
        "kind": str(getattr(observation, "kind", "") or ""),
        "ok": bool(getattr(observation, "ok", False)),
        "files": {"total": len(file_reports), "items": file_reports},
        "message": str(getattr(observation, "message", "") or ""),
    }


def format_write_files_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    files_report = report.get("files") if isinstance(report.get("files"), dict) else {}
    items = [item for item in files_report.get("items", []) if isinstance(item, dict)] if isinstance(files_report.get("items"), list) else []
    lines = [
        title,
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  files: {int(files_report.get('total', len(items)) or 0)}",
        f"  message: {message}",
    ]
    if items:
        lines.append("  items:")
        for file in items:
            lines.append(f"    - {file.get('path') or ''}: {'ok' if bool(file.get('ok')) else 'failed'} - {file.get('message') or ''}")
            diff_report = file.get("diff") if isinstance(file.get("diff"), dict) else {}
            diff = str(diff_report.get("text") or "")
            if diff:
                lines.append("      diff:")
                for diff_line in diff.splitlines():
                    lines.append(f"        {diff_line}")
    return "\n".join(lines)


def format_line_edit_observation(title: str, root: Path, observation: object) -> str:
    return format_line_edit_report_text(title, serialize_line_edit_report(root, observation))


def serialize_line_edit_report(root: Path, observation: object) -> dict[str, object]:
    diff = str(getattr(observation, "diff", "") or "")
    report: dict[str, object] = {
        "projectRoot": str(root),
        "kind": str(getattr(observation, "kind", "")),
        "ok": bool(getattr(observation, "ok", False)),
        "path": str(getattr(observation, "path", "") or ""),
        "message": str(getattr(observation, "message", "") or ""),
        "diff": {"text": diff, "lines": diff.splitlines(), "lineCount": len(diff.splitlines())},
    }
    if hasattr(observation, "start_line"):
        report["startLine"] = getattr(observation, "start_line")
    if hasattr(observation, "end_line"):
        report["endLine"] = getattr(observation, "end_line")
    if hasattr(observation, "line"):
        report["line"] = getattr(observation, "line")
    return report


def format_line_edit_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    lines = [
        title,
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  path: {report.get('path') or ''}",
    ]
    if "startLine" in report and "endLine" in report:
        lines.append(f"  range: {report.get('startLine')}-{report.get('endLine')}")
    if "line" in report:
        lines.append(f"  line: {report.get('line')}")
    lines.append(f"  message: {message}")
    diff_report = report.get("diff") if isinstance(report.get("diff"), dict) else {}
    diff = str(diff_report.get("text") or "")
    if diff:
        lines.append("  diff:")
        for diff_line in diff.splitlines():
            lines.append(f"    {diff_line}")
    return "\n".join(lines)


