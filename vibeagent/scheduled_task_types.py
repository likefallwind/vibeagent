from __future__ import annotations

from dataclasses import dataclass


SCHEDULE_STORE_FILE = "scheduled_tasks.json"
SCHEDULE_STORE_VERSION = 1
MAX_SCHEDULED_TASKS = 50
RECURRING_EXPIRY_SECONDS = 7 * 24 * 60 * 60


class ScheduledTaskError(ValueError):
    pass


@dataclass(frozen=True)
class ScheduledTask:
    id: str
    cron: str
    prompt: str
    recurring: bool
    created_at: float
    scheduled_for: float
    next_run_at: float
    expires_at: float | None = None


@dataclass(frozen=True)
class ScheduledTaskStore:
    tasks: tuple[ScheduledTask, ...] = ()
