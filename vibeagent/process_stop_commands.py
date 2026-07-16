from __future__ import annotations

from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action
from .local_command_workspace import local_command_workspace
from .process_report_helpers import process_status_text, serialize_process_info
from .types import CheckStopAllProcessesAction, CheckStopProcessAction, StopAllProcessesAction, StopProcessAction

CHECK_STOP_PROCESS_USAGE = "Usage: /check-stop-process <id>"
STOP_PROCESS_USAGE = "Usage: /stop-process <id>"
PROCESS_ID_REQUIRED_ERROR = "process id is required."


def _execute_action(*args: object, **kwargs: object) -> object:
    commands_module = sys.modules.get("vibeagent.process_commands")
    command_execute_action = getattr(commands_module, "execute_action", None) if commands_module is not None else None
    if command_execute_action is not None:
        return command_execute_action(*args, **kwargs)
    return _default_execute_action(*args, **kwargs)


def _usage_error(usage: str, error: object) -> str:
    return f"{usage}\nError: {error}"


def _check_stop_process_failure_report(root: Path, process_id: str, message: str) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "processId": process_id,
        "pid": None,
        "command": "",
        "cwd": "",
        "running": False,
        "exitCode": None,
        "signal": None,
        "status": "unknown",
        "message": message,
    }


def _stop_process_failure_report(root: Path, process_id: str, message: str) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "processId": process_id,
        "pid": None,
        "exitCode": None,
        "signal": None,
        "result": "unknown",
        "message": message,
    }


def _processes_failure_report(root: Path, key: str, message: str) -> dict[str, object]:
    collection = {"total": 0, "items": []}
    if key == "processes":
        collection["running"] = 0
    return {"projectRoot": str(root), "ok": False, key: collection, "message": message}


def get_check_stop_process_text(project_root: str | Path = ".", process_id: str | None = None) -> str:
    return format_check_stop_process_report_text(get_check_stop_process_report(project_root, process_id))


def get_check_stop_process_report(project_root: str | Path = ".", process_id: str | None = None) -> dict[str, object]:
    root = Path(project_root).resolve()
    selected_process_id = process_id.strip() if process_id else None
    if not selected_process_id:
        return _check_stop_process_failure_report(root, "", _usage_error(CHECK_STOP_PROCESS_USAGE, PROCESS_ID_REQUIRED_ERROR))

    workspace = local_command_workspace(root, "local-check-stop-process")
    observation = _execute_action(
        workspace,
        CheckStopProcessAction(type="check_stop_process", process_id=selected_process_id),
    )
    if observation.kind != "check_stop_process":
        return _check_stop_process_failure_report(
            root,
            selected_process_id,
            f"Unexpected observation: {observation.kind}",
        )

    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "processId": observation.process_id,
        "pid": observation.pid,
        "command": observation.command or "",
        "cwd": observation.cwd or "",
        "running": observation.running,
        "exitCode": observation.exit_code,
        "signal": observation.signal,
        "status": process_status_text(observation.running, observation.exit_code, observation.signal),
        "message": observation.message,
    }


def format_check_stop_process_report_text(report: dict[str, object]) -> str:
    return "\n".join(
        [
            "Check stop process:",
            f"  projectRoot: {report.get('projectRoot') or '.'}",
            f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
            f"  processId: {report.get('processId') or ''}",
            f"  pid: {report.get('pid') if report.get('pid') is not None else '.'}",
            f"  status: {report.get('status') or 'unknown'}",
            f"  command: {report.get('command') or '.'}",
            f"  cwd: {report.get('cwd') or '.'}",
            f"  message: {report.get('message') or ''}",
        ]
    )


def get_stop_process_text(project_root: str | Path = ".", process_id: str | None = None) -> str:
    return format_stop_process_report_text(get_stop_process_report(project_root, process_id))


def get_stop_process_report(project_root: str | Path = ".", process_id: str | None = None) -> dict[str, object]:
    root = Path(project_root).resolve()
    selected_process_id = process_id.strip() if process_id else None
    if not selected_process_id:
        return _stop_process_failure_report(root, "", _usage_error(STOP_PROCESS_USAGE, PROCESS_ID_REQUIRED_ERROR))

    workspace = local_command_workspace(root, "local-stop-process")
    observation = _execute_action(
        workspace,
        StopProcessAction(type="stop_process", process_id=selected_process_id),
    )
    if observation.kind != "stop_process":
        return _stop_process_failure_report(root, selected_process_id, f"Unexpected observation: {observation.kind}")

    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "processId": observation.process_id,
        "pid": observation.pid,
        "exitCode": observation.exit_code,
        "signal": observation.signal,
        "result": process_status_text(False, observation.exit_code, observation.signal),
        "message": observation.message,
    }


def format_stop_process_report_text(report: dict[str, object]) -> str:
    return "\n".join(
        [
            "Stop process:",
            f"  projectRoot: {report.get('projectRoot') or '.'}",
            f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
            f"  processId: {report.get('processId') or ''}",
            f"  pid: {report.get('pid') if report.get('pid') is not None else '.'}",
            f"  result: {report.get('result') or 'unknown'}",
            f"  message: {report.get('message') or ''}",
        ]
    )


def get_check_stop_all_processes_text(project_root: str | Path = ".") -> str:
    return format_check_stop_all_processes_report_text(get_check_stop_all_processes_report(project_root))


def get_check_stop_all_processes_report(project_root: str | Path = ".") -> dict[str, object]:
    root = Path(project_root).resolve()
    workspace = local_command_workspace(root, "local-check-stop-all-processes")
    observation = _execute_action(
        workspace,
        CheckStopAllProcessesAction(type="check_stop_all_processes"),
    )
    if observation.kind != "check_stop_all_processes":
        return _processes_failure_report(root, "processes", f"Unexpected observation: {observation.kind}")

    items = [serialize_process_info(process) for process in observation.processes]
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "processes": {"total": len(items), "running": observation.running_count, "items": items},
        "message": observation.message,
    }


def format_check_stop_all_processes_report_text(report: dict[str, object]) -> str:
    processes = report.get("processes") if isinstance(report.get("processes"), dict) else {}
    items = [item for item in processes.get("items", []) if isinstance(item, dict)] if isinstance(processes.get("items"), list) else []
    lines = [
        "Check stop processes:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  processes: {int(processes.get('total', len(items)) or 0)}",
        f"  running: {int(processes.get('running', 0) or 0)}",
    ]
    if items:
        lines.append("  items:")
        for process in items:
            lines.append(
                f"    - {process.get('processId')}: "
                f"pid={process.get('pid') if process.get('pid') is not None else '.'}; "
                f"status={process.get('status') or 'unknown'}; "
                f"cwd={process.get('cwd') or '.'}; "
                f"command={process.get('command') or ''}"
            )
    else:
        lines.append("  items: none")
    lines.append(f"  message: {report.get('message') or ''}")
    return "\n".join(lines)


def get_stop_all_processes_text(project_root: str | Path = ".") -> str:
    return format_stop_all_processes_report_text(get_stop_all_processes_report(project_root))


def get_stop_all_processes_report(project_root: str | Path = ".") -> dict[str, object]:
    root = Path(project_root).resolve()
    workspace = local_command_workspace(root, "local-stop-all-processes")
    observation = _execute_action(
        workspace,
        StopAllProcessesAction(type="stop_all_processes"),
    )
    if observation.kind != "stop_all_processes":
        return _processes_failure_report(root, "stopped", f"Unexpected observation: {observation.kind}")

    items = [serialize_stopped_process_info(process) for process in observation.stopped]
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "stopped": {"total": len(items), "items": items},
        "message": observation.message,
    }


def format_stop_all_processes_report_text(report: dict[str, object]) -> str:
    stopped = report.get("stopped") if isinstance(report.get("stopped"), dict) else {}
    items = [item for item in stopped.get("items", []) if isinstance(item, dict)] if isinstance(stopped.get("items"), list) else []
    lines = [
        "Stop processes:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  stopped: {int(stopped.get('total', len(items)) or 0)}",
    ]
    if items:
        lines.append("  processes:")
        for process in items:
            lines.extend(
                [
                    f"    - {process.get('processId') or ''}",
                    f"      pid: {process.get('pid') if process.get('pid') is not None else '.'}",
                    f"      command: {process.get('command') or ''}",
                    f"      cwd: {process.get('cwd') or '.'}",
                    f"      ok: {'yes' if bool(process.get('ok')) else 'no'}",
                    f"      result: {process.get('result') or 'unknown'}",
                    f"      message: {process.get('message') or ''}",
                ]
            )
    else:
        lines.append("  processes: none")
    lines.append(f"  message: {report.get('message') or ''}")
    return "\n".join(lines)


def serialize_stopped_process_info(process: object) -> dict[str, object]:
    exit_code = getattr(process, "exit_code", None)
    signal = getattr(process, "signal", None)
    return {
        "processId": str(getattr(process, "process_id", "") or ""),
        "pid": getattr(process, "pid", None),
        "command": str(getattr(process, "command", "") or ""),
        "cwd": str(getattr(process, "cwd", ".") or "."),
        "ok": bool(getattr(process, "ok", False)),
        "exitCode": exit_code,
        "signal": signal,
        "result": process_status_text(False, exit_code, signal),
        "message": str(getattr(process, "message", "") or ""),
    }
