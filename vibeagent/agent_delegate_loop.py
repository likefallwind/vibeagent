from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .agent_delegate_completion import clip_delegate_summary, delegate_completion_message, finish_delegate_task
from .agent_delegate_context import compact_delegate_message_history
from .agent_delegate_tools import delegate_tool_definitions, execute_delegate_tool_call
from .agent_model import complete_with_retries
from .agent_runtime_utils import append_session_event, content_blocks_to_text, normalize_assistant_content, to_jsonable
from .agent_tool_results import record_subagent_tool_observation
from .types import (
    AgentLogger,
    ApprovalHandler,
    ApprovalPolicy,
    ChatClient,
    ChatMessage,
    ContentBlock,
    DelegateTaskAction,
    DelegateTaskObservation,
    Observation,
    TaskStep,
)
from .workspace_core import RunWorkspace
from .workspace_hooks import ProjectHooks
from .workspace_permissions import ProjectPermissions


@dataclass(frozen=True)
class DelegateLoopContext:
    workspace: RunWorkspace
    action: DelegateTaskAction
    client: ChatClient
    messages: list[ChatMessage]
    observations: list[Observation]
    steps: list[TaskStep]
    parent_iteration: int
    subagent_id: str
    profile_prompt: str | None
    allowed_tool_names: frozenset[str] | None
    active_tool_names: set[str]
    delegate_observation_start: int
    max_output_tokens: int
    model_retries: int
    model_retry_delay_ms: int
    model_timeout_ms: int
    command_timeout_ms: int
    logger: AgentLogger | None
    approval_handler: ApprovalHandler | None
    approval_policy: ApprovalPolicy
    hooks: ProjectHooks
    permissions: ProjectPermissions
    cancel_requested: Callable[[], bool] | None


def run_delegate_iterations(context: DelegateLoopContext) -> DelegateTaskObservation:
    tool_calls_used: list[str] = []
    auto_checkpoint_attempted = False

    for child_iteration in range(1, context.action.max_iterations + 1):
        if _cancellation_requested(context):
            return _finish_cancelled(context, child_iteration - 1, tool_calls_used)

        response, error_message = complete_with_retries(
            context.client,
            context.messages,
            tools=delegate_tool_definitions(
                context.action.mode,
                context.active_tool_names,
                context.approval_policy,
                context.allowed_tool_names,
            ),
            max_output_tokens=context.max_output_tokens,
            model_retries=context.model_retries,
            model_retry_delay_ms=context.model_retry_delay_ms,
            model_timeout_ms=context.model_timeout_ms,
            iteration=child_iteration,
            session_dir=context.workspace.session_dir,
            logger=context.logger,
            error_event_type="subagent_model_error",
            error_event_extra={
                "subagent_id": context.subagent_id,
                "parent_iteration": context.parent_iteration,
            },
        )
        if response is None:
            return finish_delegate_task(
                context.workspace,
                context.action,
                context.subagent_id,
                ok=False,
                summary="",
                iterations=child_iteration,
                tool_calls=tool_calls_used,
                message=error_message or "Subagent model request failed.",
                logger=context.logger,
            )
        if _cancellation_requested(context):
            return _finish_cancelled(context, child_iteration, tool_calls_used)

        assistant_content = normalize_assistant_content(response.content if hasattr(response, "content") else response)
        _record_delegate_model_response(context, child_iteration, assistant_content, getattr(response, "usage", None))
        context.messages.append(ChatMessage(role="assistant", content=assistant_content))

        tool_calls = [block for block in assistant_content if block.get("type") == "tool_call"]
        if not tool_calls:
            return _finish_text_response(context, child_iteration, tool_calls_used, assistant_content)

        tool_results: list[ContentBlock] = []
        for block in tool_calls:
            if _cancellation_requested(context):
                return _finish_cancelled(context, child_iteration, tool_calls_used)
            tool_id = str(block.get("id") or "")
            tool_name = str(block.get("name") or "")
            tool_input = block.get("input") or {}
            tool_calls_used.append(tool_name)
            _record_delegate_tool_call(context, child_iteration, tool_id, tool_name, tool_input)
            execution = execute_delegate_tool_call(
                context.workspace,
                mode=context.action.mode,
                tool_name=tool_name,
                tool_input=tool_input,
                active_tool_names=context.active_tool_names,
                observations=context.observations,
                steps=context.steps,
                iteration=child_iteration,
                command_timeout_ms=context.command_timeout_ms,
                logger=context.logger,
                approval_handler=context.approval_handler,
                approval_policy=context.approval_policy,
                auto_checkpoint_attempted=auto_checkpoint_attempted,
                allowed_tool_names=context.allowed_tool_names,
                hooks=context.hooks,
                permissions=context.permissions,
            )
            auto_checkpoint_attempted = execution.auto_checkpoint_attempted
            if execution.finish_action is not None:
                return _finish_tool_response(
                    context,
                    child_iteration,
                    tool_calls_used,
                    tool_id,
                    tool_name,
                    execution.finish_action.message,
                )
            if execution.observation is not None:
                tool_results.append(
                    record_subagent_tool_observation(
                        context.workspace,
                        subagent_id=context.subagent_id,
                        parent_iteration=context.parent_iteration,
                        iteration=child_iteration,
                        tool_id=tool_id,
                        tool_name=tool_name,
                        observation=execution.observation,
                        hook_results=execution.hook_results,
                    )
                )

        context.messages.append(ChatMessage(role="user", content=tool_results))
        context.messages[:] = compact_delegate_message_history(
            context.workspace,
            context.action,
            context.messages,
            context.observations[context.delegate_observation_start :],
            parent_iteration=context.parent_iteration,
            child_iteration=child_iteration,
            subagent_id=context.subagent_id,
            profile_prompt=context.profile_prompt,
        )

    return finish_delegate_task(
        context.workspace,
        context.action,
        context.subagent_id,
        ok=False,
        summary="",
        iterations=context.action.max_iterations,
        tool_calls=tool_calls_used,
        message=f"Subagent reached iteration limit ({context.action.max_iterations}) before completing the delegated task.",
        logger=context.logger,
    )


def _cancellation_requested(context: DelegateLoopContext) -> bool:
    return context.cancel_requested is not None and context.cancel_requested()


def _finish_cancelled(
    context: DelegateLoopContext,
    iterations: int,
    tool_calls_used: list[str],
) -> DelegateTaskObservation:
    return finish_delegate_task(
        context.workspace,
        context.action,
        context.subagent_id,
        ok=False,
        summary="",
        iterations=iterations,
        tool_calls=tool_calls_used,
        message="Background subagent task was cancelled.",
        logger=context.logger,
        cancelled=True,
    )


def _record_delegate_model_response(
    context: DelegateLoopContext,
    child_iteration: int,
    assistant_content: list[ContentBlock],
    usage: object | None,
) -> None:
    payload: dict[str, object] = {
        "subagent_id": context.subagent_id,
        "parent_iteration": context.parent_iteration,
        "iteration": child_iteration,
        "content": assistant_content,
    }
    if usage is not None:
        payload["usage"] = to_jsonable(usage)
    append_session_event(context.workspace.session_dir, "subagent_model", payload)


def _record_delegate_tool_call(
    context: DelegateLoopContext,
    child_iteration: int,
    tool_id: str,
    tool_name: str,
    tool_input: object,
) -> None:
    append_session_event(
        context.workspace.session_dir,
        "subagent_tool_call",
        {
            "subagent_id": context.subagent_id,
            "parent_iteration": context.parent_iteration,
            "iteration": child_iteration,
            "id": tool_id,
            "name": tool_name,
            "input": tool_input,
        },
    )


def _finish_text_response(
    context: DelegateLoopContext,
    child_iteration: int,
    tool_calls_used: list[str],
    assistant_content: list[ContentBlock],
) -> DelegateTaskObservation:
    summary = content_blocks_to_text(assistant_content).strip()
    return finish_delegate_task(
        context.workspace,
        context.action,
        context.subagent_id,
        ok=bool(summary),
        summary=clip_delegate_summary(summary) if summary else "",
        iterations=child_iteration,
        tool_calls=tool_calls_used,
        message=(
            delegate_completion_message(context.action)
            if summary
            else "Subagent response did not include text or a tool call."
        ),
        logger=context.logger,
    )


def _finish_tool_response(
    context: DelegateLoopContext,
    child_iteration: int,
    tool_calls_used: list[str],
    tool_id: str,
    tool_name: str,
    message: str,
) -> DelegateTaskObservation:
    summary = clip_delegate_summary(message)
    return finish_delegate_task(
        context.workspace,
        context.action,
        context.subagent_id,
        ok=bool(summary),
        summary=summary,
        iterations=child_iteration,
        tool_calls=tool_calls_used,
        message=(
            delegate_completion_message(context.action)
            if summary
            else "Subagent finish call did not include a report."
        ),
        logger=context.logger,
        tool_event={
            "parent_iteration": context.parent_iteration,
            "iteration": child_iteration,
            "id": tool_id,
            "name": tool_name,
        },
    )
