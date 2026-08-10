from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from threading import Event, Thread
from typing import Literal

from .types import DelegateTaskAction, DelegateTaskObservation


BackgroundDelegateRunner = Callable[
    [str, Callable[[], bool], Callable[[bool], list[str]]],
    DelegateTaskObservation,
]


@dataclass
class BackgroundDelegateTask:
    task_id: str
    action: DelegateTaskAction
    cancel_event: Event = field(default_factory=Event)
    done_event: Event = field(default_factory=Event)
    result: DelegateTaskObservation | None = None
    error: str | None = None
    thread: Thread | None = None
    discard_when_done: bool = False
    pending_messages: list[str] = field(default_factory=list)
    accepting_messages: bool = True
    notification_delivered: bool = False
    depth: int = 1
    parent_id: str | None = None


@dataclass(frozen=True)
class BackgroundDelegateSnapshot:
    task_id: str
    action: DelegateTaskAction
    status: Literal["running", "completed", "failed", "cancelled"]
    depth: int = 1
    parent_id: str | None = None


@dataclass(frozen=True)
class BackgroundDelegateCloseResult:
    task_ids: tuple[str, ...]
    cancel_requested_task_ids: tuple[str, ...]
    discarded_task_ids: tuple[str, ...]
    still_running_task_ids: tuple[str, ...]


__all__ = [
    "BackgroundDelegateCloseResult",
    "BackgroundDelegateRunner",
    "BackgroundDelegateSnapshot",
    "BackgroundDelegateTask",
]
