from __future__ import annotations

from dataclasses import replace

from .session_task_types import SessionTask


def add_dependencies(
    tasks: list[SessionTask],
    index: int,
    add_blocks: tuple[str, ...],
    add_blocked_by: tuple[str, ...],
) -> str | None:
    current_id = tasks[index].id
    known_ids = {task.id for task in tasks}
    requested = (*add_blocks, *add_blocked_by)
    missing = [task_id for task_id in requested if task_id not in known_ids]
    if missing:
        return f"Unknown task dependency: {missing[0]}"
    if current_id in requested:
        return "A task cannot block or be blocked by itself."
    for target_id in add_blocks:
        _add_edge(tasks, current_id, target_id)
    for blocker_id in add_blocked_by:
        _add_edge(tasks, blocker_id, current_id)
    return None


def remove_dependency(task: SessionTask, removed_id: str) -> SessionTask:
    return replace(
        task,
        blocks=tuple(value for value in task.blocks if value != removed_id),
        blocked_by=tuple(value for value in task.blocked_by if value != removed_id),
    )


def has_dependency_cycle(tasks: tuple[SessionTask, ...]) -> bool:
    edges = {task.id: task.blocks for task in tasks}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> bool:
        if task_id in visiting:
            return True
        if task_id in visited:
            return False
        visiting.add(task_id)
        if any(visit(blocked_id) for blocked_id in edges.get(task_id, ())):
            return True
        visiting.remove(task_id)
        visited.add(task_id)
        return False

    return any(visit(task_id) for task_id in edges)


def _add_edge(tasks: list[SessionTask], blocker_id: str, blocked_id: str) -> None:
    blocker_index = next(index for index, task in enumerate(tasks) if task.id == blocker_id)
    blocked_index = next(index for index, task in enumerate(tasks) if task.id == blocked_id)
    blocker = tasks[blocker_index]
    blocked = tasks[blocked_index]
    tasks[blocker_index] = replace(blocker, blocks=_append_unique(blocker.blocks, blocked_id))
    tasks[blocked_index] = replace(blocked, blocked_by=_append_unique(blocked.blocked_by, blocker_id))


def _append_unique(values: tuple[str, ...], value: str) -> tuple[str, ...]:
    return values if value in values else (*values, value)
