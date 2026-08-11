from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any
from uuid import uuid4

from .auto_mode import AutoModeRuntime
from .agent_async_hook_notifications import inject_async_hook_notifications
from .agent_hook_prompt import HookModelRuntime
from .agent_background_notifications import inject_background_delegate_notifications
from .agent_conversation import conversation_for_next_prompt
from .agent_message_flow import (
    append_tool_results_and_compact,
    compact_agent_context_if_needed,
    recover_agent_context_limit,
)
from .agent_message_display import build_message_display_finish
from .agent_observation_utils import observation_failed
from .agent_lifecycle_runtime import AgentLifecycleRuntime
from .agent_model_turn import handle_no_tool_call_response, record_model_turn
from .agent_multimodal import strip_consumed_tool_images
from .agent_monitor_notifications import inject_monitor_notifications
from .agent_notification_hooks import (
    permission_notification_message,
    wrap_approval_handler_with_notification,
)
from .agent_parallel_execution import execute_parallel_tool_call_batch
from .agent_peer_notifications import inject_peer_notifications
from .agent_post_tool_batch_hooks import append_batch_context, run_post_tool_batch_hooks
from .agent_plan_mode import PlanModeRuntime, approval_handler_after_plan
from .agent_plugin_monitors import AgentPluginMonitorController
from .peer_runtime import PeerSessionRuntime
from .prompt_expansion import prompt_expansion_from_task_metadata
from .redaction import redact_sensitive_text
from .plugin_monitor_runtime import PluginMonitorRuntime
from .agent_scheduled_notifications import inject_scheduled_task_notifications
from .agent_result import AgentResult
from .agent_run_setup import AgentRunSetup
from .agent_sequential_execution import execute_sequential_tool_call
from .agent_sequential_execution import SequentialToolCallResult
from .agent_runtime_utils import append_session_event, content_blocks_to_text
from .agent_deferred_loop import (
    persist_deferred_tool_batch,
    resume_deferred_tool_batch,
)
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
from .deferred_tool_state import DeferredToolState
from .file_changed_hooks import FileChangedHookRuntime
from .config_change_hooks import ConfigChangeHookRuntime


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
    deferred_tool_state: DeferredToolState | None = None,
    defer_tool_calls: bool = False,
    setup_trigger: str | None = None,
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
    hook_system_messages: list[str] = []
    turn_id = str(uuid4())
    hook_model_runtime = HookModelRuntime(
        client=client,
        complete_with_retries=runtime.complete_with_retries,
        max_output_tokens=max_output_tokens,
        model_retries=model_retries,
        model_retry_delay_ms=model_retry_delay_ms,
        logger=logger,
    )
    auto_mode_runtime = AutoModeRuntime(
        model=hook_model_runtime,
        messages_provider=lambda: messages,
        interactive=approval_handler is not None and not defer_tool_calls,
    )

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
        *,
        stop_reason: str | None = None,
        deferred_tool_use: dict[str, object] | None = None,
        is_error: bool = False,
        display_message: str | None = None,
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
                stop_reason=stop_reason,
                deferred_tool_use=deferred_tool_use,
                is_error=is_error,
            ),
            approval_policy=plan_mode.current_policy,
            hook_system_messages=list(hook_system_messages),
            conversation=conversation_for_next_prompt(messages, task),
            display_message=display_message,
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

    def finish_deferred_run(
        state: DeferredToolState,
        iterations: int,
        *,
        unavailable: bool = False,
    ) -> AgentResult:
        pending = state.pending_tool_use
        stop_reason = "tool_deferred_unavailable" if unavailable else "tool_deferred"
        message = (
            f"Deferred tool is no longer available: {pending['name']}."
            if unavailable
            else f"Tool call deferred: {pending['name']}."
        )
        return finish_with_conversation(
            current_workspace,
            not unavailable,
            message,
            iterations,
            observations,
            steps,
            plan,
            command_timeout_ms,
            logger,
            stop_reason=stop_reason,
            deferred_tool_use=pending,
            is_error=unavailable,
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
        hook_model_runtime=hook_model_runtime,
    )

    def approval_handler_with_notifications(iteration: int):
        if plan_mode.current_policy != "ask":
            return current_approval_handler

        def notify(request):
            return lifecycle.notify(
                current_workspace,
                "permission_prompt",
                permission_notification_message(request),
                title="Permission needed",
                iteration=iteration,
            )

        def notification_error(error: Exception) -> None:
            append_session_event(
                current_workspace.session_dir,
                "notification_hook_error",
                {
                    "iteration": iteration,
                    "message": redact_sensitive_text(str(error))[:2_000],
                },
            )

        return wrap_approval_handler_with_notification(
            current_approval_handler,
            notify,
            hook_system_messages,
            on_error=notification_error,
        )

    def run_post_batch(
        calls: list[ContentBlock], results: list[ContentBlock], batch_iteration: int
    ):
        batch = run_post_tool_batch_hooks(
            current_workspace,
            calls,
            results,
            iteration=batch_iteration,
            command_timeout_ms=command_timeout_ms,
            logger=logger,
            approval_handler=current_approval_handler,
            approval_policy=plan_mode.current_policy,
            execute_action_safely_func=runtime.execute_action_safely,
            hooks=project_hooks,
            permissions=project_permissions,
            hook_model_runtime=hook_model_runtime,
        )
        append_batch_context(results, batch)
        return batch

    def compact_hook_runner(iteration: int):
        return lambda phase, trigger, summary: lifecycle.compact(
            current_workspace,
            phase,
            trigger,
            summary,
            iteration=iteration,
        )

    config_change_runtime = ConfigChangeHookRuntime(current_workspace, lifecycle)
    startup_block = lifecycle.start(
        current_workspace,
        messages,
        task,
        resumed=bool(prior_context),
        setup_trigger=setup_trigger,
        prompt_expansion=prompt_expansion_from_task_metadata(setup.task_metadata),
    )
    if startup_block is not None:
        return finish_run(False, startup_block, 0)
    file_changed_runtime = FileChangedHookRuntime(
        current_workspace,
        project_hooks,
        lifecycle,
    )
    initial_config_changes = config_change_runtime.poll(iteration=0)
    hook_system_messages.extend(initial_config_changes.system_messages)
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

    def poll_runtime_changes(iteration: int) -> None:
        config_changes = config_change_runtime.poll(
            workspace=current_workspace,
            iteration=iteration,
        )
        hook_system_messages.extend(config_changes.system_messages)
        changed = file_changed_runtime.poll(
            workspace=current_workspace,
            iteration=iteration,
        )
        hook_system_messages.extend(changed.system_messages)

    def apply_sequential_runtime_state(
        sequential: SequentialToolCallResult,
        iteration: int,
    ) -> Observation:
        nonlocal plan, auto_checkpoint_attempted, current_workspace
        nonlocal project_permissions
        nonlocal current_approval_handler, plugin_monitors
        observation = sequential.observation
        permission_application = sequential.permission_application
        permission_state_changed = permission_application is not None
        if permission_application is not None:
            current_workspace = permission_application.workspace
            project_permissions = permission_application.permissions
            policy_changed = plan_mode.apply_permission_policy(
                current_workspace,
                permission_application.approval_policy,
                iteration=iteration,
            )
            lifecycle.permissions = project_permissions
            if policy_changed:
                current_approval_handler = approval_handler_after_plan(
                    approval_handler,
                    plan_mode.current_policy,
                )
                lifecycle.approval_policy = plan_mode.current_policy
                lifecycle.approval_handler = current_approval_handler
                if peer_runtime is not None:
                    peer_runtime.update_approval_policy(plan_mode.current_policy)
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
        elif permission_state_changed:
            plugin_monitors = AgentPluginMonitorController.create(
                plugin_monitor_runtime,
                current_workspace,
                project_permissions,
                current_approval_handler,
                plan_mode.current_policy,
                logger,
            )
        return observation

    def resume_deferred_batch(state: DeferredToolState) -> AgentResult | None:
        nonlocal messages
        deferred_workspace = current_workspace
        tool_calls = list(state.tool_calls)
        activate_tools_for_run(
            current_workspace,
            active_tool_names,
            [str(block.get("name") or "") for block in tool_calls],
            0,
            source="deferred_resume",
            approval_policy=plan_mode.current_policy,
            excluded_names=setup.main_profile.disallowed_tool_names,
            allowed_names=setup.main_profile.allowed_tool_names,
        )
        available_names = {
            str(tool.get("name") or "")
            for tool in agent_tool_definitions(
                active_tool_names,
                plan_mode.current_policy,
                excluded_names=setup.main_profile.disallowed_tool_names,
                allowed_names=setup.main_profile.allowed_tool_names,
            )
        }
        def execute_block(block: ContentBlock) -> SequentialToolCallResult:
            return execute_sequential_tool_call(
                current_workspace,
                block,
                client,
                observations=observations,
                steps=steps,
                plan=plan,
                active_tool_names=active_tool_names,
                iteration=0,
                max_output_tokens=max_output_tokens,
                model_retries=model_retries,
                model_retry_delay_ms=model_retry_delay_ms,
                model_timeout_ms=model_timeout_ms,
                command_timeout_ms=command_timeout_ms,
                logger=logger,
                approval_handler=approval_handler_with_notifications(0),
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
                defer_tool_calls=defer_tool_calls,
                hook_model_runtime=hook_model_runtime,
                auto_mode_runtime=auto_mode_runtime,
            )

        def on_resume(pending: dict[str, object], completed_results: int) -> None:
            messages.append(
                ChatMessage(role="assistant", content=list(state.assistant_content))
            )
            append_session_event(
                current_workspace.session_dir,
                "tool_deferred_resumed",
                {"tool": pending, "completed_results": completed_results},
            )

        outcome = resume_deferred_tool_batch(
            deferred_workspace,
            state,
            available_names,
            execute_block=execute_block,
            apply_result=lambda result: apply_sequential_runtime_state(result, 0),
            on_resume=on_resume,
            finish_deferred=lambda next_state, unavailable: finish_deferred_run(
                next_state, 0, unavailable=unavailable
            ),
            finish_action=lambda observation: finish_run(
                True, observation.message, 0
            ),
        )
        if outcome.result is not None:
            return outcome.result
        resumed_results = list(outcome.tool_results)
        resumed_batch = run_post_batch(list(state.tool_calls), resumed_results, 0)
        if resumed_batch.blocking_message is not None:
            messages.append(ChatMessage(role="user", content=resumed_results))
            return finish_with_conversation(
                current_workspace, False, resumed_batch.blocking_message, 0,
                observations, steps, plan, command_timeout_ms, logger,
                stop_reason="hook_blocked",
            )
        messages = append_tool_results_and_compact(
            task=task,
            workspace=current_workspace,
            messages=messages,
            tool_results=resumed_results,
            observations=observations,
            plan=plan,
            original_prior_context=prior_context,
            iteration=0,
            approval_policy=plan_mode.current_policy,
            system_prompt=system_prompt,
            append_system_prompt=append_system_prompt,
            compact_hook_runner=compact_hook_runner(0),
        )
        checkpoint_conversation()
        return None

    if deferred_tool_state is not None:
        deferred_result = resume_deferred_batch(deferred_tool_state)
        if deferred_result is not None:
            return deferred_result

    for iteration in range(1, max_iterations + 1):
        # Tool loop: provider-neutral tool_call blocks -> local execution -> tool_result blocks.
        if logger:
            logger("thinking", f"iteration {iteration}/{max_iterations}")

        poll_runtime_changes(iteration)

        inject_background_delegate_notifications(
            current_workspace,
            messages,
            observations,
            iteration=iteration,
            logger=logger,
        )
        inject_async_hook_notifications(
            current_workspace,
            messages,
            hook_system_messages,
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
            compact_hook_runner=compact_hook_runner(iteration),
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
                compact_hook_runner=compact_hook_runner(iteration),
            ),
        )
        if response is None:
            failure_message = model_error_message or "Model request failed."
            lifecycle.stop_failure(current_workspace, failure_message, iteration)
            return finish_run(False, failure_message, iteration)
        strip_consumed_tool_images(messages)
        model_turn = record_model_turn(current_workspace, messages, response, iteration)
        poll_runtime_changes(iteration)
        assistant_content = model_turn.assistant_content
        tool_calls = model_turn.tool_calls
        assistant_text = content_blocks_to_text(assistant_content)
        if not tool_calls:
            late_async_hooks = inject_async_hook_notifications(
                current_workspace,
                messages,
                hook_system_messages,
                iteration=iteration,
                logger=logger,
            )
            late_monitors = inject_monitor_notifications(
                current_workspace, messages, iteration=iteration, logger=logger
            )
            if late_async_hooks or late_monitors:
                checkpoint_conversation()
                continue
            finish_model_message = build_message_display_finish(
                lifecycle,
                finish_with_conversation,
                hook_system_messages,
                assistant_text=assistant_text,
                turn_id=turn_id,
                message_id=str(uuid4()),
            )
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
                finish_agent_run_func=finish_model_message,
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
            batch = run_post_batch(tool_calls, tool_results, iteration)
            if batch.blocking_message is not None:
                messages.append(ChatMessage(role="user", content=tool_results))
                return finish_with_conversation(
                    current_workspace, False, batch.blocking_message, iteration,
                    observations, steps, plan, command_timeout_ms, logger,
                    stop_reason="hook_blocked",
                )
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
                compact_hook_runner=compact_hook_runner(iteration),
            )
            checkpoint_conversation()
            continue

        blocked_completion_feedback: str | None = None
        for tool_index, block in enumerate(
            tool_calls[handled_tool_calls:], start=handled_tool_calls
        ):
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
                approval_handler=approval_handler_with_notifications(iteration),
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
                defer_tool_calls=defer_tool_calls,
                hook_model_runtime=hook_model_runtime,
                auto_mode_runtime=auto_mode_runtime,
            )
            if sequential.deferred_tool_use is not None:
                deferred_state = DeferredToolState(
                    assistant_content=tuple(tool_calls),
                    completed_tool_results=tuple(tool_results),
                    next_tool_index=tool_index,
                )
                persist_deferred_tool_batch(
                    current_workspace, deferred_state, resumed=False
                )
                return finish_deferred_run(deferred_state, iteration)
            assert sequential.tool_result is not None
            tool_results.append(sequential.tool_result)
            observation = apply_sequential_runtime_state(sequential, iteration)

            if sequential.halt_turn_message is not None:
                messages.append(ChatMessage(role="user", content=tool_results))
                return finish_with_conversation(
                    current_workspace,
                    False,
                    sequential.halt_turn_message,
                    iteration,
                    observations,
                    steps,
                    plan,
                    command_timeout_ms,
                    logger,
                    stop_reason="hook_blocked",
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

        batch = run_post_batch(tool_calls[: len(tool_results)], tool_results, iteration)
        if batch.blocking_message is not None:
            messages.append(ChatMessage(role="user", content=tool_results))
            return finish_with_conversation(
                current_workspace, False, batch.blocking_message, iteration,
                observations, steps, plan, command_timeout_ms, logger,
                stop_reason="hook_blocked",
            )
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
            compact_hook_runner=compact_hook_runner(iteration),
        )
        checkpoint_conversation()

    return finish_run(False, f"Reached iteration limit ({max_iterations}) before finish.", max_iterations)
