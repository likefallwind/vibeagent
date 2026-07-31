from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action
from .cli_process_stdin import parse_process_stdin_file_argument, read_project_stdin_file
from .local_command_workspace import local_command_workspace
from .process_request_parsing import parse_single_quoted_argument
from .types import CheckWriteProcessAction, WriteProcessAction

WRITE_PROCESS_USAGE = "Usage: /write-process <id> <text> [--stdin-file PATH]"
CHECK_WRITE_PROCESS_USAGE = "Usage: /check-write-process <id> <text> [--stdin-file PATH]"


def _usage_error(usage: str, error: object) -> str:
    return f"{usage}\nError: {error}"


def _yes_no(value: object) -> str:
    return "yes" if bool(value) else "no"


def _write_process_failure_report(
    root: Path,
    process_id: str,
    content_chars: int,
    message: str,
    stdin_file: str | None = None,
) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "processId": process_id,
        "pid": None,
        "running": False,
        "command": "",
        "cwd": "",
        "contentChars": content_chars,
        "stdinFile": stdin_file or "",
        "message": message,
    }


def _execute_action(*args: object, **kwargs: object) -> object:
    commands_module = sys.modules.get("vibeagent.process_commands")
    command_execute_action = getattr(commands_module, "execute_action", None) if commands_module is not None else None
    if command_execute_action is not None:
        return command_execute_action(*args, **kwargs)
    return _default_execute_action(*args, **kwargs)


def _process_command_function(name: str, default: Callable[..., object]) -> Callable[..., object]:
    commands_module = sys.modules.get("vibeagent.process_commands")
    candidate = getattr(commands_module, name, None) if commands_module is not None else None
    return candidate if callable(candidate) else default


def get_write_process_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    process_id: str | None = None,
    content: str | None = None,
    stdin_file: str | None = None,
) -> str:
    get_report = _process_command_function("get_write_process_report", get_write_process_report)
    format_report = _process_command_function("format_write_process_report_text", format_write_process_report_text)
    return format_report(get_report(project_root, argument, process_id, content, stdin_file))


def get_write_process_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    process_id: str | None = None,
    content: str | None = None,
    stdin_file: str | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        selected_process_id, selected_content, selected_stdin_file = parse_write_process_request(
            argument,
            process_id,
            content,
            stdin_file,
            project_root=root,
        )
    except ValueError as error:
        return _write_process_failure_report(
            root,
            process_id or "",
            len(content or ""),
            _usage_error(WRITE_PROCESS_USAGE, error),
            stdin_file,
        )

    workspace = local_command_workspace(root, "local-write-process")
    observation = _execute_action(
        workspace,
        WriteProcessAction(
            type="write_process",
            process_id=selected_process_id,
            content=selected_content,
            stdin_file=selected_stdin_file,
        ),
    )
    if observation.kind != "write_process":
        return _write_process_failure_report(
            root,
            selected_process_id,
            len(selected_content or ""),
            f"Unexpected observation: {observation.kind}",
            selected_stdin_file,
        )

    return serialize_write_process_report(root, observation)


def format_write_process_report_text(report: dict[str, object]) -> str:
    return _format_write_like_process_report_text("Write process", report)


def get_check_write_process_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    process_id: str | None = None,
    content: str | None = None,
    stdin_file: str | None = None,
) -> str:
    get_report = _process_command_function("get_check_write_process_report", get_check_write_process_report)
    format_report = _process_command_function("format_check_write_process_report_text", format_check_write_process_report_text)
    return format_report(get_report(project_root, argument, process_id, content, stdin_file))


def get_check_write_process_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    process_id: str | None = None,
    content: str | None = None,
    stdin_file: str | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        selected_process_id, selected_content, selected_stdin_file = parse_write_process_request(
            argument,
            process_id,
            content,
            stdin_file,
            project_root=root,
        )
    except ValueError as error:
        return _write_process_failure_report(
            root,
            process_id or "",
            len(content or ""),
            _usage_error(CHECK_WRITE_PROCESS_USAGE, error),
            stdin_file,
        )

    workspace = local_command_workspace(root, "local-check-write-process")
    observation = _execute_action(
        workspace,
        CheckWriteProcessAction(
            type="check_write_process",
            process_id=selected_process_id,
            content=selected_content,
            stdin_file=selected_stdin_file,
        ),
    )
    if observation.kind != "check_write_process":
        return _write_process_failure_report(
            root,
            selected_process_id,
            len(selected_content or ""),
            f"Unexpected observation: {observation.kind}",
            selected_stdin_file,
        )

    return serialize_write_process_report(root, observation)


def format_check_write_process_report_text(report: dict[str, object]) -> str:
    return _format_write_like_process_report_text("Check write process", report)


def _format_write_like_process_report_text(title: str, report: dict[str, object]) -> str:
    lines = [
        f"{title}:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {_yes_no(report.get('ok'))}",
        f"  processId: {report.get('processId') or ''}",
        f"  pid: {report.get('pid') if report.get('pid') is not None else '.'}",
        f"  running: {_yes_no(report.get('running'))}",
        f"  command: {report.get('command') or '.'}",
        f"  cwd: {report.get('cwd') or '.'}",
        f"  contentChars: {int(report.get('contentChars', 0) or 0)}",
        f"  stdinFile: {report.get('stdinFile') or '.'}",
        f"  message: {report.get('message') or ''}",
    ]
    return "\n".join(lines)


def serialize_write_process_report(root: Path, observation: object) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": bool(getattr(observation, "ok", False)),
        "processId": str(getattr(observation, "process_id", "") or ""),
        "pid": getattr(observation, "pid", None),
        "running": bool(getattr(observation, "running", False)),
        "command": str(getattr(observation, "command", "") or ""),
        "cwd": str(getattr(observation, "cwd", "") or ""),
        "contentChars": int(getattr(observation, "content_chars", 0) or 0),
        "stdinFile": str(getattr(observation, "stdin_file", "") or ""),
        "message": str(getattr(observation, "message", "") or ""),
    }


def parse_write_process_request(
    argument: str | None = None,
    process_id: str | None = None,
    content: str | None = None,
    stdin_file: str | None = None,
    *,
    project_root: str | Path = ".",
) -> tuple[str, str | None, str | None]:
    selected_process_id = process_id.strip() if process_id else None
    selected_content = content
    selected_stdin_file = stdin_file
    if selected_stdin_file is not None and selected_stdin_file.strip() == "":
        raise ValueError("stdin_file must be a non-empty path.")
    if selected_content is not None and selected_stdin_file is not None:
        raise ValueError("content and stdin_file cannot be used together.")
    if argument and argument.strip():
        if process_id is not None or content is not None or stdin_file is not None:
            raise ValueError("write-process argument cannot be combined with explicit process_id, content, or stdin_file.")
        if "--stdin-file" in argument:
            parsed = parse_process_stdin_file_argument(argument, project_root=project_root)
            selected_process_id = parsed.process_id
            selected_content = parsed.content
            selected_stdin_file = parsed.stdin_file
            if not selected_process_id:
                raise ValueError("process id is required.")
            if selected_content is None or selected_content == "":
                raise ValueError("stdin text is required.")
            return selected_process_id, None, selected_stdin_file
        else:
            parts = argument.strip().split(maxsplit=1)
            if parts:
                selected_process_id = parts[0]
            selected_content = parse_single_quoted_argument(parts[1]) if len(parts) > 1 else None
    if not selected_process_id:
        raise ValueError("process id is required.")
    if selected_stdin_file is not None:
        file_content = read_project_stdin_file(project_root, selected_stdin_file, "stdin_file")
        if file_content is None or file_content == "":
            raise ValueError("stdin text is required.")
        return selected_process_id, None, selected_stdin_file
    if selected_content is None or selected_content == "":
        raise ValueError("stdin text is required.")
    return selected_process_id, decode_stdin_escapes(selected_content), None


def decode_stdin_escapes(value: str) -> str:
    return value.replace("\\r", "\r").replace("\\n", "\n").replace("\\t", "\t")
