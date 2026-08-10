from __future__ import annotations

from .agent_action_logging import log_action
from .agent_runtime_utils import append_session_event
from .agent_steps import complete_task_step, start_task_step
from .types import (
    AgentLogger,
    AskUserAction,
    TaskStep,
    UserInputHandler,
    UserInputObservation,
)
from .user_input_runtime import (
    normalize_user_input_answer,
    serialize_user_input_request,
    user_input_requests,
)
from .workspace_core import RunWorkspace


def execute_user_input_action(
    workspace: RunWorkspace,
    action: AskUserAction,
    steps: list[TaskStep],
    iteration: int,
    logger: AgentLogger | None,
    handler: UserInputHandler | None,
) -> UserInputObservation:
    step = start_task_step(workspace, steps, iteration, action, logger)
    log_action(logger, action)
    requests = user_input_requests(action)
    append_session_event(
        workspace.session_dir,
        "user_input_requested",
        {
            "iteration": iteration,
            "step": step,
            "request": requests[0],
            "requests": requests,
        },
    )

    answers: dict[str, str] = {}
    answer_error: str | None = None
    message = "User input is unavailable in this run. Return the question to the user without guessing."
    if handler is not None or action.answers:
        for request in requests:
            try:
                provided = action.answers.get(request.question)
                if provided is None:
                    if handler is None:
                        break
                    provided = handler(request)
            except (EOFError, KeyboardInterrupt):
                message = "User input was interrupted. Return the unanswered question to the user without guessing."
                break
            except Exception as error:
                message = f"User input failed: {error}"
                break
            answer, answer_error = normalize_user_input_answer(request, provided)
            if answer is None:
                if answer_error is not None:
                    message = f"{answer_error} Ask again without guessing."
                break
            answers[request.question] = answer

    cancelled = len(answers) != len(requests)
    if not cancelled:
        if len(requests) == 1:
            message = f"User answered: {answers[requests[0].question]}"
        else:
            message = f"User answered all {len(requests)} questions."
    elif answers and answer_error is None:
        message = (
            f"User answered {len(answers)} of {len(requests)} questions. "
            "Return the unanswered question to the user without guessing."
        )

    observation = UserInputObservation(
        kind="ask_user",
        question=requests[0].question,
        options=list(requests[0].options),
        answer=answers.get(requests[0].question),
        cancelled=cancelled,
        message=message,
        questions=(
            [serialize_user_input_request(request) for request in requests]
            if action.questions
            else []
        ),
        answers=answers,
    )
    append_session_event(
        workspace.session_dir,
        "user_input_answered",
        {"iteration": iteration, "step": step, "result": observation},
    )
    complete_task_step(workspace, step, observation, iteration, logger)
    return observation
