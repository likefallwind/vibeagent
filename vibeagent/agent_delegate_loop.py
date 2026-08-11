from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .auto_mode import AutoModeRuntime
from .agent_delegate_completion import clip_delegate_summary, delegate_completion_message, finish_delegate_task
from .agent_delegate_context import compact_delegate_message_history, recover_delegate_context_limit
from .agent_delegate_events import record_delegate_model_response, record_delegate_tool_call
from .agent_delegate_hooks import DelegateLifecycleHooks
from .agent_delegate_inbox import DelegateInbox
from .agent_delegate_tools import delegate_tool_definitions, execute_delegate_tool_call
from .agent_execution_support import execute_action_safely
from .agent_hook_prompt import HookModelRuntime
from .agent_lifecycle_hooks import run_instruction_loaded_hooks
from .agent_model import complete_with_retries
from .agent_post_tool_batch_hooks import append_batch_context, run_post_tool_batch_hooks
from .agent_runtime_utils import content_blocks_to_text, normalize_assistant_content
from .agent_tool_results import record_subagent_tool_observation
from .nested_delegate_runtime import NestedDelegateRuntime
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
    ToolErrorObservation,
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
    lifecycle: DelegateLifecycleHooks
    profile_prompt: str | None
    allowed_tool_names: frozenset[str] | None
    disallowed_tool_names: frozenset[str]
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
    nested_runtime: NestedDelegateRuntime
    hook_model_runtime: HookModelRuntime | None = None
    auto_mode_runtime: AutoModeRuntime | None = None
    transcript_checkpoint: Callable[[list[ChatMessage]], None] | None = None
    inbox: DelegateInbox | None = None


def run_delegate_iterations(context: DelegateLoopContext) -> DelegateTaskObservation:
    tool_calls_used: list[str] = []
    auto_checkpoint_attempted = False

    for child_iteration in range(1, context.action.max_iterations + 1):
        if context.inbox is not None:
            context.inbox.append_to(context.messages)
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
                context.disallowed_tool_names,
                context.nested_runtime.can_delegate,
                context.nested_runtime.team_member_name is not None,
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
            recover_context=lambda: recover_delegate_context_limit(
                context.workspace,
                context.action,
                context.messages,
                context.observations[context.delegate_observation_start :],
                parent_iteration=context.parent_iteration,
                child_iteration=child_iteration,
                subagent_id=context.subagent_id,
                profile_prompt=context.profile_prompt,
            ),
        )
        if response is None:
            if context.inbox is not None:
                context.inbox.close()
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
        record_delegate_model_response(
            context.workspace,
            subagent_id=context.subagent_id,
            parent_iteration=context.parent_iteration,
            iteration=child_iteration,
            content=assistant_content,
            usage=getattr(response, "usage", None),
        )
        context.messages.append(ChatMessage(role="assistant", content=assistant_content))
        _checkpoint(context)

        tool_calls = [block for block in assistant_content if block.get("type") == "tool_call"]
        if not tool_calls:
            stop_feedback = _text_stop_feedback(context, child_iteration, assistant_content)
            if stop_feedback is not None:
                context.messages.append(ChatMessage(role="user", content=stop_feedback))
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
                _checkpoint(context)
                continue
            if context.inbox is not None and context.inbox.append_to(context.messages, final=True):
                continue
            idle_feedback, idle_halt = context.lifecycle.teammate_idle_feedback(
                child_iteration
            )
            if idle_halt is not None:
                return finish_delegate_task(
                    context.workspace,
                    context.action,
                    context.subagent_id,
                    ok=False,
                    summary="",
                    iterations=child_iteration,
                    tool_calls=tool_calls_used,
                    message=idle_halt,
                    logger=context.logger,
                )
            if idle_feedback is not None:
                context.messages.append(ChatMessage(role="user", content=idle_feedback))
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
                _checkpoint(context)
                continue
            return _finish_text_response(context, child_iteration, tool_calls_used, assistant_content)

        tool_results: list[ContentBlock] = []
        for block in tool_calls:
            if _cancellation_requested(context):
                return _finish_cancelled(context, child_iteration, tool_calls_used)
            tool_id = str(block.get("id") or "")
            tool_name = str(block.get("name") or "")
            tool_input = block.get("input") or {}
            tool_calls_used.append(tool_name)
            record_delegate_tool_call(
                context.workspace,
                subagent_id=context.subagent_id,
                parent_iteration=context.parent_iteration,
                iteration=child_iteration,
                tool_id=tool_id,
                tool_name=tool_name,
                tool_input=tool_input,
            )
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
                disallowed_tool_names=context.disallowed_tool_names,
                hooks=context.hooks,
                permissions=context.permissions,
                special_action_handler=lambda action: context.nested_runtime.execute(
                    action, child_iteration, tool_id
                ),
                tool_id=tool_id,
                coordination_tool_names=(
                    context.nested_runtime.coordination_tool_names
                ),
                hook_model_runtime=context.hook_model_runtime,
                auto_mode_runtime=context.auto_mode_runtime,
                teammate_name=context.nested_runtime.team_member_name,
            )
            auto_checkpoint_attempted = execution.auto_checkpoint_attempted
            if execution.finish_action is not None:
                stop_feedback = context.lifecycle.stop_feedback(
                    execution.finish_action.message,
                    child_iteration,
                )
                if stop_feedback is not None:
                    feedback_observation = ToolErrorObservation(
                        kind="tool_error",
                        tool=tool_name,
                        message=stop_feedback,
                    )
                    tool_results.append(
                        record_subagent_tool_observation(
                            context.workspace,
                            subagent_id=context.subagent_id,
                            parent_iteration=context.parent_iteration,
                            iteration=child_iteration,
                            tool_id=tool_id,
                            tool_name=tool_name,
                            observation=feedback_observation,
                        )
                    )
                    break
                if context.inbox is not None and context.inbox.append_to(context.messages, final=True):
                    feedback_observation = ToolErrorObservation(
                        kind="tool_error",
                        tool=tool_name,
                        message="Completion deferred because the parent agent sent follow-up direction.",
                    )
                    tool_results.append(
                        record_subagent_tool_observation(
                            context.workspace,
                            subagent_id=context.subagent_id,
                            parent_iteration=context.parent_iteration,
                            iteration=child_iteration,
                            tool_id=tool_id,
                            tool_name=tool_name,
                            observation=feedback_observation,
                        )
                    )
                    break
                idle_feedback, idle_halt = context.lifecycle.teammate_idle_feedback(
                    child_iteration
                )
                if idle_feedback is not None or idle_halt is not None:
                    feedback_observation = ToolErrorObservation(
                        kind="tool_error",
                        tool=tool_name,
                        message=idle_feedback or idle_halt or "Teammate idle blocked.",
                    )
                    tool_results.append(
                        record_subagent_tool_observation(
                            context.workspace,
                            subagent_id=context.subagent_id,
                            parent_iteration=context.parent_iteration,
                            iteration=child_iteration,
                            tool_id=tool_id,
                            tool_name=tool_name,
                            observation=feedback_observation,
                        )
                    )
                    if idle_halt is not None:
                        context.messages.append(ChatMessage(role="user", content=tool_results))
                        return finish_delegate_task(
                            context.workspace,
                            context.action,
                            context.subagent_id,
                            ok=False,
                            summary="",
                            iterations=child_iteration,
                            tool_calls=tool_calls_used,
                            message=idle_halt,
                            logger=context.logger,
                        )
                    break
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
                        instruction_hook_runner=lambda instruction_context: run_instruction_loaded_hooks(
                            context.workspace,
                            context.hooks,
                            instruction_context,
                            iteration=child_iteration,
                            command_timeout_ms=context.command_timeout_ms,
                            logger=context.logger,
                            approval_handler=context.approval_handler,
                            approval_policy=context.approval_policy,
                            execute_action_safely_func=execute_action_safely,
                            permissions=context.permissions,
                            hook_model_runtime=context.hook_model_runtime,
                        ),
                    )
                )
            if execution.halt_turn_message is not None:
                if context.inbox is not None:
                    context.inbox.close()
                return finish_delegate_task(
                    context.workspace,
                    context.action,
                    context.subagent_id,
                    ok=False,
                    summary="",
                    iterations=child_iteration,
                    tool_calls=tool_calls_used,
                    message=execution.halt_turn_message,
                    logger=context.logger,
                )

        batch = run_post_tool_batch_hooks(
            context.workspace,
            tool_calls[: len(tool_results)],
            tool_results,
            iteration=child_iteration,
            command_timeout_ms=context.command_timeout_ms,
            logger=context.logger,
            approval_handler=context.approval_handler,
            approval_policy=context.approval_policy,
            execute_action_safely_func=execute_action_safely,
            hooks=context.hooks,
            permissions=context.permissions,
            hook_model_runtime=context.hook_model_runtime,
        )
        append_batch_context(tool_results, batch)
        if batch.blocking_message is not None:
            context.messages.append(ChatMessage(role="user", content=tool_results))
            if context.inbox is not None:
                context.inbox.close()
            return finish_delegate_task(
                context.workspace,
                context.action,
                context.subagent_id,
                ok=False,
                summary="",
                iterations=child_iteration,
                tool_calls=tool_calls_used,
                message=batch.blocking_message,
                logger=context.logger,
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
        _checkpoint(context)

    if context.inbox is not None:
        context.inbox.close()
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


def _checkpoint(context: DelegateLoopContext) -> None:
    if context.transcript_checkpoint is not None:
        context.transcript_checkpoint(context.messages)


def _text_stop_feedback(
    context: DelegateLoopContext,
    child_iteration: int,
    assistant_content: list[ContentBlock],
) -> str | None:
    summary = content_blocks_to_text(assistant_content).strip()
    if not summary:
        return None
    return context.lifecycle.stop_feedback(summary, child_iteration)


def _finish_cancelled(
    context: DelegateLoopContext,
    iterations: int,
    tool_calls_used: list[str],
) -> DelegateTaskObservation:
    if context.inbox is not None:
        context.inbox.close()
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
