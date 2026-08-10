from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from threading import Event, RLock, Thread
from time import monotonic
from uuid import uuid4

from .types import (
    DelegateTaskAction,
    DelegateTaskObservation,
    TaskOutputAction,
    TaskOutputObservation,
    TaskStopAction,
    TaskStopObservation,
)
from .workspace_core import RunWorkspace


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


@dataclass(frozen=True)
class BackgroundDelegateCloseResult:
    task_ids: tuple[str, ...]
    cancel_requested_task_ids: tuple[str, ...]
    discarded_task_ids: tuple[str, ...]
    still_running_task_ids: tuple[str, ...]


_TASKS_LOCK = RLock()
_TASKS: dict[tuple[str, str], BackgroundDelegateTask] = {}
_MAX_RETAINED_TASKS = 128


def start_background_delegate_task(
    workspace: RunWorkspace,
    action: DelegateTaskAction,
    runner: BackgroundDelegateRunner,
    *,
    task_id: str | None = None,
    resumed: bool = False,
) -> DelegateTaskObservation:
    task_id = task_id or f"task-{uuid4().hex[:12]}"
    task = BackgroundDelegateTask(task_id=task_id, action=action)
    key = (_workspace_key(workspace), task_id)

    def drain_messages(final: bool = False) -> list[str]:
        with _TASKS_LOCK:
            messages = list(task.pending_messages)
            task.pending_messages.clear()
            if final and not messages:
                task.accepting_messages = False
            return messages

    def run() -> None:
        try:
            task.result = runner(task_id, task.cancel_event.is_set, drain_messages)
        except Exception as error:  # pragma: no cover - defensive isolation around worker failures.
            task.error = f"{type(error).__name__}: {error}"
        finally:
            task.done_event.set()
            with _TASKS_LOCK:
                if task.discard_when_done:
                    _TASKS.pop(key, None)

    task.thread = Thread(target=run, name=f"vibeagent-{task_id}", daemon=True)
    with _TASKS_LOCK:
        existing = _TASKS.get(key)
        if existing is not None and not existing.done_event.is_set():
            raise ValueError(f"Background task {task_id} is already running.")
        _prune_completed_tasks_locked()
        _TASKS[key] = task
    task.thread.start()
    return DelegateTaskObservation(
        kind="delegate_task",
        ok=True,
        task=action.task,
        summary="",
        iterations=0,
        tool_calls=[],
        message=(
            f"Subagent {task_id} resumed in the background. Use TaskOutput to read its result."
            if resumed
            else f"Background subagent started as {task_id}. Use TaskOutput to read its result."
        ),
        mode=action.mode,
        agent=action.agent,
        task_id=task_id,
        background=True,
        running=True,
    )


def send_background_delegate_message(
    workspace: RunWorkspace,
    task_id: str,
    message: str,
) -> DelegateTaskObservation | None:
    task = _find_task(workspace, task_id)
    if task is None:
        return None
    with _TASKS_LOCK:
        if task.done_event.is_set():
            return None
        if not task.accepting_messages:
            finishing = True
        else:
            finishing = False
            task.pending_messages.append(message)
    if finishing:
        task.done_event.wait(5)
        return None
    return DelegateTaskObservation(
        kind="delegate_task",
        ok=True,
        task=task.action.task,
        summary="",
        iterations=0,
        tool_calls=[],
        message=f"Message delivered to running subagent {task_id}.",
        mode=task.action.mode,
        agent=task.action.agent,
        task_id=task_id,
        background=True,
        running=True,
    )


def execute_background_task_action(
    workspace: RunWorkspace,
    action: object,
) -> TaskOutputObservation | TaskStopObservation | None:
    if isinstance(action, TaskOutputAction):
        return read_background_delegate_task(workspace, action)
    if isinstance(action, TaskStopAction):
        return stop_background_delegate_task(workspace, action)
    return None


def read_background_delegate_task(
    workspace: RunWorkspace,
    action: TaskOutputAction,
) -> TaskOutputObservation:
    task = _find_task(workspace, action.task_id)
    if task is None:
        return TaskOutputObservation(
            kind="task_output",
            ok=False,
            task_id=action.task_id,
            running=False,
            completed=False,
            result=None,
            message=f"Background task {action.task_id} was not found in this session.",
        )
    if action.block and not task.done_event.is_set():
        task.done_event.wait(action.timeout_ms / 1000)
    if not task.done_event.is_set():
        return TaskOutputObservation(
            kind="task_output",
            ok=True,
            task_id=action.task_id,
            running=True,
            completed=False,
            result=None,
            message=f"Background task {action.task_id} is still running.",
        )
    if task.result is not None:
        status = "completed" if task.result.ok else "failed"
        return TaskOutputObservation(
            kind="task_output",
            ok=True,
            task_id=action.task_id,
            running=False,
            completed=True,
            result=task.result,
            message=f"Background task {action.task_id} {status}: {task.result.message}",
        )
    return TaskOutputObservation(
        kind="task_output",
        ok=False,
        task_id=action.task_id,
        running=False,
        completed=True,
        result=None,
        message=f"Background task {action.task_id} failed unexpectedly: {task.error or 'unknown worker error'}",
    )


def stop_background_delegate_task(
    workspace: RunWorkspace,
    action: TaskStopAction,
) -> TaskStopObservation:
    task = _find_task(workspace, action.task_id)
    if task is None:
        return TaskStopObservation(
            kind="task_stop",
            ok=False,
            task_id=action.task_id,
            running=False,
            stopped=False,
            message=f"Background task {action.task_id} was not found in this session.",
        )
    task.cancel_event.set()
    task.done_event.wait(0.1)
    running = not task.done_event.is_set()
    return TaskStopObservation(
        kind="task_stop",
        ok=True,
        task_id=action.task_id,
        running=running,
        stopped=not running,
        message=(
            f"Background task {action.task_id} stopped."
            if not running
            else f"Cancellation requested for background task {action.task_id}; it is still stopping."
        ),
    )


def close_background_delegate_tasks(
    workspace: RunWorkspace,
    wait_ms: int = 100,
) -> BackgroundDelegateCloseResult:
    workspace_key = _workspace_key(workspace)
    with _TASKS_LOCK:
        matching = [(key, task) for key, task in _TASKS.items() if key[0] == workspace_key]
        for _key, task in matching:
            task.discard_when_done = True

    cancel_requested: list[str] = []
    for _key, task in matching:
        if not task.done_event.is_set():
            task.cancel_event.set()
            cancel_requested.append(task.task_id)

    deadline = monotonic() + max(0, wait_ms) / 1000
    for _key, task in matching:
        if task.done_event.is_set():
            continue
        remaining = deadline - monotonic()
        if remaining <= 0:
            break
        task.done_event.wait(remaining)

    discarded: list[str] = []
    still_running: list[str] = []
    with _TASKS_LOCK:
        for key, task in matching:
            if task.done_event.is_set():
                _TASKS.pop(key, None)
                discarded.append(task.task_id)
            else:
                still_running.append(task.task_id)

    return BackgroundDelegateCloseResult(
        task_ids=tuple(task.task_id for _key, task in matching),
        cancel_requested_task_ids=tuple(cancel_requested),
        discarded_task_ids=tuple(discarded),
        still_running_task_ids=tuple(still_running),
    )


def _find_task(workspace: RunWorkspace, task_id: str) -> BackgroundDelegateTask | None:
    with _TASKS_LOCK:
        return _TASKS.get((_workspace_key(workspace), task_id))


def _workspace_key(workspace: RunWorkspace) -> str:
    return str(workspace.session_dir.resolve())


def _prune_completed_tasks_locked() -> None:
    if len(_TASKS) < _MAX_RETAINED_TASKS:
        return
    completed_keys = [key for key, task in _TASKS.items() if task.done_event.is_set()]
    for key in completed_keys[: max(1, len(_TASKS) - _MAX_RETAINED_TASKS + 1)]:
        _TASKS.pop(key, None)
