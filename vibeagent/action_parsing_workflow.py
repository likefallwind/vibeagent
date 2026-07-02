from __future__ import annotations

from typing import Any

from .action_parsing_helpers import ActionParseError, parse_plan_items
from .types import FinishAction, UpdatePlanAction


WORKFLOW_ACTION_TYPES = {
    "update_plan",
    "finish",
}


def parse_workflow_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in WORKFLOW_ACTION_TYPES:
        return None

    if action_type == "update_plan":
        explanation = value.get("explanation")
        if explanation is not None and not isinstance(explanation, str):
            raise ActionParseError("update_plan action explanation must be a string when provided.", raw)
        return UpdatePlanAction(
            type="update_plan",
            explanation=explanation,
            plan=parse_plan_items(value.get("plan"), raw),
        )

    if action_type == "finish":
        message = value.get("message")
        if not isinstance(message, str):
            raise ActionParseError("finish action requires a string message.", raw)
        return FinishAction(type="finish", message=message)

    raise AssertionError(f"Unhandled workflow action type: {action_type!r}")
