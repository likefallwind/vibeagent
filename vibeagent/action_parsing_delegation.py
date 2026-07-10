from __future__ import annotations

from typing import Any

from .action_parsing_helpers import ActionParseError
from .types import DelegateTaskAction


def parse_delegation_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type != "delegate_task":
        return None

    task = value.get("task")
    if not isinstance(task, str) or not task.strip():
        raise ActionParseError("delegate_task action requires a non-empty task.", raw)
    task = task.strip()
    if len(task) > 4_000:
        raise ActionParseError("delegate_task action task must contain at most 4000 characters.", raw)

    context = value.get("context")
    if context is not None and not isinstance(context, str):
        raise ActionParseError("delegate_task action context must be a string when provided.", raw)
    context = context.strip() if isinstance(context, str) and context.strip() else None
    if context is not None and len(context) > 4_000:
        raise ActionParseError("delegate_task action context must contain at most 4000 characters.", raw)

    max_iterations = value.get("max_iterations", 4)
    if isinstance(max_iterations, bool) or not isinstance(max_iterations, int):
        raise ActionParseError("delegate_task action max_iterations must be an integer.", raw)
    if max_iterations < 1 or max_iterations > 8:
        raise ActionParseError("delegate_task action max_iterations must be between 1 and 8.", raw)

    return DelegateTaskAction(
        type="delegate_task",
        task=task,
        context=context,
        max_iterations=max_iterations,
    )
