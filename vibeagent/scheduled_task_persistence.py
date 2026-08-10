from __future__ import annotations

import json
import math
from pathlib import Path
from uuid import uuid4

from .cron_expression import parse_cron_expression
from .scheduled_task_types import (
    MAX_SCHEDULED_TASKS,
    SCHEDULE_STORE_FILE,
    SCHEDULE_STORE_VERSION,
    ScheduledTask,
    ScheduledTaskError,
    ScheduledTaskStore,
)
from .workspace_core import RunWorkspace


MAX_SCHEDULE_STORE_BYTES = 2_000_000


def schedule_store_path(workspace: RunWorkspace) -> Path:
    return workspace.session_dir / SCHEDULE_STORE_FILE


def read_schedule_store(workspace: RunWorkspace) -> ScheduledTaskStore:
    path = schedule_store_path(workspace)
    _validate_store_path(workspace, path)
    if not path.exists():
        return ScheduledTaskStore()
    if not path.is_file():
        raise ScheduledTaskError(f"Scheduled task store is not a regular file: {path}")
    if path.stat().st_size > MAX_SCHEDULE_STORE_BYTES:
        raise ScheduledTaskError(f"Scheduled task store exceeds {MAX_SCHEDULE_STORE_BYTES} bytes.")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ScheduledTaskError(f"Invalid scheduled task store: {error.msg}") from error
    return _parse_store(payload)


def write_schedule_store(workspace: RunWorkspace, store: ScheduledTaskStore) -> None:
    path = schedule_store_path(workspace)
    _validate_store_path(workspace, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _validate_store_path(workspace, path)
    payload = {
        "version": SCHEDULE_STORE_VERSION,
        "tasks": [_serialize_task(task) for task in store.tasks],
    }
    encoded = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if len(encoded.encode("utf-8")) > MAX_SCHEDULE_STORE_BYTES:
        raise ScheduledTaskError(f"Scheduled task store exceeds {MAX_SCHEDULE_STORE_BYTES} bytes.")
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        temporary.write_text(encoded, encoding="utf-8")
        temporary.replace(path)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def _validate_store_path(workspace: RunWorkspace, path: Path) -> None:
    runtime = workspace.root / ".vibeagent"
    sessions = runtime / "sessions"
    for candidate in (runtime, sessions, workspace.session_dir, path):
        if candidate.is_symlink():
            raise ScheduledTaskError(f"Scheduled task path must not be a symlink: {candidate}")


def _parse_store(payload: object) -> ScheduledTaskStore:
    if not isinstance(payload, dict) or payload.get("version") != SCHEDULE_STORE_VERSION:
        raise ScheduledTaskError("Unsupported or malformed scheduled task store.")
    raw_tasks = payload.get("tasks")
    if not isinstance(raw_tasks, list) or len(raw_tasks) > MAX_SCHEDULED_TASKS:
        raise ScheduledTaskError("Malformed scheduled task store metadata.")
    tasks = tuple(_parse_task(value) for value in raw_tasks)
    ids = [task.id for task in tasks]
    if len(ids) != len(set(ids)):
        raise ScheduledTaskError("Scheduled task store contains duplicate IDs.")
    return ScheduledTaskStore(tasks)


def _parse_task(value: object) -> ScheduledTask:
    if not isinstance(value, dict):
        raise ScheduledTaskError("Scheduled task entry must be an object.")
    task_id = value.get("id")
    cron = value.get("cron")
    prompt = value.get("prompt")
    recurring = value.get("recurring")
    created_at = value.get("createdAt")
    scheduled_for = value.get("scheduledFor")
    next_run_at = value.get("nextRunAt")
    expires_at = value.get("expiresAt")
    if (
        not isinstance(task_id, str)
        or len(task_id) != 8
        or any(character not in "0123456789abcdef" for character in task_id)
    ):
        raise ScheduledTaskError("Scheduled task entry has an invalid ID.")
    if not isinstance(cron, str):
        raise ScheduledTaskError("Scheduled task entry has an invalid cron expression.")
    try:
        cron = parse_cron_expression(cron).source
    except ValueError as error:
        raise ScheduledTaskError(f"Scheduled task entry has an invalid cron expression: {error}") from error
    if not isinstance(prompt, str) or not prompt or len(prompt) > 25_000:
        raise ScheduledTaskError("Scheduled task entry has an invalid prompt.")
    if not isinstance(recurring, bool):
        raise ScheduledTaskError("Scheduled task entry has an invalid recurring flag.")
    times = (created_at, scheduled_for, next_run_at)
    if any(not _valid_timestamp(item) for item in times):
        raise ScheduledTaskError("Scheduled task entry has invalid timestamps.")
    if expires_at is not None and not _valid_timestamp(expires_at):
        raise ScheduledTaskError("Scheduled task entry has an invalid expiry timestamp.")
    if recurring != (expires_at is not None):
        raise ScheduledTaskError("Scheduled task entry has inconsistent expiry metadata.")
    return ScheduledTask(
        id=task_id,
        cron=cron,
        prompt=prompt,
        recurring=recurring,
        created_at=float(created_at),
        scheduled_for=float(scheduled_for),
        next_run_at=float(next_run_at),
        expires_at=float(expires_at) if expires_at is not None else None,
    )


def _valid_timestamp(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value >= 0
    )


def _serialize_task(task: ScheduledTask) -> dict[str, object]:
    return {
        "id": task.id,
        "cron": task.cron,
        "prompt": task.prompt,
        "recurring": task.recurring,
        "createdAt": task.created_at,
        "scheduledFor": task.scheduled_for,
        "nextRunAt": task.next_run_at,
        "expiresAt": task.expires_at,
    }


__all__ = ["read_schedule_store", "schedule_store_path", "write_schedule_store"]
