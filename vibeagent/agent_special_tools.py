from __future__ import annotations

from dataclasses import replace

from .auto_mode import AutoModeRuntime
from .agent_action_logging import log_action
from .agent_approval import build_approval_request
from .background_delegate_runtime import (
    background_delegate_task_is_running,
    send_background_delegate_message,
    start_background_delegate_task,
)
from .agent_delegate import execute_delegate_task_action
from .agent_delegate_profile import resolve_profile_action
from .deep_review_runtime import execute_deep_review_action
from .agent_hooks import (
    ApplyUpdatedInput,
    ExecuteActionSafely,
    HookWrappedToolResult,
    run_hooks_around_tool,
)
from .agent_plan_approval import PlanApprovalError, prepare_plan_approval
from .agent_hook_prompt import HookModelRuntime
from .agent_runtime_utils import append_session_event
from .agent_team_runtime import teammate_spawn_error
from .agent_steps import complete_task_step, start_task_step
from .agent_user_input import execute_user_input_action
from .types import (
    AgentLogger,
    ApprovalHandler,
    ApprovalPolicy,
    AskUserAction,
    ChatClient,
    DeepReviewAction,
    DelegateTaskAction,
    Observation,
    PeerMessageObservation,
    SendMessageAction,
    TaskStep,
    ToolErrorObservation,
    UserInputHandler,
)
from .peer_protocol import send_peer_message
from .peer_types import PeerMessagingError
from .subagent_transcripts import SubagentTranscriptError, read_subagent_transcript
from .workspace_core import RunWorkspace
from .workspace_hooks import ProjectHooks
from .workspace_permissions import ProjectPermissions


def execute_special_tool_action(
    workspace: RunWorkspace,
    action: AskUserAction | DeepReviewAction | DelegateTaskAction | SendMessageAction,
    client: ChatClient,
    *,
    steps: list[TaskStep],
    observations: list[Observation],
    iteration: int,
    tool_name: str,
    max_output_tokens: int,
    model_retries: int,
    model_retry_delay_ms: int,
    model_timeout_ms: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
    approval_handler: ApprovalHandler | None,
    approval_policy: ApprovalPolicy,
    user_input_handler: UserInputHandler | None,
    hooks: ProjectHooks,
    permissions: ProjectPermissions,
    execute_action_safely_func: ExecuteActionSafely,
    tool_ceiling_names: frozenset[str] | None = None,
    tool_input: dict[str, object] | None = None,
    apply_updated_input: ApplyUpdatedInput | None = None,
    defer_tool_calls: bool = False,
    tool_use_id: str | None = None,
    hook_model_runtime: HookModelRuntime | None = None,
    auto_mode_runtime: AutoModeRuntime | None = None,
) -> HookWrappedToolResult:
    return run_hooks_around_tool(
        workspace,
        hooks,
        tool_name,
        action,
        iteration,
        command_timeout_ms,
        logger,
        approval_handler,
        approval_policy,
        execute_action_safely_func,
        lambda effective_workspace, effective_action: _execute_special_tool(
            effective_workspace,
            effective_action,
            client,
            steps=steps,
            observations=observations,
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
            hooks=hooks,
            permissions=permissions,
            tool_ceiling_names=tool_ceiling_names,
            parent_tool_use_id=tool_use_id,
        ),
        permissions,
        build_default_approval_request=build_approval_request,
        tool_input=tool_input,
        apply_updated_input=apply_updated_input,
        finalize_action=lambda candidate: (
            resolve_profile_action(workspace, candidate)
            if isinstance(candidate, DelegateTaskAction)
            else candidate
        ),
        defer_tool_calls=defer_tool_calls,
        tool_use_id=tool_use_id,
        hook_model_runtime=hook_model_runtime,
        auto_mode_runtime=auto_mode_runtime,
    )


def _execute_special_tool(
    workspace: RunWorkspace,
    action: AskUserAction | DeepReviewAction | DelegateTaskAction | SendMessageAction,
    client: ChatClient,
    *,
    steps: list[TaskStep],
    observations: list[Observation],
    iteration: int,
    max_output_tokens: int,
    model_retries: int,
    model_retry_delay_ms: int,
    model_timeout_ms: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
    approval_handler: ApprovalHandler | None,
    approval_policy: ApprovalPolicy,
    user_input_handler: UserInputHandler | None,
    hooks: ProjectHooks,
    permissions: ProjectPermissions,
    tool_ceiling_names: frozenset[str] | None,
    parent_tool_use_id: str | None,
) -> Observation:
    if isinstance(action, AskUserAction):
        return execute_user_input_action(
            workspace,
            action,
            steps,
            iteration,
            logger,
            user_input_handler,
        )
    if isinstance(action, DeepReviewAction):
        step = start_task_step(workspace, steps, iteration, action, logger)
        log_action(logger, action)
        observation = execute_deep_review_action(
            workspace,
            action,
            client,
            parent_iteration=iteration,
            max_output_tokens=max_output_tokens,
            model_retries=model_retries,
            model_retry_delay_ms=model_retry_delay_ms,
            model_timeout_ms=model_timeout_ms,
            command_timeout_ms=command_timeout_ms,
            logger=logger,
            approval_handler=approval_handler,
            approval_policy=approval_policy,
            hooks=hooks,
            permissions=permissions,
            tool_ceiling_names=tool_ceiling_names,
            review_id=f"{iteration}-{step.id}",
        )
        complete_task_step(workspace, step, observation, iteration, logger)
        return observation
    if isinstance(action, SendMessageAction):
        step = start_task_step(workspace, steps, iteration, action, logger)
        log_action(logger, action)
        try:
            if action.approve_plan and background_delegate_task_is_running(
                workspace, action.to
            ):
                raise PlanApprovalError(
                    f"Teammate {action.to} plan cannot be approved while its status is running."
                )
            delivered = (
                None
                if action.approve_plan
                else send_background_delegate_message(workspace, action.to, action.message)
            )
            if delivered is not None:
                append_session_event(
                    workspace.session_dir,
                    "subagent_message_sent",
                    {"subagent_id": action.to, "resumed": False},
                )
                complete_task_step(workspace, step, delivered, iteration, logger)
                return delivered
            transcript = read_subagent_transcript(workspace, action.to)
            resume_transcript = transcript
            followup_message = action.message
            if action.approve_plan:
                resumed_action, resume_transcript, followup_message = prepare_plan_approval(
                    transcript,
                    action.message,
                )
            else:
                resumed_action = replace(transcript.action, run_in_background=True)
            delegate_observation = start_background_delegate_task(
                workspace,
                resumed_action,
                lambda task_id, cancel_requested, inbound_messages: execute_delegate_task_action(
                    workspace,
                    resumed_action,
                    client,
                    parent_iteration=iteration,
                    subagent_id=task_id,
                    max_output_tokens=max_output_tokens,
                    model_retries=model_retries,
                    model_retry_delay_ms=model_retry_delay_ms,
                    model_timeout_ms=model_timeout_ms,
                    command_timeout_ms=command_timeout_ms,
                    logger=logger,
                    approval_handler=approval_handler,
                    approval_policy=approval_policy,
                    hooks=hooks,
                    permissions=permissions,
                    cancel_requested=cancel_requested,
                    resume_transcript=resume_transcript,
                    followup_message=followup_message,
                    inbound_messages=inbound_messages,
                    depth=transcript.depth,
                    parent_subagent_id=transcript.parent_id,
                    tool_ceiling_names=tool_ceiling_names,
                    parent_tool_use_id=parent_tool_use_id,
                ),
                task_id=action.to,
                resumed=True,
                depth=transcript.depth,
                parent_id=transcript.parent_id,
            )
            append_session_event(
                workspace.session_dir,
                "subagent_plan_approved" if action.approve_plan else "subagent_message_sent",
                {"subagent_id": action.to, "resumed": True},
            )
        except PlanApprovalError as error:
            delegate_observation = ToolErrorObservation(
                kind="tool_error", tool="SendMessage", message=str(error)
            )
        except ValueError as error:
            delegate_observation = ToolErrorObservation(
                kind="tool_error", tool="SendMessage", message=str(error)
            )
        except SubagentTranscriptError as error:
            if action.approve_plan:
                delegate_observation = ToolErrorObservation(
                    kind="tool_error", tool="SendMessage", message=str(error)
                )
                complete_task_step(workspace, step, delegate_observation, iteration, logger)
                return delegate_observation
            try:
                delivery = send_peer_message(action.to, action.message)
            except PeerMessagingError as peer_error:
                delegate_observation = ToolErrorObservation(
                    kind="tool_error", tool="SendMessage", message=str(peer_error)
                )
            else:
                if delivery is None:
                    delegate_observation = ToolErrorObservation(
                        kind="tool_error", tool="SendMessage", message=str(error)
                    )
                else:
                    delegate_observation = PeerMessageObservation(
                        kind="peer_message",
                        ok=delivery.status == "delivered",
                        to=action.to,
                        peer_id=delivery.target_id,
                        status=delivery.status,
                        message=delivery.message,
                    )
                    append_session_event(
                        workspace.session_dir,
                        "peer_message_sent",
                        {
                            "peer_id": delivery.target_id,
                            "peer_name": delivery.target_name,
                            "status": delivery.status,
                        },
                    )
        complete_task_step(workspace, step, delegate_observation, iteration, logger)
        return delegate_observation
    step = start_task_step(workspace, steps, iteration, action, logger)
    log_action(logger, action)
    spawn_error = teammate_spawn_error(
        workspace,
        action.teammate_name,
        depth=1,
    )
    if spawn_error is not None:
        delegate_observation = ToolErrorObservation(
            kind="tool_error",
            tool="Agent",
            message=spawn_error,
        )
        complete_task_step(workspace, step, delegate_observation, iteration, logger)
        return delegate_observation
    if action.run_in_background:
        try:
            delegate_observation = start_background_delegate_task(
                workspace,
                action,
                lambda task_id, cancel_requested, inbound_messages: execute_delegate_task_action(
                    workspace,
                    action,
                    client,
                    parent_iteration=iteration,
                    subagent_id=task_id,
                    max_output_tokens=max_output_tokens,
                    model_retries=model_retries,
                    model_retry_delay_ms=model_retry_delay_ms,
                    model_timeout_ms=model_timeout_ms,
                    command_timeout_ms=command_timeout_ms,
                    logger=logger,
                    approval_handler=approval_handler,
                    approval_policy=approval_policy,
                    hooks=hooks,
                    permissions=permissions,
                    cancel_requested=cancel_requested,
                    inbound_messages=inbound_messages,
                    tool_ceiling_names=tool_ceiling_names,
                    parent_tool_use_id=parent_tool_use_id,
                ),
                task_id=action.teammate_name,
            )
        except ValueError as error:
            delegate_observation = ToolErrorObservation(
                kind="tool_error",
                tool="Agent" if action.teammate_name is not None else "delegate_task",
                message=str(error),
            )
    else:
        delegate_observation = execute_delegate_task_action(
            workspace,
            action,
            client,
            parent_iteration=iteration,
            subagent_id=f"delegate-{iteration}-{step.id}",
            max_output_tokens=max_output_tokens,
            model_retries=model_retries,
            model_retry_delay_ms=model_retry_delay_ms,
            model_timeout_ms=model_timeout_ms,
            command_timeout_ms=command_timeout_ms,
            logger=logger,
            approval_handler=approval_handler,
            approval_policy=approval_policy,
            parent_observations=observations,
            parent_steps=steps,
            hooks=hooks,
            permissions=permissions,
            tool_ceiling_names=tool_ceiling_names,
            parent_tool_use_id=parent_tool_use_id,
        )
    complete_task_step(workspace, step, delegate_observation, iteration, logger)
    return delegate_observation
