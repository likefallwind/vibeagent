from __future__ import annotations

from dataclasses import replace

from .action_parsing_helpers import ActionParseError
from .types import AskUserAction


def apply_hook_supplied_answers(
    action: object,
    value: object,
    raw: str,
) -> object:
    if not isinstance(action, AskUserAction):
        raise ActionParseError(
            "PreToolUse updatedInput.answers is valid only for AskUserQuestion.",
            raw,
        )
    if not isinstance(value, dict):
        raise ActionParseError("ask_user answers must be an object.", raw)
    questions = (
        {question.question for question in action.questions}
        if action.questions
        else {action.question}
    )
    answers: dict[str, str] = {}
    for question, answer in value.items():
        if not isinstance(question, str) or question not in questions:
            raise ActionParseError("ask_user answers contain an unknown question.", raw)
        if not isinstance(answer, str) or not answer.strip():
            raise ActionParseError(
                "ask_user answers must contain non-empty strings.", raw
            )
        if len(answer.strip()) > 2_000:
            raise ActionParseError(
                "ask_user answers must not exceed 2000 characters.", raw
            )
        answers[question] = answer.strip()
    return replace(action, answers=answers)


__all__ = ["apply_hook_supplied_answers"]
