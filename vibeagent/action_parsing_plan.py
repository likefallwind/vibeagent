from __future__ import annotations

from typing import Any

from .action_parsing_scalars import ActionParseError
from .types import PlanItem, UpdatePlanAction


PLAN_ITEM_STATUS_ALIASES = {
    "complete": "completed",
    "completed": "completed",
    "cancelled": "completed",
    "canceled": "completed",
    "done": "completed",
    "finished": "completed",
    "skipped": "completed",
    "success": "completed",
    "succeeded": "completed",
    "active": "in_progress",
    "doing": "in_progress",
    "in-progress": "in_progress",
    "in_progress": "in_progress",
    "started": "in_progress",
    "pending": "pending",
    "todo": "pending",
    "to-do": "pending",
    "to do": "pending",
    "to_do": "pending",
    "not-started": "pending",
    "not started": "pending",
    "not_started": "pending",
    "blocked": "pending",
    "deferred": "pending",
    "open": "pending",
    "paused": "pending",
    "queued": "pending",
    "waiting": "pending",
}
PLAN_ITEM_STATUS_VALUES = set(PLAN_ITEM_STATUS_ALIASES)
PLAN_ITEM_SCHEMA_STATUS_VALUES = ("complete", "completed", "done", "in-progress", "in_progress", "pending", "todo")


def parse_plan_items(value: Any, raw: str) -> list[PlanItem]:
    if not isinstance(value, list) or not value:
        raise ActionParseError("update_plan action requires a non-empty plan list.", raw)
    if len(value) > 20:
        raise ActionParseError("update_plan action plan must contain at most 20 items.", raw)

    items: list[PlanItem] = []
    in_progress_count = 0
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ActionParseError(f"update_plan item {index} must be an object.", raw)
        step = item.get("step")
        status = normalize_plan_item_status(item.get("status"))
        if not isinstance(step, str) or not step.strip():
            raise ActionParseError(f"update_plan item {index} requires a non-empty step.", raw)
        if status is None:
            raise ActionParseError(f"update_plan item {index} has an invalid status.", raw)
        if status == "in_progress":
            in_progress_count += 1
        active_form = parse_active_form(item)
        items.append(PlanItem(step=step.strip(), status=status, active_form=active_form))

    if in_progress_count > 1:
        raise ActionParseError("update_plan action allows at most one in_progress item.", raw)
    return items


def normalize_plan_item_status(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return PLAN_ITEM_STATUS_ALIASES.get(value.strip().lower())


def parse_active_form(item: dict[str, Any]) -> str | None:
    value = item.get("active_form")
    if value is None:
        value = item.get("activeForm")
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def summarize_plan_update(action: UpdatePlanAction) -> str:
    current = next((item.step for item in action.plan if item.status == "in_progress"), None)
    if current:
        return f"Plan updated. Current: {current}"
    if action.explanation and action.explanation.strip():
        return f"Plan updated. {action.explanation.strip()}"
    return "Plan updated."
