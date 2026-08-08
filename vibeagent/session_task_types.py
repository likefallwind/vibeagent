from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .action_task_types import TaskStatus


TASK_STORE_VERSION = 1
TASK_STORE_FILE = "tasks.json"
MAX_TASKS = 100


class TaskStoreError(ValueError):
    pass


@dataclass(frozen=True)
class SessionTask:
    id: str
    subject: str
    description: str
    status: TaskStatus = "pending"
    active_form: str | None = None
    owner: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    blocks: tuple[str, ...] = ()
    blocked_by: tuple[str, ...] = ()


@dataclass(frozen=True)
class TaskStore:
    next_id: int = 1
    tasks: tuple[SessionTask, ...] = ()


@dataclass(frozen=True)
class TaskUpdateResult:
    success: bool
    task_id: str
    updated_fields: tuple[str, ...] = ()
    error: str | None = None
    status_change: tuple[str, str] | None = None
    store: TaskStore = TaskStore()
