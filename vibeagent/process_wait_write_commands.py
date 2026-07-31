from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action
from .local_command_workspace import local_command_workspace
from .process_request_parsing import parse_positive_decimal, split_process_argument, validate_max_output_chars
from .process_report_helpers import (
    empty_command_output_analysis,
    format_structured_command_output_analysis_lines,
    indent_block as _indent_block,
    process_status_text,
    serialize_command_output_analysis,
)
from .process_write_commands import (
    CHECK_WRITE_PROCESS_USAGE,
    WRITE_PROCESS_USAGE,
    decode_stdin_escapes,
    format_check_write_process_report_text,
    format_write_process_report_text,
    get_check_write_process_report,
    get_check_write_process_text,
    get_write_process_report,
    get_write_process_text,
    parse_write_process_request,
    serialize_write_process_report,
)
from .types import WaitProcessAction

WAIT_PROCESS_USAGE = "Usage: /wait-process <id> [timeout-ms] [chars]"


def _wait_process_failure_report(
    root: Path,
    process_id: str,
    timeout_ms: int,
    max_output_chars: int | None,
    message: str,
) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "processId": process_id,
        "pid": None,
        "status": "unknown",
        "running": False,
        "timedOut": False,
        "matched": False,
        "matchedStream": None,
        "matchedPattern": None,
        "timeoutMs": timeout_ms,
        "exitCode": None,
        "signal": None,
        "maxOutputChars": max_output_chars,
        "stdout": "",
        "stderr": "",
        "analysis": empty_command_output_analysis(),
        "message": message,
    }


def _usage_error(usage: str, error: object) -> str:
    return f"{usage}\nError: {error}"


def _yes_no(value: object) -> str:
    return "yes" if bool(value) else "no"


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


def get_wait_process_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    process_id: str | None = None,
    timeout_ms: int = 5_000,
    max_output_chars: int | None = None,
    stdout_contains: str | None = None,
    stderr_contains: str | None = None,
    regex: bool = False,
) -> str:
    get_report = _process_command_function("get_wait_process_report", get_wait_process_report)
    format_report = _process_command_function("format_wait_process_report_text", format_wait_process_report_text)
    return format_report(
        get_report(
            project_root,
            argument,
            process_id,
            timeout_ms,
            max_output_chars,
            stdout_contains,
            stderr_contains,
            regex,
        )
    )


def get_wait_process_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    process_id: str | None = None,
    timeout_ms: int = 5_000,
    max_output_chars: int | None = None,
    stdout_contains: str | None = None,
    stderr_contains: str | None = None,
    regex: bool = False,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        selected_process_id, selected_timeout, selected_max = parse_wait_process_request(
            argument,
            process_id,
            timeout_ms,
            max_output_chars,
        )
    except ValueError as error:
        return _wait_process_failure_report(
            root,
            process_id or "",
            timeout_ms,
            max_output_chars,
            _usage_error(WAIT_PROCESS_USAGE, error),
        )

    workspace = local_command_workspace(root, "local-wait-process")
    observation = _execute_action(
        workspace,
        WaitProcessAction(
            type="wait_process",
            process_id=selected_process_id,
            timeout_ms=selected_timeout,
            stdout_contains=stdout_contains,
            stderr_contains=stderr_contains,
            regex=regex,
            max_output_chars=selected_max,
        ),
    )
    if observation.kind != "wait_process":
        return _wait_process_failure_report(
            root,
            selected_process_id,
            selected_timeout,
            selected_max,
            f"Unexpected observation: {observation.kind}",
        )

    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "processId": observation.process_id,
        "pid": observation.pid,
        "status": process_status_text(observation.running, observation.exit_code, observation.signal),
        "running": observation.running,
        "timedOut": observation.timed_out,
        "matched": observation.matched,
        "matchedStream": observation.matched_stream,
        "matchedPattern": observation.matched_pattern,
        "timeoutMs": observation.timeout_ms,
        "exitCode": observation.exit_code,
        "signal": observation.signal,
        "maxOutputChars": observation.max_output_chars,
        "stdout": observation.stdout,
        "stderr": observation.stderr,
        "analysis": serialize_command_output_analysis(observation),
        "message": observation.message,
    }


def format_wait_process_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    analysis = report.get("analysis") if isinstance(report.get("analysis"), dict) else {}
    lines = [
        "Wait process:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {_yes_no(report.get('ok'))}",
        f"  processId: {report.get('processId') or ''}",
        f"  pid: {report.get('pid') if report.get('pid') is not None else '.'}",
        f"  status: {report.get('status') or 'unknown'}",
        f"  timedOut: {_yes_no(report.get('timedOut'))}",
        f"  matched: {_yes_no(report.get('matched'))}",
        f"  matchedStream: {report.get('matchedStream') or '.'}",
        f"  matchedPattern: {report.get('matchedPattern') or '.'}",
        f"  timeoutMs: {report.get('timeoutMs', 0)}",
        f"  maxOutputChars: {report.get('maxOutputChars', 0)}",
        f"  message: {message}",
    ]
    stdout = str(report.get("stdout") or "")
    stderr = str(report.get("stderr") or "")
    if stdout:
        lines.append("  stdout:")
        lines.append(_indent_block(stdout.rstrip(), spaces=4))
    else:
        lines.append("  stdout: none")
    if stderr:
        lines.append("  stderr:")
        lines.append(_indent_block(stderr.rstrip(), spaces=4))
    else:
        lines.append("  stderr: none")
    lines.extend(format_structured_command_output_analysis_lines(analysis, spaces=2))
    return "\n".join(lines)


def parse_wait_process_request(
    argument: str | None = None,
    process_id: str | None = None,
    timeout_ms: int = 5_000,
    max_output_chars: int | None = None,
) -> tuple[str, int, int | None]:
    selected_process_id = process_id.strip() if process_id else None
    selected_timeout = timeout_ms
    selected_max = max_output_chars
    if argument and argument.strip() and process_id is not None:
        raise ValueError("wait-process argument cannot be combined with explicit process_id.")
    parts = split_process_argument(
        argument,
        max_parts=3,
        too_many_message="expected process id, optional timeout ms, and optional max chars.",
    )
    if parts:
        selected_process_id = parts[0]
        if len(parts) >= 2:
            selected_timeout = parse_positive_decimal(parts[1], "timeout ms")
        if len(parts) == 3:
            selected_max = parse_positive_decimal(parts[2], "max chars")
    if not selected_process_id:
        raise ValueError("process id is required.")
    if selected_timeout < 100:
        raise ValueError("timeout ms must be at least 100.")
    if selected_timeout > 600_000:
        raise ValueError("timeout ms must be at most 600000.")
    validate_max_output_chars(selected_max)
    return selected_process_id, selected_timeout, selected_max
