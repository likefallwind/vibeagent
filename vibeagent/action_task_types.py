from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


TaskStatus = Literal["pending", "in_progress", "completed"]
TaskUpdateStatus = Literal["pending", "in_progress", "completed", "deleted"]


@dataclass(frozen=True)
class TaskCreateAction:
    type: Literal["task_create"]
    subject: str
    description: str
    active_form: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TaskGetAction:
    type: Literal["task_get"]
    task_id: str


@dataclass(frozen=True)
class TaskListAction:
    type: Literal["task_list"]


@dataclass(frozen=True)
class TaskUpdateAction:
    type: Literal["task_update"]
    task_id: str
    status: TaskUpdateStatus | None = None
    subject: str | None = None
    description: str | None = None
    active_form: str | None = None
    active_form_set: bool = False
    add_blocks: tuple[str, ...] = ()
    add_blocked_by: tuple[str, ...] = ()
    owner: str | None = None
    owner_set: bool = False
    metadata: dict[str, Any] | None = None
