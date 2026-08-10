from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .agent_background_notifications import inject_background_delegate_notifications
from .agent_message_flow import (
    append_tool_results_and_compact,
    compact_agent_context_if_needed,
    recover_agent_context_limit,
)
from .agent_lifecycle_runtime import AgentLifecycleRuntime
from .agent_model_turn import handle_no_tool_call_response, record_model_turn
from .agent_multimodal import strip_consumed_tool_images
from .agent_parallel_execution import execute_parallel_tool_call_batch
from .agent_peer_notifications import inject_peer_notifications
from .agent_plugin_monitors import AgentPluginMonitorController
from .peer_runtime import PeerSessionRuntime
from .plugin_monitor_runtime import PluginMonitorRuntime
from .agent_scheduled_notifications import inject_scheduled_task_notifications
from .agent_result import AgentResult
from .agent_run_setup import AgentRunSetup
from .agent_sequential_execution import execute_sequential_tool_call
from .agent_tool_registry import (
    activate_tools_for_run,
    activate_tools_from_observations,
    agent_tool_definitions,
)
from .agent_workspace_transition import apply_workspace_transition
from .session_tasks import read_task_plan
from .types import (
    AgentLogger,
    ApprovalHandler,
    ApprovalPolicy,
    ChatClient,
    ChatMessage,
    ContentBlock,
    Observation,
    PlanItem,
    TaskStep,
    UserInputHandler,
)


@dataclass(frozen=True)
class AgentLoopRuntime:
    complete_with_retries: Callable[..., tuple[Any | None, str | None]]
    execute_action: Callable[..., Observation]
    execute_action_safely: Callable[..., Observation]
    completion_blocked_feedback_if_needed: Callable[..., str | None]
    finish_agent_run: Callable[..., AgentResult]
    should_auto_checkpoint_before_action: Callable[..., bool]
    create_auto_checkpoint_before_action: Callable[..., Observation | None]
    sleep: Callable[[float], None]


def run_agent_loop(
    task: str,
    client: ChatClient,
    setup: AgentRunSetup,
    *,
    max_iterations: int,
    command_timeout_ms: int,
    max_output_tokens: int,
    model_retries: int,
    model_retry_delay_ms: int,
    model_timeout_ms: int,
    logger: AgentLogger | None,
    approval_handler: ApprovalHandler | None,
    user_input_handler: UserInputHandler | None,
    prior_context: str | None,
    approval_policy: ApprovalPolicy,
    system_prompt: str | None,
    append_system_prompt: str | None,
    runtime: AgentLoopRuntime,
    peer_runtime: PeerSessionRuntime | None = None,
    plugin_monitor_runtime: PluginMonitorRuntime | None = None,
) -> AgentResult:
    observations: list[Observation] = []
    steps: list[TaskStep] = []
    plan: list[PlanItem] = read_task_plan(setup.workspace)
    current_workspace = setup.workspace
    messages = setup.messages
    active_tool_names = setup.active_tool_names
    project_hooks = setup.project_hooks
    project_permissions = setup.project_permissions
    auto_checkpoint_attempted = False
    lifecycle = AgentLifecycleRuntime(
        hooks=project_hooks,
        permissions=project_permissions,
        command_timeout_ms=command_timeout_ms,
        logger=logger,
        approval_handler=approval_handler,
        approval_policy=approval_policy,
        execute_action_safely=runtime.execute_action_safely,
    )
    startup_block = lifecycle.start(
        current_workspace, messages, task, resumed=bool(prior_context)
    )
    if startup_block is not None:
        return runtime.finish_agent_run(
            current_workspace,
            success=False,
            message=startup_block,
            iterations=0,
            observations=observations,
            steps=steps,
            plan=plan,
            command_timeout_ms=command_timeout_ms,
            logger=logger,
        )
    plugin_monitors = AgentPluginMonitorController.create(
        plugin_monitor_runtime,
        current_workspace,
        project_permissions,
        approval_handler,
        approval_policy,
        logger,
    )
    plugin_monitors.start()

    def stop_feedback_if_needed(message: str, iteration: int) -> str | None:
        return lifecycle.stop_feedback_if_needed(current_workspace, message, iteration)

    for iteration in range(1, max_iterations + 1):
        # Tool loop: provider-neutral tool_call blocks -> local execution -> tool_result blocks.
        if logger:
            logger("thinking", f"iteration {iteration}/{max_iterations}")

        inject_background_delegate_notifications(
            current_workspace,
            messages,
            observations,
            iteration=iteration,
            logger=logger,
        )
        plugin_monitors.inject(
            current_workspace, messages, iteration=iteration, logger=logger
        )
        inject_scheduled_task_notifications(
            current_workspace,
            messages,
            iteration=iteration,
            logger=logger,
        )
        inject_peer_notifications(
            peer_runtime,
            current_workspace,
            messages,
            iteration=iteration,
            logger=logger,
        )

        messages = compact_agent_context_if_needed(
            task=task,
            workspace=current_workspace,
            messages=messages,
            observations=observations,
            plan=plan,
            original_prior_context=prior_context,
            iteration=iteration,
            approval_policy=approval_policy,
            system_prompt=system_prompt,
            append_system_prompt=append_system_prompt,
        )

        response, model_error_message = runtime.complete_with_retries(
            client,
            messages,
            tools=agent_tool_definitions(
                active_tool_names,
                approval_policy,
                excluded_names=setup.main_profile.disallowed_tool_names,
                allowed_names=setup.main_profile.allowed_tool_names,
            ),
            max_output_tokens=max_output_tokens,
            model_retries=model_retries,
            model_retry_delay_ms=model_retry_delay_ms,
            model_timeout_ms=model_timeout_ms,
            iteration=iteration,
            session_dir=current_workspace.session_dir,
            logger=logger,
            sleep=runtime.sleep,
            recover_context=lambda: recover_agent_context_limit(
                task=task,
                workspace=current_workspace,
                messages=messages,
                observations=observations,
                plan=plan,
                original_prior_context=prior_context,
                iteration=iteration,
                approval_policy=approval_policy,
                system_prompt=system_prompt,
                append_system_prompt=append_system_prompt,
            ),
        )
        if response is None:
            return runtime.finish_agent_run(
                current_workspace,
                success=False,
                message=model_error_message or "Model request failed.",
                iterations=iteration,
                observations=observations,
                steps=steps,
                plan=plan,
                command_timeout_ms=command_timeout_ms,
                logger=logger,
            )
        strip_consumed_tool_images(messages)
        model_turn = record_model_turn(current_workspace, messages, response, iteration)
        assistant_content = model_turn.assistant_content
        tool_calls = model_turn.tool_calls
        if not tool_calls:
            no_tool_result = handle_no_tool_call_response(
                current_workspace,
                messages,
                assistant_content,
                iteration=iteration,
                max_iterations=max_iterations,
                observations=observations,
                steps=steps,
                plan=plan,
                command_timeout_ms=command_timeout_ms,
                logger=logger,
                completion_blocked_feedback_if_needed_func=runtime.completion_blocked_feedback_if_needed,
                finish_agent_run_func=runtime.finish_agent_run,
                stop_feedback_if_needed_func=stop_feedback_if_needed,
            )
            if no_tool_result.should_continue:
                continue
            return no_tool_result.result

        activate_tools_for_run(
            current_workspace,
            active_tool_names,
            [str(block.get("name") or "") for block in tool_calls],
            iteration,
            source="model_call",
            approval_policy=approval_policy,
            excluded_names=setup.main_profile.disallowed_tool_names,
            allowed_names=setup.main_profile.allowed_tool_names,
        )
        observation_start = len(observations)
        parallel_batch_result = (
            None
            if project_hooks.requires_sequential_tools or project_permissions.enabled
            else execute_parallel_tool_call_batch(
                current_workspace,
                tool_calls,
                observations,
                steps,
                iteration,
                command_timeout_ms,
                logger,
                execute=runtime.execute_action,
                approval_policy=approval_policy,
                tool_call_allowed=setup.main_profile.allows_tool_call,
            )
        )
        tool_results: list[ContentBlock] = []
        handled_tool_calls = 0
        if parallel_batch_result is not None:
            tool_results.extend(parallel_batch_result.tool_results)
            handled_tool_calls = parallel_batch_result.handled_count
            activate_tools_from_observations(
                current_workspace,
                active_tool_names,
                observations[observation_start:],
                iteration,
                approval_policy,
                excluded_names=setup.main_profile.disallowed_tool_names,
                allowed_names=setup.main_profile.allowed_tool_names,
            )
            plugin_monitors.observe_many(
                observations[observation_start:], iteration=iteration
            )
        if handled_tool_calls == len(tool_calls):
            messages = append_tool_results_and_compact(
                task=task,
                workspace=current_workspace,
                messages=messages,
                tool_results=tool_results,
                observations=observations,
                plan=plan,
                original_prior_context=prior_context,
                iteration=iteration,
                approval_policy=approval_policy,
                system_prompt=system_prompt,
                append_system_prompt=append_system_prompt,
            )
            continue

        blocked_completion_feedback: str | None = None
        for block in tool_calls[handled_tool_calls:]:
            sequential = execute_sequential_tool_call(
                current_workspace,
                block,
                client,
                observations=observations,
                steps=steps,
                plan=plan,
                active_tool_names=active_tool_names,
                iteration=iteration,
                max_output_tokens=max_output_tokens,
                model_retries=model_retries,
                model_retry_delay_ms=model_retry_delay_ms,
                model_timeout_ms=model_timeout_ms,
                command_timeout_ms=command_timeout_ms,
                logger=logger,
                approval_handler=approval_handler,
                approval_policy=approval_policy,
                user_input_handler=user_input_handler,
                hooks=project_hooks,
                permissions=project_permissions,
                auto_checkpoint_attempted=auto_checkpoint_attempted,
                execute_action_safely_func=runtime.execute_action_safely,
                should_auto_checkpoint_before_action_func=runtime.should_auto_checkpoint_before_action,
                create_auto_checkpoint_before_action_func=runtime.create_auto_checkpoint_before_action,
                tool_call_allowed=setup.main_profile.allows_tool_call,
                excluded_tool_names=setup.main_profile.disallowed_tool_names,
                allowed_tool_names=setup.main_profile.allowed_tool_names,
            )
            tool_results.append(sequential.tool_result)
            observation = sequential.observation
            plugin_monitors.observe(observation, iteration=iteration)
            plan = sequential.plan
            auto_checkpoint_attempted = sequential.auto_checkpoint_attempted
            current_workspace = apply_workspace_transition(
                current_workspace,
                observation,
                iteration=iteration,
            )

            if observation.kind == "finish":
                blocked_completion_feedback = (
                    runtime.completion_blocked_feedback_if_needed(
                        current_workspace,
                        success=True,
                        message=observation.message,
                        iteration=iteration,
                        max_iterations=max_iterations,
                        observations=observations,
                        plan=plan,
                        command_timeout_ms=command_timeout_ms,
                        logger=logger,
                    )
                )
                if blocked_completion_feedback is not None:
                    break
                blocked_completion_feedback = stop_feedback_if_needed(
                    observation.message, iteration
                )
                if blocked_completion_feedback is not None:
                    break
                if logger:
                    logger("finished", observation.message)
                return runtime.finish_agent_run(
                    current_workspace,
                    success=True,
                    message=observation.message,
                    iterations=iteration,
                    observations=observations,
                    steps=steps,
                    plan=plan,
                    command_timeout_ms=command_timeout_ms,
                    logger=logger,
                )

        if blocked_completion_feedback is not None:
            messages.append(ChatMessage(role="user", content=tool_results))
            messages.append(
                ChatMessage(role="user", content=blocked_completion_feedback)
            )
            continue

        messages = append_tool_results_and_compact(
            task=task,
            workspace=current_workspace,
            messages=messages,
            tool_results=tool_results,
            observations=observations,
            plan=plan,
            original_prior_context=prior_context,
            iteration=iteration,
            approval_policy=approval_policy,
            system_prompt=system_prompt,
            append_system_prompt=append_system_prompt,
        )

    return runtime.finish_agent_run(
        current_workspace,
        success=False,
        message=f"Reached iteration limit ({max_iterations}) before finish.",
        iterations=max_iterations,
        observations=observations,
        steps=steps,
        plan=plan,
        command_timeout_ms=command_timeout_ms,
        logger=logger,
    )
