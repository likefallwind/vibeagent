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
    UserInputRequest,
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
    request = UserInputRequest(
        question=action.question,
        options=list(action.options),
        allow_free_text=action.allow_free_text,
    )
    append_session_event(
        workspace.session_dir,
        "user_input_requested",
        {"iteration": iteration, "step": step, "request": request},
    )

    answer: str | None = None
    message = "User input is unavailable in this run. Return the question to the user without guessing."
    if handler is not None:
        try:
            provided = handler(request)
        except (EOFError, KeyboardInterrupt):
            provided = None
            message = "User input was interrupted. Return the question to the user without guessing."
        except Exception as error:
            provided = None
            message = f"User input failed: {error}"
        if provided is not None and provided.strip():
            candidate = provided.strip()
            if action.allow_free_text or candidate in action.options:
                answer = candidate
                message = f"User answered: {candidate}"
            else:
                message = "User response did not match one of the allowed options. Ask again without guessing."

    observation = UserInputObservation(
        kind="ask_user",
        question=action.question,
        options=list(action.options),
        answer=answer,
        cancelled=answer is None,
        message=message,
    )
    append_session_event(
        workspace.session_dir,
        "user_input_answered",
        {"iteration": iteration, "step": step, "result": observation},
    )
    complete_task_step(workspace, step, observation, iteration, logger)
    return observation
