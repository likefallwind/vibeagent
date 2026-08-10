from __future__ import annotations

from dataclasses import replace
import os
from threading import RLock
import time
from uuid import uuid4

from .action_cron_types import CronCreateAction
from .cron_expression import (
    next_scheduled_time,
    one_shot_fire_time,
    parse_cron_expression,
    recurring_fire_time,
)
from .scheduled_task_types import (
    MAX_SCHEDULED_TASKS,
    RECURRING_EXPIRY_SECONDS,
    ScheduledTask,
    ScheduledTaskError,
    ScheduledTaskStore,
)
from .scheduled_task_persistence import read_schedule_store, schedule_store_path, write_schedule_store
from .session_id import is_valid_session_id
from .workspace_core import RunWorkspace, create_local_workspace


CRON_TOOL_NAMES = frozenset({"CronCreate", "CronList", "CronDelete"})
_STORE_LOCK = RLock()
_ENABLED_VALUES = frozenset({"1", "true", "yes", "on"})


def scheduled_tasks_enabled() -> bool:
    for name in ("VIBEAGENT_DISABLE_CRON", "CLAUDE_CODE_DISABLE_CRON"):
        if os.environ.get(name, "").strip().lower() in _ENABLED_VALUES:
            return False
    return True


def create_scheduled_task(
    workspace: RunWorkspace,
    action: CronCreateAction,
    *,
    now: float | None = None,
) -> tuple[ScheduledTask, ScheduledTaskStore]:
    _require_enabled()
    current = time.time() if now is None else now
    expression = parse_cron_expression(action.cron)
    with _STORE_LOCK:
        store = read_schedule_store(workspace)
        if len(store.tasks) >= MAX_SCHEDULED_TASKS:
            raise ScheduledTaskError(
                f"Scheduled task list already contains the maximum of {MAX_SCHEDULED_TASKS} tasks."
            )
        task_id = _new_task_id(store)
        scheduled_for = next_scheduled_time(expression, current)
        if action.recurring:
            next_run_at = recurring_fire_time(task_id, expression, scheduled_for)
            expires_at = current + RECURRING_EXPIRY_SECONDS
        else:
            next_run_at = max(current, one_shot_fire_time(task_id, expression, scheduled_for))
            expires_at = None
        task = ScheduledTask(
            id=task_id,
            cron=expression.source,
            prompt=action.prompt,
            recurring=action.recurring,
            created_at=current,
            scheduled_for=scheduled_for,
            next_run_at=next_run_at,
            expires_at=expires_at,
        )
        updated = ScheduledTaskStore((*store.tasks, task))
        write_schedule_store(workspace, updated)
        return task, updated


def list_scheduled_tasks(workspace: RunWorkspace) -> ScheduledTaskStore:
    _require_enabled()
    with _STORE_LOCK:
        return read_schedule_store(workspace)


def delete_scheduled_task(workspace: RunWorkspace, task_id: str) -> tuple[bool, ScheduledTaskStore]:
    _require_enabled()
    with _STORE_LOCK:
        store = read_schedule_store(workspace)
        updated = ScheduledTaskStore(tuple(task for task in store.tasks if task.id != task_id))
        if updated != store:
            write_schedule_store(workspace, updated)
            return True, updated
        return False, store


def collect_due_scheduled_tasks(
    workspace: RunWorkspace,
    *,
    now: float | None = None,
) -> list[ScheduledTask]:
    if not scheduled_tasks_enabled():
        return []
    current = time.time() if now is None else now
    with _STORE_LOCK:
        store = read_schedule_store(workspace)
        due: list[ScheduledTask] = []
        retained: list[ScheduledTask] = []
        changed = False
        for task in store.tasks:
            expired = task.recurring and task.expires_at is not None and current >= task.expires_at
            if task.next_run_at > current and not expired:
                retained.append(task)
                continue
            due.append(task)
            changed = True
            if not task.recurring or expired:
                continue
            expression = parse_cron_expression(task.cron)
            scheduled_for = next_scheduled_time(expression, max(current, task.scheduled_for))
            retained.append(
                replace(
                    task,
                    scheduled_for=scheduled_for,
                    next_run_at=recurring_fire_time(task.id, expression, scheduled_for),
                )
            )
        if changed:
            write_schedule_store(workspace, ScheduledTaskStore(tuple(retained)))
        return due


def inherit_schedule_store(
    workspace: RunWorkspace,
    source_run_id: str | None,
    *,
    now: float | None = None,
) -> tuple[int, str | None]:
    if source_run_id is None:
        return 0, None
    if not is_valid_session_id(source_run_id):
        return 0, f"Invalid source session id for scheduled task restore: {source_run_id}"
    target = schedule_store_path(workspace)
    if target.exists() or target.is_symlink():
        return 0, None
    source = create_local_workspace(workspace.root, source_run_id)
    source_path = schedule_store_path(source)
    if not source_path.exists() and not source_path.is_symlink():
        return 0, None
    current = time.time() if now is None else now
    try:
        source_store = read_schedule_store(source)
        restored = tuple(
            task
            for task in source_store.tasks
            if (
                task.recurring
                and task.expires_at is not None
                and task.expires_at > current
            )
            or (
                not task.recurring
                and task.scheduled_for > current
            )
        )
        write_schedule_store(workspace, ScheduledTaskStore(restored))
    except (OSError, ScheduledTaskError, ValueError) as error:
        return 0, str(error)
    return len(restored), None


def _require_enabled() -> None:
    if not scheduled_tasks_enabled():
        raise ScheduledTaskError("Scheduled tasks are disabled by environment configuration.")


def _new_task_id(store: ScheduledTaskStore) -> str:
    used = {task.id for task in store.tasks}
    for _ in range(100):
        candidate = uuid4().hex[:8]
        if candidate not in used:
            return candidate
    raise ScheduledTaskError("Could not allocate a unique scheduled task ID.")


__all__ = [
    "CRON_TOOL_NAMES",
    "collect_due_scheduled_tasks",
    "create_scheduled_task",
    "delete_scheduled_task",
    "inherit_schedule_store",
    "list_scheduled_tasks",
    "read_schedule_store",
    "schedule_store_path",
    "scheduled_tasks_enabled",
    "write_schedule_store",
]
