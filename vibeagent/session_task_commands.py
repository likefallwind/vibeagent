from __future__ import annotations

from pathlib import Path
from typing import Any

from .local_command_workspace import local_command_workspace
from .session import get_last_session_id
from .session_input import normalize_optional_run_id
from .session_task_store import read_task_store
from .session_task_types import MAX_TASKS, SessionTask, TaskStoreError
from .session_utils import compact, session_dir


SESSION_TASK_MAX_TEXT = 2_000


def get_session_tasks_report(
    project_root: str | Path = ".",
    run_id: str | None = None,
    *,
    max_tasks: int = MAX_TASKS,
    max_text: int = SESSION_TASK_MAX_TEXT,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    selected = normalize_optional_run_id(run_id) or get_last_session_id(root)
    if not selected:
        return _error_report(root, None, "No sessions found.", "missing")
    if max_tasks < 1 or max_tasks > MAX_TASKS:
        return _error_report(root, selected, f"max_tasks must be between 1 and {MAX_TASKS}.", "invalid")
    if max_text < 80 or max_text > SESSION_TASK_MAX_TEXT:
        return _error_report(
            root,
            selected,
            f"max_text must be between 80 and {SESSION_TASK_MAX_TEXT}.",
            "invalid",
        )
    session_exists = False
    try:
        selected_dir = session_dir(root, selected)
        if not selected_dir.is_dir():
            return _error_report(root, selected, f"Session not found: {selected}", "missing")
        session_exists = True
        store = read_task_store(local_command_workspace(root, selected))
    except (OSError, UnicodeError, TaskStoreError, ValueError) as error:
        return _error_report(root, selected, str(error), "invalid", exists=session_exists)

    tasks = list(store.tasks)
    shown = tasks[:max_tasks]
    statuses = _status_counts(tasks)
    blocked = sum(1 for task in tasks if _is_blocked(task, tasks))
    return {
        "projectRoot": str(root),
        "session": selected,
        "exists": True,
        "ok": True,
        "status": "ready" if tasks else "empty",
        "counts": {**statuses, "blocked": blocked},
        "tasks": {
            "total": len(tasks),
            "shown": len(shown),
            "omitted": len(tasks) - len(shown),
            "truncated": len(tasks) > len(shown),
            "items": [_task_item(task, tasks, max_text=max_text) for task in shown],
        },
        "message": f"Found {len(tasks)} persistent session task(s).",
    }


def get_session_tasks_text(
    project_root: str | Path = ".",
    run_id: str | None = None,
) -> str:
    return format_session_tasks_report_text(get_session_tasks_report(project_root, run_id))


def format_session_tasks_report_text(report: dict[str, object]) -> str:
    if not bool(report.get("ok")):
        message = str(report.get("message") or "Session task graph is unavailable.")
        if message.startswith(("No sessions found.", "Session not found:", "Invalid session id:")):
            return message
        return "\n".join(("Session tasks:", "  ok: no", f"  error: {message}"))
    counts = _mapping(report.get("counts"))
    tasks = _mapping(report.get("tasks"))
    items = [item for item in tasks.get("items", []) if isinstance(item, dict)]
    lines = [
        "Session tasks:",
        "  ok: yes",
        f"  session: {report.get('session')}",
        f"  status: {report.get('status')}",
        f"  tasks: {tasks.get('shown', 0)}/{tasks.get('total', 0)}",
        (
            "  counts: "
            f"pending={counts.get('pending', 0)}, "
            f"inProgress={counts.get('inProgress', 0)}, "
            f"completed={counts.get('completed', 0)}, "
            f"blocked={counts.get('blocked', 0)}"
        ),
    ]
    for item in items:
        line = f"  - #{item.get('id')} [{item.get('status')}] {item.get('subject')}"
        if item.get("owner"):
            line += f" (owner: {item.get('owner')})"
        lines.append(line)
        if item.get("blockedBy"):
            lines.append(f"    blockedBy: {', '.join(str(value) for value in item['blockedBy'])}")
        if item.get("blocks"):
            lines.append(f"    blocks: {', '.join(str(value) for value in item['blocks'])}")
        lines.append(f"    description: {item.get('description')}")
    if bool(tasks.get("truncated")):
        lines.append(f"  omitted: {tasks.get('omitted', 0)}")
    return "\n".join(lines)


def _task_item(task: SessionTask, tasks: list[SessionTask], *, max_text: int) -> dict[str, object]:
    return {
        "id": task.id,
        "subject": compact(task.subject, min(500, max_text)),
        "description": compact(task.description, max_text),
        "status": task.status,
        "activeForm": compact(task.active_form, min(500, max_text)) if task.active_form else None,
        "owner": compact(task.owner, min(200, max_text)) if task.owner else None,
        "blocks": list(task.blocks),
        "blockedBy": list(task.blocked_by),
        "blocked": _is_blocked(task, tasks),
    }


def _is_blocked(task: SessionTask, tasks: list[SessionTask]) -> bool:
    by_id = {item.id: item for item in tasks}
    return any(by_id[task_id].status != "completed" for task_id in task.blocked_by)


def _status_counts(tasks: list[SessionTask]) -> dict[str, int]:
    return {
        "pending": sum(task.status == "pending" for task in tasks),
        "inProgress": sum(task.status == "in_progress" for task in tasks),
        "completed": sum(task.status == "completed" for task in tasks),
    }


def _mapping(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _error_report(
    root: Path,
    run_id: str | None,
    message: str,
    status: str,
    *,
    exists: bool = False,
) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "session": run_id,
        "exists": exists,
        "ok": False,
        "status": status,
        "counts": {"pending": 0, "inProgress": 0, "completed": 0, "blocked": 0},
        "tasks": {"total": 0, "shown": 0, "omitted": 0, "truncated": False, "items": []},
        "message": message,
    }


__all__ = [
    "format_session_tasks_report_text",
    "get_session_tasks_report",
    "get_session_tasks_text",
]
