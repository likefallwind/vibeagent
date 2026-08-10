from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any

from .agent_background_notifications import inject_background_delegate_notifications
from .agent_conversation import conversation_for_next_prompt
from .agent_message_flow import (
    append_tool_results_and_compact,
    compact_agent_context_if_needed,
    recover_agent_context_limit,
)
from .agent_observation_utils import observation_failed
from .agent_lifecycle_runtime import AgentLifecycleRuntime
from .agent_model_turn import handle_no_tool_call_response, record_model_turn
from .agent_multimodal import strip_consumed_tool_images
from .agent_monitor_notifications import inject_monitor_notifications
from .agent_parallel_execution import execute_parallel_tool_call_batch
from .agent_peer_notifications import inject_peer_notifications
from .agent_plan_mode import PlanModeRuntime, approval_handler_after_plan
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
from .session_conversation import checkpoint_session_conversation
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
from .workspace_core import RunWorkspace


@dataclass(frozen=True)
class AgentLoopRuntime:
    complete_with_retries: Callable[..., tuple[Any | None, str | None]]
    execute_action: Callable[..., Observation]
    execute_action_safely: Callable[..., Observation]
    completion_blocked_feedback_if_needed: Callable[..., str | None]
    finish_agent_run: Callable[..., AgentResult]
    should_auto_checkpoint_before_action: Callable[..., bool]
    create_auto_checkpoint_before_action: Callable[..., Observation | None]
    create_auto_checkpoint_for_prompt: Callable[..., Observation | None]
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
    prompt_checkpoint_steps: list[TaskStep] = []
    prompt_checkpoint = runtime.create_auto_checkpoint_for_prompt(
        current_workspace,
        task,
        prompt_checkpoint_steps,
        command_timeout_ms,
        logger,
    )
    pending_prompt_checkpoint = (
        prompt_checkpoint
        if prompt_checkpoint is not None and not observation_failed(prompt_checkpoint)
        else None
    )
    auto_checkpoint_attempted = False
    plan_mode = PlanModeRuntime.create(
        approval_policy,
        locked=setup.approval_policy_locked,
    )
    current_approval_handler = approval_handler

    def tool_call_allowed(name: str, action: object) -> bool:
        if (
            setup.approval_policy_locked
            and getattr(action, "type", None) == "exit_plan_mode"
        ):
            return False
        return setup.main_profile.allows_tool_call(name, action)

    def checkpoint_conversation() -> None:
        checkpoint_session_conversation(current_workspace, messages, task)

    def finish_with_conversation(
        workspace: RunWorkspace,
        success: bool,
        message: str,
        iterations: int,
        finish_observations: list[Observation],
        finish_steps: list[TaskStep],
        finish_plan: list[PlanItem],
        timeout_ms: int,
        finish_logger: AgentLogger | None,
    ) -> AgentResult:
        checkpoint_session_conversation(workspace, messages, task)
        return replace(
            runtime.finish_agent_run(
                workspace,
                success=success,
                message=message,
                iterations=iterations,
                observations=finish_observations,
                steps=finish_steps,
                plan=finish_plan,
                command_timeout_ms=timeout_ms,
                logger=finish_logger,
            ),
            approval_policy=plan_mode.current_policy,
            conversation=conversation_for_next_prompt(messages, task),
        )

    def finish_run(success: bool, message: str, iterations: int) -> AgentResult:
        return finish_with_conversation(
            current_workspace,
            success,
            message,
            iterations,
            observations,
            steps,
            plan,
            command_timeout_ms,
            logger,
        )

    def create_checkpoint_before_action(
        workspace: RunWorkspace,
        action: object,
        action_steps: list[TaskStep],
        iteration: int,
        timeout_ms: int,
        action_logger: AgentLogger | None,
    ) -> Observation | None:
        nonlocal pending_prompt_checkpoint
        if pending_prompt_checkpoint is not None:
            checkpoint = pending_prompt_checkpoint
            pending_prompt_checkpoint = None
            return checkpoint
        return runtime.create_auto_checkpoint_before_action(
            workspace,
            action,
            action_steps,
            iteration,
            timeout_ms,
            action_logger,
        )
    lifecycle = AgentLifecycleRuntime(
        hooks=project_hooks,
        permissions=project_permissions,
        command_timeout_ms=command_timeout_ms,
        logger=logger,
        approval_handler=current_approval_handler,
        approval_policy=plan_mode.current_policy,
        execute_action_safely=runtime.execute_action_safely,
    )
    startup_block = lifecycle.start(
        current_workspace, messages, task, resumed=bool(prior_context)
    )
    if startup_block is not None:
        return finish_run(False, startup_block, 0)
    checkpoint_conversation()
    plugin_monitors = AgentPluginMonitorController.create(
        plugin_monitor_runtime,
        current_workspace,
        project_permissions,
        current_approval_handler,
        plan_mode.current_policy,
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
        inject_monitor_notifications(
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
            approval_policy=plan_mode.current_policy,
            system_prompt=system_prompt,
            append_system_prompt=append_system_prompt,
        )
        checkpoint_conversation()

        response, model_error_message = runtime.complete_with_retries(
            client,
            messages,
            tools=agent_tool_definitions(
                active_tool_names,
                plan_mode.current_policy,
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
                approval_policy=plan_mode.current_policy,
                system_prompt=system_prompt,
                append_system_prompt=append_system_prompt,
            ),
        )
        if response is None:
            return finish_run(False, model_error_message or "Model request failed.", iteration)
        strip_consumed_tool_images(messages)
        model_turn = record_model_turn(current_workspace, messages, response, iteration)
        assistant_content = model_turn.assistant_content
        tool_calls = model_turn.tool_calls
        if not tool_calls:
            if inject_monitor_notifications(
                current_workspace, messages, iteration=iteration, logger=logger
            ):
                checkpoint_conversation()
                continue
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
                finish_agent_run_func=finish_with_conversation,
                stop_feedback_if_needed_func=stop_feedback_if_needed,
            )
            if no_tool_result.should_continue:
                checkpoint_conversation()
                continue
            return no_tool_result.result

        activate_tools_for_run(
            current_workspace,
            active_tool_names,
            [str(block.get("name") or "") for block in tool_calls],
            iteration,
            source="model_call",
            approval_policy=plan_mode.current_policy,
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
                approval_policy=plan_mode.current_policy,
                tool_call_allowed=tool_call_allowed,
                excluded_tool_names=setup.main_profile.disallowed_tool_names,
                allowed_tool_names=setup.main_profile.allowed_tool_names,
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
                plan_mode.current_policy,
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
                approval_policy=plan_mode.current_policy,
                system_prompt=system_prompt,
                append_system_prompt=append_system_prompt,
            )
            checkpoint_conversation()
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
                approval_handler=current_approval_handler,
                approval_policy=plan_mode.current_policy,
                user_input_handler=user_input_handler,
                hooks=project_hooks,
                permissions=project_permissions,
                auto_checkpoint_attempted=auto_checkpoint_attempted,
                execute_action_safely_func=runtime.execute_action_safely,
                should_auto_checkpoint_before_action_func=runtime.should_auto_checkpoint_before_action,
                create_auto_checkpoint_before_action_func=create_checkpoint_before_action,
                tool_call_allowed=tool_call_allowed,
                excluded_tool_names=setup.main_profile.disallowed_tool_names,
                allowed_tool_names=setup.main_profile.allowed_tool_names,
                tool_ceiling_names=setup.tool_ceiling_names,
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
            if plan_mode.apply(current_workspace, observation, iteration=iteration):
                current_approval_handler = approval_handler_after_plan(
                    approval_handler,
                    plan_mode.current_policy,
                )
                lifecycle.approval_policy = plan_mode.current_policy
                lifecycle.approval_handler = current_approval_handler
                active_tool_names.add(
                    "ExitPlanMode"
                    if plan_mode.current_policy == "plan"
                    else "EnterPlanMode"
                )
                if peer_runtime is not None:
                    peer_runtime.update_approval_policy(plan_mode.current_policy)
                plugin_monitors = AgentPluginMonitorController.create(
                    plugin_monitor_runtime,
                    current_workspace,
                    project_permissions,
                    current_approval_handler,
                    plan_mode.current_policy,
                    logger,
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
                return finish_run(True, observation.message, iteration)

        if blocked_completion_feedback is not None:
            messages.append(ChatMessage(role="user", content=tool_results))
            messages.append(
                ChatMessage(role="user", content=blocked_completion_feedback)
            )
            checkpoint_conversation()
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
            approval_policy=plan_mode.current_policy,
            system_prompt=system_prompt,
            append_system_prompt=append_system_prompt,
        )
        checkpoint_conversation()

    return finish_run(False, f"Reached iteration limit ({max_iterations}) before finish.", max_iterations)
