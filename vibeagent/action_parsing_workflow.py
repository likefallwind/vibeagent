from __future__ import annotations

from typing import Any

from .action_parsing_helpers import ActionParseError, normalize_plan_item_status, parse_active_form, parse_plan_items
from .types import (
    AskUserAction,
    AskUserOption,
    AskUserQuestion,
    EnterPlanModeAction,
    ExitPlanModeAction,
    FinishAction,
    PlanItem,
    UpdatePlanAction,
)


WORKFLOW_ACTION_TYPES = {
    "ask_user",
    "todo_write",
    "update_plan",
    "finish",
    "enter_plan_mode",
    "exit_plan_mode",
}


def parse_workflow_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in WORKFLOW_ACTION_TYPES:
        return None

    if action_type == "ask_user":
        if "answers" in value:
            raise ActionParseError(
                "ask_user answers are accepted only from PreToolUse updatedInput.",
                raw,
            )
        if "questions" in value:
            return _parse_structured_user_questions(value, raw)
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

    if action_type == "enter_plan_mode":
        if set(value) != {"type"}:
            raise ActionParseError("enter_plan_mode action does not accept input fields.", raw)
        return EnterPlanModeAction(type="enter_plan_mode")

    if action_type == "exit_plan_mode":
        allowed_prompts = value.get("allowed_prompts", [])
        if (
            not isinstance(allowed_prompts, list)
            or len(allowed_prompts) > 20
            or any(
                not isinstance(item, dict)
                or any(
                    not isinstance(key, str) or not isinstance(item_value, str)
                    for key, item_value in item.items()
                )
                for item in allowed_prompts
            )
        ):
            raise ActionParseError(
                "exit_plan_mode allowed_prompts must contain at most 20 string maps.",
                raw,
            )
        return ExitPlanModeAction(
            type="exit_plan_mode",
            plan=parse_plan_items(value.get("plan"), raw),
            allowed_prompts=[dict(item) for item in allowed_prompts],
        )

    if action_type == "finish":
        message = value.get("message")
        if not isinstance(message, str):
            raise ActionParseError("finish action requires a string message.", raw)
        return FinishAction(type="finish", message=message)

    raise AssertionError(f"Unhandled workflow action type: {action_type!r}")


def _parse_structured_user_questions(value: dict[str, Any], raw: str) -> AskUserAction:
    if any(key in value for key in ("question", "options", "allow_free_text")):
        raise ActionParseError(
            "ask_user action cannot combine questions with legacy single-question fields.",
            raw,
        )
    raw_questions = value.get("questions")
    if not isinstance(raw_questions, list) or not raw_questions:
        raise ActionParseError("ask_user action questions must be a non-empty list.", raw)
    if len(raw_questions) > 4:
        raise ActionParseError("ask_user action questions must contain at most 4 items.", raw)

    questions: list[AskUserQuestion] = []
    seen_questions: set[str] = set()
    for index, item in enumerate(raw_questions, start=1):
        if not isinstance(item, dict):
            raise ActionParseError(f"ask_user question {index} must be an object.", raw)
        unknown = set(item) - {"question", "header", "options", "multiSelect"}
        if unknown:
            raise ActionParseError(
                f"ask_user question {index} has unknown field {sorted(unknown)[0]!r}.",
                raw,
            )
        question = item.get("question")
        header = item.get("header")
        raw_options = item.get("options")
        multi_select = item.get("multiSelect", False)
        if not isinstance(question, str) or not question.strip():
            raise ActionParseError(f"ask_user question {index} requires non-empty question.", raw)
        question = question.strip()
        if len(question) > 1_000:
            raise ActionParseError(f"ask_user question {index} exceeds 1000 characters.", raw)
        if question in seen_questions:
            raise ActionParseError("ask_user structured questions must be unique.", raw)
        seen_questions.add(question)
        if not isinstance(header, str) or not header.strip():
            raise ActionParseError(f"ask_user question {index} requires non-empty header.", raw)
        header = header.strip()
        if len(header) > 12:
            raise ActionParseError(f"ask_user question {index} header exceeds 12 characters.", raw)
        if not isinstance(raw_options, list) or not 2 <= len(raw_options) <= 4:
            raise ActionParseError(
                f"ask_user question {index} options must contain 2 to 4 items.",
                raw,
            )
        if not isinstance(multi_select, bool):
            raise ActionParseError(f"ask_user question {index} multiSelect must be a boolean.", raw)

        options: list[AskUserOption] = []
        seen_labels: set[str] = set()
        for option_index, option in enumerate(raw_options, start=1):
            if not isinstance(option, dict) or set(option) != {"label", "description"}:
                raise ActionParseError(
                    f"ask_user question {index} option {option_index} requires label and description.",
                    raw,
                )
            label = option.get("label")
            description = option.get("description")
            if not isinstance(label, str) or not label.strip() or len(label.strip()) > 200:
                raise ActionParseError(
                    f"ask_user question {index} option {option_index} has invalid label.",
                    raw,
                )
            label = label.strip()
            if label in seen_labels:
                raise ActionParseError(f"ask_user question {index} option labels must be unique.", raw)
            seen_labels.add(label)
            if (
                not isinstance(description, str)
                or not description.strip()
                or len(description.strip()) > 500
            ):
                raise ActionParseError(
                    f"ask_user question {index} option {option_index} has invalid description.",
                    raw,
                )
            options.append(
                AskUserOption(label=label, description=description.strip())
            )
        questions.append(
            AskUserQuestion(
                question=question,
                header=header,
                options=options,
                multi_select=multi_select,
            )
        )

    first = questions[0]
    return AskUserAction(
        type="ask_user",
        question=first.question,
        options=[option.label for option in first.options],
        allow_free_text=True,
        questions=questions,
    )


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
