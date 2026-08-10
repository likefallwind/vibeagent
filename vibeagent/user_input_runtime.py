from __future__ import annotations

from .types import AskUserAction, UserInputAnswer, UserInputRequest


def user_input_requests(action: AskUserAction) -> list[UserInputRequest]:
    if not action.questions:
        return [
            UserInputRequest(
                question=action.question,
                options=list(action.options),
                allow_free_text=action.allow_free_text,
            )
        ]
    return [
        UserInputRequest(
            question=item.question,
            header=item.header,
            options=[option.label for option in item.options],
            option_descriptions={
                option.label: option.description for option in item.options
            },
            allow_free_text=True,
            multi_select=item.multi_select,
        )
        for item in action.questions
    ]


def serialize_user_input_request(request: UserInputRequest) -> dict[str, object]:
    options = [
        {
            "label": label,
            "description": (request.option_descriptions or {}).get(label, ""),
        }
        for label in request.options
    ]
    return {
        "question": request.question,
        "header": request.header,
        "options": options,
        "multiSelect": request.multi_select,
        "allowFreeText": request.allow_free_text,
    }


def normalize_user_input_answer(
    request: UserInputRequest,
    provided: UserInputAnswer | None,
) -> tuple[str | None, str | None]:
    if provided is None:
        return None, None
    raw_values = provided if isinstance(provided, list) else [provided]
    if not raw_values or any(not isinstance(value, str) for value in raw_values):
        return None, "User response must contain text selections."
    values = [value.strip() for value in raw_values]
    if any(not value for value in values):
        return None, "User response must not contain empty selections."
    if len(set(values)) != len(values):
        return None, "User response contains duplicate selections."
    if not request.multi_select and len(values) != 1:
        return None, "User response selected multiple values for a single-choice question."
    if len(values) > max(1, len(request.options)):
        return None, "User response selected more values than the question provides."
    if all(value in request.options for value in values):
        return ", ".join(values), None
    if request.allow_free_text and len(values) == 1:
        return values[0], None
    return None, "User response did not match the allowed options."


__all__ = [
    "normalize_user_input_answer",
    "serialize_user_input_request",
    "user_input_requests",
]
