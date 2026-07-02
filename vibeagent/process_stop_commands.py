from __future__ import annotations

from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action
from .types import CheckStopAllProcessesAction, CheckStopProcessAction, StopAllProcessesAction, StopProcessAction
from .workspace_core import RunWorkspace


def _execute_action(*args: object, **kwargs: object) -> object:
    commands_module = sys.modules.get("vibeagent.process_commands")
    command_execute_action = getattr(commands_module, "execute_action", None) if commands_module is not None else None
    if command_execute_action is not None:
        return command_execute_action(*args, **kwargs)
    return _default_execute_action(*args, **kwargs)


def get_check_stop_process_text(project_root: str | Path = ".", process_id: str | None = None) -> str:
    return format_check_stop_process_report_text(get_check_stop_process_report(project_root, process_id))


def get_check_stop_process_report(project_root: str | Path = ".", process_id: str | None = None) -> dict[str, object]:
    root = Path(project_root).resolve()
    selected_process_id = process_id.strip() if process_id else None
    if not selected_process_id:
        return {
            "projectRoot": str(root),
            "ok": False,
            "processId": "",
            "pid": None,
            "command": "",
            "cwd": "",
            "running": False,
            "exitCode": None,
            "signal": None,
            "status": "unknown",
            "message": "Usage: /check-stop-process <id>\nError: process id is required.",
        }

    workspace = RunWorkspace(root=root, run_id="local-check-stop-process", session_dir=root / ".vibeagent" / "sessions" / "local-check-stop-process")
    observation = _execute_action(
        workspace,
        CheckStopProcessAction(type="check_stop_process", process_id=selected_process_id),
    )
    if observation.kind != "check_stop_process":
        return {
            "projectRoot": str(root),
            "ok": False,
            "processId": selected_process_id,
            "pid": None,
            "command": "",
            "cwd": "",
            "running": False,
            "exitCode": None,
            "signal": None,
            "status": "unknown",
            "message": f"Unexpected observation: {observation.kind}",
        }

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
        return {
            "projectRoot": str(root),
            "ok": False,
            "processId": "",
            "pid": None,
            "exitCode": None,
            "signal": None,
            "result": "unknown",
            "message": "Usage: /stop-process <id>\nError: process id is required.",
        }

    workspace = RunWorkspace(root=root, run_id="local-stop-process", session_dir=root / ".vibeagent" / "sessions" / "local-stop-process")
    observation = _execute_action(
        workspace,
        StopProcessAction(type="stop_process", process_id=selected_process_id),
    )
    if observation.kind != "stop_process":
        return {
            "projectRoot": str(root),
            "ok": False,
            "processId": selected_process_id,
            "pid": None,
            "exitCode": None,
            "signal": None,
            "result": "unknown",
            "message": f"Unexpected observation: {observation.kind}",
        }

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
    workspace = RunWorkspace(root=root, run_id="local-check-stop-all-processes", session_dir=root / ".vibeagent" / "sessions" / "local-check-stop-all-processes")
    observation = _execute_action(
        workspace,
        CheckStopAllProcessesAction(type="check_stop_all_processes"),
    )
    if observation.kind != "check_stop_all_processes":
        return {
            "projectRoot": str(root),
            "ok": False,
            "processes": {"total": 0, "running": 0, "items": []},
            "message": f"Unexpected observation: {observation.kind}",
        }

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
    workspace = RunWorkspace(root=root, run_id="local-stop-all-processes", session_dir=root / ".vibeagent" / "sessions" / "local-stop-all-processes")
    observation = _execute_action(
        workspace,
        StopAllProcessesAction(type="stop_all_processes"),
    )
    if observation.kind != "stop_all_processes":
        return {
            "projectRoot": str(root),
            "ok": False,
            "stopped": {"total": 0, "items": []},
            "message": f"Unexpected observation: {observation.kind}",
        }

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


def process_status_text(running: bool, exit_code: int | None, signal: str | None) -> str:
    if signal:
        return f"signaled({signal})"
    if running:
        return "running"
    if exit_code is not None:
        return f"exited({exit_code})"
    return "unknown"


def serialize_process_info(process: object) -> dict[str, object]:
    running = bool(getattr(process, "running", False))
    exit_code = getattr(process, "exit_code", None)
    signal = getattr(process, "signal", None)
    return {
        "processId": str(getattr(process, "process_id", "") or ""),
        "pid": getattr(process, "pid", None),
        "command": str(getattr(process, "command", "") or ""),
        "cwd": str(getattr(process, "cwd", ".") or "."),
        "running": running,
        "exitCode": exit_code,
        "signal": signal,
        "status": process_status_text(running, exit_code, signal),
    }


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
