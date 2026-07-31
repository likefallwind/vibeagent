from __future__ import annotations

from typing import Any

from .session_types import SessionPlanItem, SessionProcessInfo
from .session_utils import as_int


def parse_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def session_check_failure_labels(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    failures: list[str] = []
    for item in value:
        if not isinstance(item, dict) or item.get("ok") is not False:
            continue
        path = item.get("path")
        message = item.get("message")
        if not isinstance(path, str) or not path.strip():
            path = "unknown"
        if not isinstance(message, str) or not message.strip():
            message = "failed"
        location = session_check_location(item.get("line"), item.get("column"))
        failures.append(f"{path}{location}: {message}")
    return failures


def session_changed_file_labels(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    labels: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        if not isinstance(path, str) or not path.strip():
            continue
        status = item.get("status")
        status_label = status.strip() if isinstance(status, str) and status.strip() else "?"
        labels.append(f"{status_label} {path.strip()}")
    return labels


def session_check_location(line: Any, column: Any) -> str:
    line_number = as_int(line)
    column_number = as_int(column)
    if line_number is None:
        return ""
    if column_number is None:
        return f" at line {line_number}"
    return f" at line {line_number}, column {column_number}"


def parse_session_plan(value: Any) -> list[SessionPlanItem]:
    if not isinstance(value, list):
        return []
    items: list[SessionPlanItem] = []
    for item in value[:20]:
        if not isinstance(item, dict):
            continue
        step = item.get("step")
        status = item.get("status")
        if not isinstance(step, str) or not step.strip():
            continue
        if status not in {"pending", "in_progress", "completed"}:
            continue
        active_form = item.get("active_form")
        if active_form is None:
            active_form = item.get("activeForm")
        items.append(
            SessionPlanItem(
                step=step.strip(),
                status=status,
                active_form=active_form.strip() if isinstance(active_form, str) and active_form.strip() else None,
            )
        )
    return items


def checkpoint_result_id(result: dict[str, Any]) -> str | None:
    checkpoint = result.get("checkpoint")
    if not isinstance(checkpoint, dict):
        return None
    checkpoint_id = checkpoint.get("checkpoint_id")
    if isinstance(checkpoint_id, str) and checkpoint_id.strip():
        return checkpoint_id.strip()
    return None


def update_session_background_processes(
    active_processes: dict[str, SessionProcessInfo],
    result: dict[str, Any],
    line_number: int,
) -> None:
    kind = result.get("kind")
    if kind == "start_command":
        if result.get("ok") is not True:
            return
        process_id = result.get("process_id")
        if not isinstance(process_id, str) or not process_id.strip():
            return
        active_processes[process_id] = session_process_info(result, line_number=line_number)
        return

    if kind in {"read_process", "wait_process"}:
        process_id = result.get("process_id")
        if not isinstance(process_id, str) or process_id not in active_processes:
            return
        if result.get("running") is False:
            active_processes.pop(process_id, None)
            return
        if result.get("running") is True:
            active_processes[process_id] = merge_session_process_info(
                active_processes[process_id],
                result,
                line_number=line_number,
            )
        return

    if kind == "stop_process":
        process_id = result.get("process_id")
        if result.get("ok") is True and isinstance(process_id, str):
            active_processes.pop(process_id, None)
        return

    if kind == "stop_all_processes":
        if result.get("ok") is not True:
            return
        stopped = result.get("stopped")
        if isinstance(stopped, list):
            for item in stopped:
                if isinstance(item, dict) and isinstance(item.get("process_id"), str):
                    active_processes.pop(item["process_id"], None)
            return
        active_processes.clear()
        return

    if kind == "final_review":
        running_processes = result.get("running_processes")
        if not isinstance(running_processes, list):
            return
        active_processes.clear()
        for process in running_processes:
            if isinstance(process, dict) and isinstance(process.get("process_id"), str):
                active_processes[process["process_id"]] = session_process_info(process, line_number=line_number)


def session_process_info(result: dict[str, Any], line_number: int) -> SessionProcessInfo:
    process_id = result.get("process_id")
    command = result.get("command")
    cwd = result.get("cwd")
    return SessionProcessInfo(
        process_id=process_id if isinstance(process_id, str) and process_id.strip() else "unknown",
        pid=as_int(result.get("pid")),
        command=command.strip() if isinstance(command, str) and command.strip() else "unknown",
        cwd=cwd.strip() if isinstance(cwd, str) and cwd.strip() else ".",
        line_number=line_number,
    )


def merge_session_process_info(
    previous: SessionProcessInfo,
    result: dict[str, Any],
    line_number: int,
) -> SessionProcessInfo:
    current = session_process_info(result, line_number=line_number)
    return SessionProcessInfo(
        process_id=previous.process_id,
        pid=current.pid if current.pid is not None else previous.pid,
        command=current.command if current.command != "unknown" else previous.command,
        cwd=current.cwd if current.cwd != "." else previous.cwd,
        line_number=line_number,
    )
