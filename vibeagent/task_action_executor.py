from __future__ import annotations

from .action_task_types import TaskCreateAction, TaskGetAction, TaskListAction, TaskUpdateAction
from .observation_task_types import (
    TaskCreateObservation,
    TaskCreateResult,
    TaskDetails,
    TaskGetObservation,
    TaskListItem,
    TaskListObservation,
    TaskUpdateObservation,
)
from .session_tasks import (
    SessionTask,
    TaskStore,
    TaskStoreError,
    create_session_task,
    get_session_task,
    list_session_tasks,
    task_store_plan,
    update_session_task,
)
from .workspace_core import RunWorkspace


def execute_task_action(workspace: RunWorkspace, action: object) -> object | None:
    try:
        if isinstance(action, TaskCreateAction):
            task, store = create_session_task(workspace, action)
            return TaskCreateObservation(
                kind="task_create",
                ok=True,
                task=TaskCreateResult(id=task.id, subject=task.subject),
                message=f"Created task {task.id}: {task.subject}",
                plan=task_store_plan(store),
            )
        if isinstance(action, TaskGetAction):
            task, store = get_session_task(workspace, action.task_id)
            return TaskGetObservation(
                kind="task_get",
                ok=True,
                task=_task_details(task) if task is not None else None,
                message=f"Found task {task.id}." if task is not None else f"Task not found: {action.task_id}",
                plan=task_store_plan(store),
            )
        if isinstance(action, TaskListAction):
            store = list_session_tasks(workspace)
            return TaskListObservation(
                kind="task_list",
                ok=True,
                tasks=[_task_list_item(task) for task in store.tasks],
                message=f"Found {len(store.tasks)} task(s).",
                plan=task_store_plan(store),
            )
        if isinstance(action, TaskUpdateAction):
            result = update_session_task(workspace, action)
            status_change = None
            if result.status_change is not None:
                status_change = {"from": result.status_change[0], "to": result.status_change[1]}
            return TaskUpdateObservation(
                kind="task_update",
                ok=result.success,
                success=result.success,
                taskId=result.task_id,
                updatedFields=list(result.updated_fields),
                error=result.error,
                statusChange=status_change,
                message=(
                    f"Updated task {result.task_id}: {', '.join(result.updated_fields) or 'no changes'}."
                    if result.success
                    else result.error or f"Could not update task {result.task_id}."
                ),
                plan=task_store_plan(result.store),
            )
    except (OSError, TaskStoreError) as error:
        return _task_failure(action, str(error))
    return None


def _task_failure(action: object, message: str) -> object:
    if isinstance(action, TaskCreateAction):
        return TaskCreateObservation(kind="task_create", ok=False, task=None, message=message)
    if isinstance(action, TaskGetAction):
        return TaskGetObservation(kind="task_get", ok=False, task=None, message=message)
    if isinstance(action, TaskListAction):
        return TaskListObservation(kind="task_list", ok=False, tasks=[], message=message)
    assert isinstance(action, TaskUpdateAction)
    return TaskUpdateObservation(
        kind="task_update",
        ok=False,
        success=False,
        taskId=action.task_id,
        updatedFields=[],
        error=message,
        statusChange=None,
        message=message,
    )


def _task_details(task: SessionTask) -> TaskDetails:
    return TaskDetails(
        id=task.id,
        subject=task.subject,
        description=task.description,
        status=task.status,
        blocks=list(task.blocks),
        blockedBy=list(task.blocked_by),
        activeForm=task.active_form,
        owner=task.owner,
        metadata=dict(task.metadata),
    )


def _task_list_item(task: SessionTask) -> TaskListItem:
    return TaskListItem(
        id=task.id,
        subject=task.subject,
        status=task.status,
        owner=task.owner,
        blockedBy=list(task.blocked_by),
    )
