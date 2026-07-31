from __future__ import annotations

from typing import Any

from .action_parsing_helpers import ActionParseError, normalize_plan_item_status, parse_active_form, parse_plan_items
from .types import AskUserAction, FinishAction, PlanItem, UpdatePlanAction


WORKFLOW_ACTION_TYPES = {
    "ask_user",
    "todo_write",
    "update_plan",
    "finish",
}


def parse_workflow_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in WORKFLOW_ACTION_TYPES:
        return None

    if action_type == "ask_user":
        question = value.get("question")
        if not isinstance(question, str) or not question.strip():
            raise ActionParseError("ask_user action requires a non-empty question.", raw)
        if len(question.strip()) > 1_000:
            raise ActionParseError("ask_user action question must contain at most 1000 characters.", raw)
        raw_options = value.get("options", [])
        if not isinstance(raw_options, list) or any(not isinstance(option, str) for option in raw_options):
            raise ActionParseError("ask_user action options must be a list of strings.", raw)
        options = [option.strip() for option in raw_options]
        if any(not option for option in options):
            raise ActionParseError("ask_user action options must not contain empty values.", raw)
        if len(options) > 4:
            raise ActionParseError("ask_user action options must contain at most 4 values.", raw)
        if any(len(option) > 200 for option in options):
            raise ActionParseError("ask_user action options must contain at most 200 characters each.", raw)
        if len(set(options)) != len(options):
            raise ActionParseError("ask_user action options must be unique.", raw)
        allow_free_text = value.get("allow_free_text", True)
        if not isinstance(allow_free_text, bool):
            raise ActionParseError("ask_user action allow_free_text must be a boolean.", raw)
        if not options and not allow_free_text:
            raise ActionParseError("ask_user action requires options when free text is disabled.", raw)
        return AskUserAction(
            type="ask_user",
            question=question.strip(),
            options=options,
            allow_free_text=allow_free_text,
        )

    if action_type in {"update_plan", "todo_write"}:
        explanation = value.get("explanation")
        if explanation is not None and not isinstance(explanation, str):
            raise ActionParseError(f"{action_type} action explanation must be a string when provided.", raw)
        if action_type == "update_plan":
            plan = parse_plan_items(value.get("plan"), raw)
        else:
            plan = parse_plan_items(value.get("plan"), raw) if "plan" in value else parse_todo_items(value.get("todos"), raw)
        return UpdatePlanAction(
            type="update_plan",
            explanation=explanation,
            plan=plan,
        )

    if action_type == "finish":
        message = value.get("message")
        if not isinstance(message, str):
            raise ActionParseError("finish action requires a string message.", raw)
        return FinishAction(type="finish", message=message)

    raise AssertionError(f"Unhandled workflow action type: {action_type!r}")


def parse_todo_items(value: Any, raw: str) -> list[PlanItem]:
    if not isinstance(value, list) or not value:
        raise ActionParseError("todo_write action requires a non-empty todos list.", raw)
    if len(value) > 20:
        raise ActionParseError("todo_write action todos must contain at most 20 items.", raw)

    items: list[PlanItem] = []
    in_progress_count = 0
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ActionParseError(f"todo_write item {index} must be an object.", raw)
        content = item.get("content")
        status = normalize_plan_item_status(item.get("status"))
        if not isinstance(content, str) or not content.strip():
            raise ActionParseError(f"todo_write item {index} requires non-empty content.", raw)
        if status is None:
            raise ActionParseError(f"todo_write item {index} has an invalid status.", raw)
        if status == "in_progress":
            in_progress_count += 1
        items.append(PlanItem(step=content.strip(), status=status, active_form=parse_active_form(item)))

    if in_progress_count > 1:
        raise ActionParseError("todo_write action allows at most one in_progress item.", raw)
    return items
