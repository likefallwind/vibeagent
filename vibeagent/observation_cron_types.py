from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class ScheduledTaskDetails:
    id: str
    cron: str
    prompt: str
    recurring: bool
    createdAt: str
    scheduledFor: str
    nextRunAt: str
    expiresAt: str | None


@dataclass(frozen=True)
class CronCreateObservation:
    kind: Literal["cron_create"]
    ok: bool
    task: ScheduledTaskDetails | None
    message: str


@dataclass(frozen=True)
class CronListObservation:
    kind: Literal["cron_list"]
    ok: bool
    tasks: list[ScheduledTaskDetails] = field(default_factory=list)
    message: str = ""


@dataclass(frozen=True)
class CronDeleteObservation:
    kind: Literal["cron_delete"]
    ok: bool
    taskId: str
    deleted: bool
    message: str
