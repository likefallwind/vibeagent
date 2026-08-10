from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .agent_runtime_utils import (
    append_session_event,
    content_blocks_to_text,
    normalize_assistant_content,
    to_jsonable,
)
from .types import (
    AgentLogger,
    ChatMessage,
    ContentBlock,
    Observation,
    PlanItem,
    TaskStep,
)
from .workspace_core import RunWorkspace


@dataclass(frozen=True)
class RecordedModelTurn:
    assistant_content: list[ContentBlock]
    tool_calls: list[ContentBlock]


@dataclass(frozen=True)
class NoToolCallResult:
    handled: bool
    should_continue: bool = False
    result: object | None = None


CompletionBlockedFeedback = Callable[
    [
        RunWorkspace,
        bool,
        str,
        int,
        int,
        list[Observation],
        list[PlanItem],
        int,
        AgentLogger | None,
    ],
    str | None,
]
FinishAgentRun = Callable[
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
    object,
]
StopFeedbackIfNeeded = Callable[[str, int], str | None]


def record_model_turn(
    workspace: RunWorkspace,
    messages: list[ChatMessage],
    response: object,
    iteration: int,
) -> RecordedModelTurn:
    assistant_content = normalize_assistant_content(
        response.content if hasattr(response, "content") else response
    )
    model_event: dict[str, Any] = {"iteration": iteration, "content": assistant_content}
    response_usage = response.usage if hasattr(response, "usage") else None
    if response_usage is not None:
        model_event["usage"] = to_jsonable(response_usage)
    append_session_event(workspace.session_dir, "model", model_event)
    messages.append(ChatMessage(role="assistant", content=assistant_content))
    return RecordedModelTurn(
        assistant_content=assistant_content,
        tool_calls=[
            block for block in assistant_content if block.get("type") == "tool_call"
        ],
    )


def handle_no_tool_call_response(
    workspace: RunWorkspace,
    messages: list[ChatMessage],
    assistant_content: list[ContentBlock],
    *,
    iteration: int,
    max_iterations: int,
    observations: list[Observation],
    steps: list[TaskStep],
    plan: list[PlanItem],
    command_timeout_ms: int,
    logger: AgentLogger | None,
    completion_blocked_feedback_if_needed_func: CompletionBlockedFeedback,
    finish_agent_run_func: FinishAgentRun,
    stop_feedback_if_needed_func: StopFeedbackIfNeeded | None = None,
) -> NoToolCallResult:
    text = content_blocks_to_text(assistant_content).strip()
    if text:
        feedback = completion_blocked_feedback_if_needed_func(
            workspace,
            True,
            text,
            iteration,
            max_iterations,
            observations,
            plan,
            command_timeout_ms,
            logger,
        )
        if feedback is not None:
            messages.append(ChatMessage(role="user", content=feedback))
            return NoToolCallResult(handled=True, should_continue=True)
        stop_feedback = (
            stop_feedback_if_needed_func(text, iteration)
            if stop_feedback_if_needed_func
            else None
        )
        if stop_feedback is not None:
            messages.append(ChatMessage(role="user", content=stop_feedback))
            return NoToolCallResult(handled=True, should_continue=True)
        if logger:
            logger("finished", text)
        return NoToolCallResult(
            handled=True,
            result=finish_agent_run_func(
                workspace,
                True,
                text,
                iteration,
                observations,
                steps,
                plan,
                command_timeout_ms,
                logger,
            ),
        )
    return NoToolCallResult(
        handled=True,
        result=finish_agent_run_func(
            workspace,
            False,
            "Model response did not include text or a tool call.",
            iteration,
            observations,
            steps,
            plan,
            command_timeout_ms,
            logger,
        ),
    )
