from __future__ import annotations

from collections.abc import Callable

from .agent_lifecycle_runtime import AgentLifecycleRuntime
from .agent_result import AgentResult
from .types import AgentLogger, Observation, PlanItem, TaskStep
from .workspace_core import RunWorkspace


FinishWithConversation = Callable[..., AgentResult]
FinishModelMessage = Callable[
    [
        RunWorkspace,
        bool,
        str,
        int,
        list[Observation],
        list[TaskStep],
        list[PlanItem],
        int,
        AgentLogger | None,
    ],
    AgentResult,
]


def build_message_display_finish(
    lifecycle: AgentLifecycleRuntime,
    finish_with_conversation: FinishWithConversation,
    hook_system_messages: list[str],
    *,
    assistant_text: str,
    turn_id: str,
    message_id: str,
) -> FinishModelMessage:
    def finish_model_message(
        workspace: RunWorkspace,
        success: bool,
        message: str,
        iteration: int,
        observations: list[Observation],
        steps: list[TaskStep],
        plan: list[PlanItem],
        timeout_ms: int,
        logger: AgentLogger | None,
    ) -> AgentResult:
        display_message: str | None = None
        if success and assistant_text:
            display = lifecycle.message_display(
                workspace,
                assistant_text,
                turn_id=turn_id,
                message_id=message_id,
                iteration=iteration,
            )
            display_message = display.display_content
            hook_system_messages.extend(display.system_messages)
        return finish_with_conversation(
            workspace,
            success,
            message,
            iteration,
            observations,
            steps,
            plan,
            timeout_ms,
            logger,
            display_message=display_message,
        )

    return finish_model_message


__all__ = ["build_message_display_finish"]
