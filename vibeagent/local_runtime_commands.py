from __future__ import annotations

from pathlib import Path

from .actions import build_command_check_observation
from .local_http_commands import (
    format_http_fetch_report_text,
    format_http_report_text,
    format_port_report_text,
    get_http_fetch_report,
    get_http_fetch_text,
    get_http_report,
    get_http_text,
    get_port_report,
    get_port_text,
    parse_http_fetch_request,
    parse_http_request,
    parse_port_request,
    serialize_http_report,
)
from .local_run_commands import (
    get_check_run_sequence_report,
    get_check_run_sequence_text,
    get_run_report,
    get_run_sequence_report,
    get_run_sequence_text,
    get_run_text,
    parse_run_sequence_request,
)
from .local_runtime_execution import execute_local_action
from .local_runtime_reports import (
    empty_command_output_analysis,
    format_check_run_sequence_report_text,
    format_check_start_report_text,
    format_command_check_report_text,
    format_command_output_context_lines,
    format_command_output_diagnostic_lines,
    format_run_report_text,
    format_run_sequence_report_text,
    format_start_report_text,
    format_structured_command_output_analysis_lines,
    indent_block as _indent_block,
    command_results_clean,
    serialize_command_check,
    serialize_command_output_analysis,
    serialize_command_result,
    sum_command_result_duration_ms,
    validate_run_output_context_options,
)
from .types import (
    CheckStartCommandAction,
    StartCommandAction,
)
from .workspace_core import RunWorkspace


def get_command_check_text(project_root: str | Path = ".", command: str | None = None, cwd: str | None = None) -> str:
    return format_command_check_report_text(get_command_check_report(project_root, command, cwd))


def get_command_check_report(project_root: str | Path = ".", command: str | None = None, cwd: str | None = None) -> dict[str, object]:
    root = Path(project_root).resolve()
    if command is None or not command.strip():
        return {
            "projectRoot": str(root),
            "command": "",
            "cwd": cwd or ".",
            "ok": False,
            "cwdOk": False,
            "blocked": False,
            "executableAvailable": False,
            "blockReason": None,
            "missingTool": None,
            "message": "Usage: /command <shell command>",
        }
    workspace = RunWorkspace(root=root, run_id="local-command-check", session_dir=root / ".vibeagent" / "sessions" / "local-command-check")
    observation = build_command_check_observation(workspace, command.strip(), cwd)
    return {
        "projectRoot": str(root),
        **serialize_command_check(observation),
    }


def get_check_start_text(project_root: str | Path = ".", command: str | None = None, cwd: str | None = None) -> str:
    return format_check_start_report_text(get_check_start_report(project_root, command, cwd=cwd))


def get_check_start_report(project_root: str | Path = ".", command: str | None = None, cwd: str | None = None) -> dict[str, object]:
    root = Path(project_root).resolve()

    def failure(message: str) -> dict[str, object]:
        return {
            "projectRoot": str(root),
            "command": (command or "").strip(),
            "cwd": cwd or ".",
            "ok": False,
            "cwdOk": False,
            "blocked": False,
            "executableAvailable": False,
            "blockReason": None,
            "missingTool": None,
            "message": message,
        }

    if command is None or not command.strip():
        return failure("Usage: /check-start <shell command>")
    workspace = RunWorkspace(root=root, run_id="local-check-start", session_dir=root / ".vibeagent" / "sessions" / "local-check-start")
    observation = execute_local_action(
        workspace,
        CheckStartCommandAction(type="check_start_command", command=command.strip(), cwd=cwd),
    )
    if observation.kind != "check_start_command":
        return failure(f"Unexpected observation: {observation.kind}")

    return {
        "projectRoot": str(root),
        **serialize_command_check(observation),
    }

def get_start_text(project_root: str | Path = ".", command: str | None = None, cwd: str | None = None) -> str:
    return format_start_report_text(get_start_report(project_root, command, cwd=cwd))


def get_start_report(project_root: str | Path = ".", command: str | None = None, cwd: str | None = None) -> dict[str, object]:
    root = Path(project_root).resolve()

    def failure(message: str) -> dict[str, object]:
        return {
            "projectRoot": str(root),
            "ok": False,
            "command": (command or "").strip(),
            "cwd": cwd or ".",
            "processId": "",
            "pid": None,
            "stdoutPath": "",
            "stderrPath": "",
            "message": message,
        }

    if command is None or not command.strip():
        return failure("Usage: /start <shell command>")

    workspace = RunWorkspace(root=root, run_id="local-start", session_dir=root / ".vibeagent" / "sessions" / "local-start")
    observation = execute_local_action(
        workspace,
        StartCommandAction(type="start_command", command=command.strip(), cwd=cwd),
    )
    if observation.kind != "start_command":
        return failure(f"Unexpected observation: {observation.kind}")

    return {
        "projectRoot": str(root),
        "command": observation.command,
        "cwd": observation.cwd,
        "ok": observation.ok,
        "processId": observation.process_id,
        "pid": observation.pid,
        "stdoutPath": observation.stdout_path,
        "stderrPath": observation.stderr_path,
        "message": observation.message,
    }
