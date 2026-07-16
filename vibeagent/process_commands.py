from __future__ import annotations

from pathlib import Path

from .actions import execute_action
from .local_command_workspace import local_command_workspace
from .process_output_commands import (
    format_process_output_contexts_report_text,
    format_process_output_diagnostics_report_text,
    get_process_output_contexts_report,
    get_process_output_contexts_text,
    get_process_output_diagnostics_report,
    get_process_output_diagnostics_text,
)
from .process_request_parsing import parse_process_request
from .process_stop_commands import (
    format_check_stop_all_processes_report_text,
    format_check_stop_process_report_text,
    format_stop_all_processes_report_text,
    format_stop_process_report_text,
    get_check_stop_all_processes_report,
    get_check_stop_all_processes_text,
    get_check_stop_process_report,
    get_check_stop_process_text,
    get_stop_all_processes_report,
    get_stop_all_processes_text,
    get_stop_process_report,
    get_stop_process_text,
    serialize_stopped_process_info,
)
from .process_wait_write_commands import (
    decode_stdin_escapes,
    format_check_write_process_report_text,
    format_wait_process_report_text,
    format_write_process_report_text,
    get_check_write_process_report,
    get_check_write_process_text,
    get_wait_process_report,
    get_wait_process_text,
    get_write_process_report,
    get_write_process_text,
    parse_wait_process_request,
    parse_write_process_request,
    serialize_write_process_report,
)
from .process_report_helpers import (
    empty_command_output_analysis,
    format_env_report_text,
    format_process_report_text,
    format_processes_report_text,
    format_structured_command_output_analysis_lines,
    process_status_text,
    serialize_command_output_analysis,
    serialize_process_info,
)
from .types import EnvironmentInfoAction, ListProcessesAction, ReadProcessAction

PROCESS_USAGE = "Usage: /process <id> [chars]"


def _usage_error(usage: str, error: object) -> str:
    return f"{usage}\nError: {error}"


def _process_failure_report(
    root: Path,
    process_id: str,
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
        "exitCode": None,
        "signal": None,
        "maxOutputChars": max_output_chars,
        "stdout": "",
        "stderr": "",
        "analysis": empty_command_output_analysis(),
        "message": message,
    }


def get_env_text(project_root: str | Path = ".") -> str:
    return format_env_report_text(get_env_report(project_root))


def get_env_report(project_root: str | Path = ".") -> dict[str, object]:
    root = Path(project_root).resolve()
    workspace = local_command_workspace(root, "local-env")
    observation = execute_action(
        workspace,
        EnvironmentInfoAction(type="environment_info"),
    )
    if observation.kind != "environment_info":
        return {
            "projectRoot": str(root),
            "ok": False,
            "platform": "",
            "pythonVersion": "",
            "pythonExecutable": "",
            "gitRepo": False,
            "tools": {"available": 0, "total": 0, "items": []},
            "message": f"Unexpected observation: {observation.kind}",
        }

    items = [
        {
            "name": tool.name,
            "available": tool.available,
            "path": tool.path or "",
            "version": tool.version or "",
            "message": tool.message,
        }
        for tool in observation.tools
    ]
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "platform": observation.platform,
        "pythonVersion": observation.python_version,
        "pythonExecutable": observation.python_executable,
        "gitRepo": observation.is_git_repo,
        "tools": {
            "available": sum(1 for tool in items if bool(tool.get("available"))),
            "total": len(items),
            "items": items,
        },
        "message": observation.message,
    }


def get_processes_text(project_root: str | Path = ".") -> str:
    return format_processes_report_text(get_processes_report(project_root))


def get_processes_report(project_root: str | Path = ".") -> dict[str, object]:
    root = Path(project_root).resolve()
    workspace = local_command_workspace(root, "local-processes")
    observation = execute_action(
        workspace,
        ListProcessesAction(type="list_processes"),
    )
    if observation.kind != "list_processes":
        return {
            "projectRoot": str(root),
            "processes": {"total": 0, "running": 0, "items": []},
            "message": f"Unexpected observation: {observation.kind}",
        }

    items = [serialize_process_info(process) for process in observation.processes]
    running_count = sum(1 for process in items if bool(process.get("running")))
    return {
        "projectRoot": str(root),
        "processes": {"total": len(items), "running": running_count, "items": items},
        "message": observation.message,
    }


def get_process_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    process_id: str | None = None,
    max_output_chars: int | None = None,
) -> str:
    return format_process_report_text(get_process_report(project_root, argument, process_id, max_output_chars))


def get_process_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    process_id: str | None = None,
    max_output_chars: int | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        selected_process_id, selected_max = parse_process_request(argument, process_id, max_output_chars)
    except ValueError as error:
        return _process_failure_report(root, process_id or "", max_output_chars, _usage_error(PROCESS_USAGE, error))

    workspace = local_command_workspace(root, "local-process")
    observation = execute_action(
        workspace,
        ReadProcessAction(type="read_process", process_id=selected_process_id, max_output_chars=selected_max),
    )
    if observation.kind != "read_process":
        return _process_failure_report(
            root,
            selected_process_id,
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
        "exitCode": observation.exit_code,
        "signal": observation.signal,
        "maxOutputChars": observation.max_output_chars,
        "stdout": observation.stdout,
        "stderr": observation.stderr,
        "analysis": serialize_command_output_analysis(observation),
        "message": observation.message,
    }
