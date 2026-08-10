from __future__ import annotations

from datetime import datetime

from .action_cron_types import CronCreateAction, CronDeleteAction, CronListAction
from .observation_cron_types import (
    CronCreateObservation,
    CronDeleteObservation,
    CronListObservation,
    ScheduledTaskDetails,
)
from .scheduled_task_store import (
    create_scheduled_task,
    delete_scheduled_task,
    list_scheduled_tasks,
)
from .scheduled_task_types import ScheduledTask, ScheduledTaskError
from .workspace_core import RunWorkspace


def execute_cron_action(workspace: RunWorkspace, action: object) -> object | None:
    try:
        if isinstance(action, CronCreateAction):
            task, _ = create_scheduled_task(workspace, action)
            return CronCreateObservation(
                kind="cron_create",
                ok=True,
                task=_details(task),
                message=f"Created scheduled task {task.id}; next run at {_local_time(task.next_run_at)}.",
            )
        if isinstance(action, CronListAction):
            store = list_scheduled_tasks(workspace)
            return CronListObservation(
                kind="cron_list",
                ok=True,
                tasks=[_details(task) for task in store.tasks],
                message=f"Found {len(store.tasks)} scheduled task(s).",
            )
        if isinstance(action, CronDeleteAction):
            deleted, _ = delete_scheduled_task(workspace, action.task_id)
            return CronDeleteObservation(
                kind="cron_delete",
                ok=deleted,
                taskId=action.task_id,
                deleted=deleted,
                message=(
                    f"Deleted scheduled task {action.task_id}."
                    if deleted
                    else f"Scheduled task not found: {action.task_id}"
                ),
            )
    except (OSError, ScheduledTaskError, ValueError) as error:
        return _failure(action, str(error))
    return None


def _failure(action: object, message: str) -> object:
    if isinstance(action, CronCreateAction):
        return CronCreateObservation(kind="cron_create", ok=False, task=None, message=message)
    if isinstance(action, CronListAction):
        return CronListObservation(kind="cron_list", ok=False, tasks=[], message=message)
    assert isinstance(action, CronDeleteAction)
    return CronDeleteObservation(
        kind="cron_delete",
        ok=False,
        taskId=action.task_id,
        deleted=False,
        message=message,
    )


def _details(task: ScheduledTask) -> ScheduledTaskDetails:
    return ScheduledTaskDetails(
        id=task.id,
        cron=task.cron,
        prompt=task.prompt,
        recurring=task.recurring,
        createdAt=_local_time(task.created_at),
        scheduledFor=_local_time(task.scheduled_for),
        nextRunAt=_local_time(task.next_run_at),
        expiresAt=_local_time(task.expires_at) if task.expires_at is not None else None,
    )


def _local_time(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp).astimezone().isoformat(timespec="seconds")


__all__ = ["execute_cron_action"]
