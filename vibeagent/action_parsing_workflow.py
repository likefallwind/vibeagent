from __future__ import annotations

from typing import Any

from .action_parsing_helpers import ActionParseError, parse_plan_items
from .types import AskUserAction, FinishAction, UpdatePlanAction


WORKFLOW_ACTION_TYPES = {
    "ask_user",
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
