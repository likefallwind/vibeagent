from __future__ import annotations

from dataclasses import replace
from threading import RLock

from .action_task_types import TaskCreateAction, TaskUpdateAction
from .action_types import PlanItem
from .redaction import redact_jsonable_payload
from .session_task_graph import add_dependencies, has_dependency_cycle, remove_dependency
from .session_id import is_valid_session_id
from .session_task_store import read_task_store, task_store_path, write_task_store
from .session_task_types import MAX_TASKS, SessionTask, TaskStore, TaskStoreError, TaskUpdateResult
from .workspace_core import RunWorkspace


_TASK_STORE_LOCK = RLock()


def create_session_task(workspace: RunWorkspace, action: TaskCreateAction) -> tuple[SessionTask, TaskStore]:
    with _TASK_STORE_LOCK:
        store = read_task_store(workspace)
        if len(store.tasks) >= MAX_TASKS:
            raise TaskStoreError(f"Task list already contains the maximum of {MAX_TASKS} tasks.")
        task = SessionTask(
            id=str(store.next_id),
            subject=action.subject,
            description=action.description,
            active_form=action.active_form,
            metadata=_safe_metadata(action.metadata),
        )
        updated = TaskStore(next_id=store.next_id + 1, tasks=(*store.tasks, task))
        write_task_store(workspace, updated)
        return task, updated


def get_session_task(workspace: RunWorkspace, task_id: str) -> tuple[SessionTask | None, TaskStore]:
    with _TASK_STORE_LOCK:
        store = read_task_store(workspace)
        return next((task for task in store.tasks if task.id == task_id), None), store


def list_session_tasks(workspace: RunWorkspace) -> TaskStore:
    with _TASK_STORE_LOCK:
        return read_task_store(workspace)


def update_session_task(workspace: RunWorkspace, action: TaskUpdateAction) -> TaskUpdateResult:
    with _TASK_STORE_LOCK:
        store = read_task_store(workspace)
        index = next((index for index, task in enumerate(store.tasks) if task.id == action.task_id), None)
        if index is None:
            return _update_failure(action.task_id, store, f"Task not found: {action.task_id}")
        tasks = list(store.tasks)
        current = tasks[index]
        if action.status == "deleted":
            updated_store = TaskStore(
                next_id=store.next_id,
                tasks=tuple(remove_dependency(task, current.id) for task in tasks if task.id != current.id),
            )
            write_task_store(workspace, updated_store)
            return TaskUpdateResult(
                success=True,
                task_id=current.id,
                updated_fields=("status",),
                status_change=(current.status, "deleted"),
                store=updated_store,
            )

        updated_fields, tasks[index] = _apply_fields(current, action)
        dependency_error = add_dependencies(tasks, index, action.add_blocks, action.add_blocked_by)
        if dependency_error is not None:
            return _update_failure(current.id, store, dependency_error)
        if action.add_blocks:
            updated_fields.append("addBlocks")
        if action.add_blocked_by:
            updated_fields.append("addBlockedBy")

        status_change: tuple[str, str] | None = None
        updated = tasks[index]
        if action.status is not None and action.status != updated.status:
            unresolved = _unfinished_blockers(tasks, updated)
            if action.status in {"in_progress", "completed"} and unresolved:
                return _update_failure(
                    current.id,
                    store,
                    f"Task is blocked by unfinished task(s): {', '.join(unresolved)}",
                )
            status_change = (updated.status, action.status)
            tasks[index] = replace(updated, status=action.status)
            updated_fields.append("status")

        updated_store = TaskStore(next_id=store.next_id, tasks=tuple(tasks))
        if has_dependency_cycle(updated_store.tasks):
            return _update_failure(current.id, store, "Task dependency update would create a cycle.")
        if updated_store != store:
            write_task_store(workspace, updated_store)
        return TaskUpdateResult(
            success=True,
            task_id=current.id,
            updated_fields=tuple(dict.fromkeys(updated_fields)),
            status_change=status_change,
            store=updated_store,
        )


def task_store_plan(store: TaskStore) -> list[PlanItem]:
    return [PlanItem(step=task.subject, status=task.status, active_form=task.active_form) for task in store.tasks]


def read_task_plan(workspace: RunWorkspace) -> list[PlanItem]:
    try:
        return task_store_plan(list_session_tasks(workspace))
    except (OSError, TaskStoreError):
        return []


def inherit_task_store(workspace: RunWorkspace, source_run_id: str | None) -> tuple[bool, str | None]:
    if source_run_id is None:
        return False, None
    if not is_valid_session_id(source_run_id):
        return False, f"Invalid source session id for task restore: {source_run_id}"
    target_path = task_store_path(workspace)
    if target_path.exists() or target_path.is_symlink():
        return False, None
    source_workspace = replace(
        workspace,
        run_id=source_run_id,
        session_dir=workspace.root / ".vibeagent" / "sessions" / source_run_id,
    )
    if not task_store_path(source_workspace).exists():
        return False, None
    try:
        write_task_store(workspace, read_task_store(source_workspace))
    except (OSError, TaskStoreError) as error:
        return False, str(error)
    return True, None


def _apply_fields(current: SessionTask, action: TaskUpdateAction) -> tuple[list[str], SessionTask]:
    fields: list[str] = []
    updated = current
    for name, value, enabled, output_name in (
        ("subject", action.subject, action.subject is not None, "subject"),
        ("description", action.description, action.description is not None, "description"),
        ("active_form", action.active_form, action.active_form_set, "activeForm"),
        ("owner", action.owner, action.owner_set, "owner"),
        ("metadata", action.metadata, action.metadata is not None, "metadata"),
    ):
        if enabled and value != getattr(updated, name):
            updated = replace(updated, **{name: _safe_metadata(value) if name == "metadata" else value})
            fields.append(output_name)
    return fields, updated


def _unfinished_blockers(tasks: list[SessionTask], task: SessionTask) -> list[str]:
    by_id = {item.id: item for item in tasks}
    return [task_id for task_id in task.blocked_by if by_id[task_id].status != "completed"]


def _update_failure(task_id: str, store: TaskStore, error: str) -> TaskUpdateResult:
    return TaskUpdateResult(success=False, task_id=task_id, error=error, store=store)


def _safe_metadata(value: object) -> dict[str, object]:
    redacted = redact_jsonable_payload(value)
    return dict(redacted) if isinstance(redacted, dict) else {}


__all__ = [
    "SessionTask",
    "TaskStore",
    "TaskStoreError",
    "create_session_task",
    "get_session_task",
    "inherit_task_store",
    "list_session_tasks",
    "read_task_plan",
    "read_task_store",
    "task_store_plan",
    "update_session_task",
]
