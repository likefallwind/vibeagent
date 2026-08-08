from __future__ import annotations

import json
from typing import Any

from .action_parsing_scalars import ActionParseError
from .action_task_types import TaskCreateAction, TaskGetAction, TaskListAction, TaskUpdateAction


TASK_ACTION_TYPES = {"task_create", "task_get", "task_list", "task_update"}
TASK_STATUSES = {"pending", "in_progress", "completed", "deleted"}


def parse_task_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in TASK_ACTION_TYPES:
        return None
    if action_type == "task_create":
        subject = _required_text(value.get("subject"), "TaskCreate subject", raw, 500)
        description = _required_text(value.get("description"), "TaskCreate description", raw, 10_000)
        active_form = _optional_text(value.get("active_form"), "TaskCreate activeForm", raw, 500)
        metadata = _metadata(value.get("metadata", {}), "TaskCreate metadata", raw)
        return TaskCreateAction(
            type="task_create",
            subject=subject,
            description=description,
            active_form=active_form,
            metadata=metadata,
        )
    if action_type == "task_get":
        return TaskGetAction(type="task_get", task_id=_task_id(value.get("task_id"), "TaskGet", raw))
    if action_type == "task_list":
        return TaskListAction(type="task_list")

    task_id = _task_id(value.get("task_id"), "TaskUpdate", raw)
    status = value.get("status")
    if status is not None and status not in TASK_STATUSES:
        raise ActionParseError("TaskUpdate status must be pending, in_progress, completed, or deleted.", raw)
    subject = _optional_text(value.get("subject"), "TaskUpdate subject", raw, 500)
    description = _optional_text(value.get("description"), "TaskUpdate description", raw, 10_000)
    active_form_set = "active_form" in value
    active_form = _nullable_text(value.get("active_form"), "TaskUpdate activeForm", raw, 500)
    owner_set = "owner" in value
    owner = _nullable_text(value.get("owner"), "TaskUpdate owner", raw, 200)
    metadata = _metadata(value.get("metadata"), "TaskUpdate metadata", raw) if "metadata" in value else None
    add_blocks = _task_ids(value.get("add_blocks", []), "TaskUpdate addBlocks", raw)
    add_blocked_by = _task_ids(value.get("add_blocked_by", []), "TaskUpdate addBlockedBy", raw)
    if not any(
        (
            status is not None,
            subject is not None,
            description is not None,
            active_form_set,
            owner_set,
            metadata is not None,
            add_blocks,
            add_blocked_by,
        )
    ):
        raise ActionParseError("TaskUpdate requires at least one field to update.", raw)
    return TaskUpdateAction(
        type="task_update",
        task_id=task_id,
        status=status,
        subject=subject,
        description=description,
        active_form=active_form,
        active_form_set=active_form_set,
        add_blocks=add_blocks,
        add_blocked_by=add_blocked_by,
        owner=owner,
        owner_set=owner_set,
        metadata=metadata,
    )


def _required_text(value: Any, label: str, raw: str, max_chars: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ActionParseError(f"{label} must be a non-empty string.", raw)
    text = value.strip()
    if len(text) > max_chars:
        raise ActionParseError(f"{label} must contain at most {max_chars} characters.", raw)
    return text


def _optional_text(value: Any, label: str, raw: str, max_chars: int) -> str | None:
    if value is None:
        return None
    return _required_text(value, label, raw, max_chars)


def _nullable_text(value: Any, label: str, raw: str, max_chars: int) -> str | None:
    if value is None:
        return None
    return _required_text(value, label, raw, max_chars)


def _task_id(value: Any, label: str, raw: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 64:
        raise ActionParseError(f"{label} taskId must be a non-empty string of at most 64 characters.", raw)
    return value.strip()


def _task_ids(value: Any, label: str, raw: str) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) > 100:
        raise ActionParseError(f"{label} must be a list of at most 100 task IDs.", raw)
    ids = tuple(_task_id(item, label, raw) for item in value)
    if len(ids) != len(set(ids)):
        raise ActionParseError(f"{label} must not contain duplicate task IDs.", raw)
    return ids


def _metadata(value: Any, label: str, raw: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ActionParseError(f"{label} must be an object.", raw)
    try:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError) as error:
        raise ActionParseError(f"{label} must be JSON serializable.", raw) from error
    if len(encoded) > 20_000:
        raise ActionParseError(f"{label} must contain at most 20000 encoded characters.", raw)
    return dict(value)
