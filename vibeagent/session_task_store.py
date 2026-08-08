from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from .session_task_graph import has_dependency_cycle
from .session_task_types import MAX_TASKS, TASK_STORE_FILE, TASK_STORE_VERSION, SessionTask, TaskStore, TaskStoreError
from .workspace_core import RunWorkspace


MAX_TASK_STORE_BYTES = 1_000_000


def task_store_path(workspace: RunWorkspace) -> Path:
    return workspace.session_dir / TASK_STORE_FILE


def read_task_store(workspace: RunWorkspace) -> TaskStore:
    path = task_store_path(workspace)
    if path.is_symlink():
        raise TaskStoreError(f"Task store must not be a symlink: {path}")
    if not path.exists():
        return TaskStore()
    if not path.is_file():
        raise TaskStoreError(f"Task store is not a regular file: {path}")
    if path.stat().st_size > MAX_TASK_STORE_BYTES:
        raise TaskStoreError(f"Session task store exceeds {MAX_TASK_STORE_BYTES} bytes.")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise TaskStoreError(f"Invalid session task store: {error.msg}") from error
    return _parse_task_store(payload)


def write_task_store(workspace: RunWorkspace, store: TaskStore) -> None:
    path = task_store_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise TaskStoreError(f"Task store must not be a symlink: {path}")
    payload = {
        "version": TASK_STORE_VERSION,
        "nextId": store.next_id,
        "tasks": [_serialize_task(task) for task in store.tasks],
    }
    encoded = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if len(encoded.encode("utf-8")) > MAX_TASK_STORE_BYTES:
        raise TaskStoreError(f"Session task store exceeds {MAX_TASK_STORE_BYTES} bytes.")
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        temporary.write_text(encoded, encoding="utf-8")
        temporary.replace(path)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def _parse_task_store(payload: object) -> TaskStore:
    if not isinstance(payload, dict) or payload.get("version") != TASK_STORE_VERSION:
        raise TaskStoreError("Unsupported or malformed session task store.")
    next_id = payload.get("nextId")
    raw_tasks = payload.get("tasks")
    if not isinstance(next_id, int) or next_id < 1 or not isinstance(raw_tasks, list) or len(raw_tasks) > MAX_TASKS:
        raise TaskStoreError("Malformed session task store metadata.")
    tasks = tuple(_parse_task(item) for item in raw_tasks)
    ids = [task.id for task in tasks]
    if len(ids) != len(set(ids)) or any(not task_id.isdigit() for task_id in ids):
        raise TaskStoreError("Session task store contains invalid or duplicate task IDs.")
    if any(int(task_id) >= next_id for task_id in ids):
        raise TaskStoreError("Session task store nextId does not follow assigned task IDs.")
    _validate_dependencies(tasks)
    return TaskStore(next_id=next_id, tasks=tasks)


def _validate_dependencies(tasks: tuple[SessionTask, ...]) -> None:
    by_id = {task.id: task for task in tasks}
    for task in tasks:
        if task.id in task.blocks or task.id in task.blocked_by:
            raise TaskStoreError("Session task store contains a self dependency.")
        if any(task_id not in by_id for task_id in (*task.blocks, *task.blocked_by)):
            raise TaskStoreError("Session task store contains an unknown dependency.")
        for blocked_id in task.blocks:
            if task.id not in by_id[blocked_id].blocked_by:
                raise TaskStoreError("Session task store contains an asymmetric dependency.")
        for blocker_id in task.blocked_by:
            if task.id not in by_id[blocker_id].blocks:
                raise TaskStoreError("Session task store contains an asymmetric dependency.")
    if has_dependency_cycle(tasks):
        raise TaskStoreError("Session task store contains a dependency cycle.")


def _parse_task(value: object) -> SessionTask:
    if not isinstance(value, dict):
        raise TaskStoreError("Session task entry must be an object.")
    task_id = value.get("id")
    subject = value.get("subject")
    description = value.get("description")
    status = value.get("status")
    active_form = value.get("activeForm")
    owner = value.get("owner")
    metadata = value.get("metadata", {})
    if not isinstance(task_id, str) or not task_id or len(task_id) > 64:
        raise TaskStoreError("Session task entry has an invalid ID.")
    if not isinstance(subject, str) or not subject or len(subject) > 500:
        raise TaskStoreError("Session task entry has an invalid subject.")
    if not isinstance(description, str) or not description or len(description) > 10_000:
        raise TaskStoreError("Session task entry has an invalid description.")
    if status not in {"pending", "in_progress", "completed"}:
        raise TaskStoreError("Session task entry has an invalid status.")
    if active_form is not None and (not isinstance(active_form, str) or not active_form or len(active_form) > 500):
        raise TaskStoreError("Session task entry has an invalid activeForm.")
    if owner is not None and (not isinstance(owner, str) or not owner or len(owner) > 200):
        raise TaskStoreError("Session task entry has an invalid owner.")
    if not isinstance(metadata, dict):
        raise TaskStoreError("Session task entry metadata must be an object.")
    return SessionTask(
        id=task_id,
        subject=subject,
        description=description,
        status=status,
        active_form=active_form,
        owner=owner,
        metadata=dict(metadata),
        blocks=_stored_ids(value.get("blocks", []), "blocks"),
        blocked_by=_stored_ids(value.get("blockedBy", []), "blockedBy"),
    )


def _stored_ids(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise TaskStoreError(f"Session task entry {label} must be a list of task IDs.")
    ids = tuple(value)
    if len(ids) != len(set(ids)):
        raise TaskStoreError(f"Session task entry {label} contains duplicates.")
    return ids


def _serialize_task(task: SessionTask) -> dict[str, object]:
    return {
        "id": task.id,
        "subject": task.subject,
        "description": task.description,
        "status": task.status,
        "activeForm": task.active_form,
        "owner": task.owner,
        "metadata": task.metadata,
        "blocks": list(task.blocks),
        "blockedBy": list(task.blocked_by),
    }
