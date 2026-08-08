from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from .action_types import PlanItem
from .action_task_types import TaskStatus


@dataclass(frozen=True)
class TaskCreateResult:
    id: str
    subject: str


@dataclass(frozen=True)
class TaskDetails:
    id: str
    subject: str
    description: str
    status: TaskStatus
    blocks: list[str]
    blockedBy: list[str]
    activeForm: str | None = None
    owner: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TaskListItem:
    id: str
    subject: str
    status: TaskStatus
    owner: str | None
    blockedBy: list[str]


@dataclass(frozen=True)
class TaskCreateObservation:
    kind: Literal["task_create"]
    ok: bool
    task: TaskCreateResult | None
    message: str
    plan: list[PlanItem] = field(default_factory=list)


@dataclass(frozen=True)
class TaskGetObservation:
    kind: Literal["task_get"]
    ok: bool
    task: TaskDetails | None
    message: str
    plan: list[PlanItem] = field(default_factory=list)


@dataclass(frozen=True)
class TaskListObservation:
    kind: Literal["task_list"]
    ok: bool
    tasks: list[TaskListItem]
    message: str
    plan: list[PlanItem] = field(default_factory=list)


@dataclass(frozen=True)
class TaskUpdateObservation:
    kind: Literal["task_update"]
    ok: bool
    success: bool
    taskId: str
    updatedFields: list[str]
    error: str | None
    statusChange: dict[str, str] | None
    message: str
    plan: list[PlanItem] = field(default_factory=list)
