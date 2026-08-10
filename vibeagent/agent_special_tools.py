from __future__ import annotations

from dataclasses import replace

from .agent_action_logging import log_action
from .agent_approval import build_approval_request
from .background_delegate_runtime import send_background_delegate_message, start_background_delegate_task
from .agent_delegate import execute_delegate_task_action
from .agent_hooks import ExecuteActionSafely, HookWrappedToolResult, run_hooks_around_tool
from .agent_runtime_utils import append_session_event
from .agent_steps import complete_task_step, start_task_step
from .agent_user_input import execute_user_input_action
from .types import (
    AgentLogger,
    ApprovalHandler,
    ApprovalPolicy,
    AskUserAction,
    ChatClient,
    DelegateTaskAction,
    Observation,
    SendMessageAction,
    TaskStep,
    ToolErrorObservation,
    UserInputHandler,
)
from .subagent_transcripts import SubagentTranscriptError, read_subagent_transcript
from .workspace_core import RunWorkspace
from .workspace_hooks import ProjectHooks
from .workspace_permissions import ProjectPermissions
from .workspace_agents import read_project_agent


def execute_special_tool_action(
    workspace: RunWorkspace,
    action: AskUserAction | DelegateTaskAction | SendMessageAction,
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
) -> HookWrappedToolResult:
    action = _resolve_profile_isolation(workspace, action)
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
        lambda: _execute_special_tool(
            workspace,
            action,
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
        ),
        permissions,
        default_approval_request=build_approval_request(action),
    )


def _resolve_profile_isolation(
    workspace: RunWorkspace,
    action: AskUserAction | DelegateTaskAction | SendMessageAction,
) -> AskUserAction | DelegateTaskAction | SendMessageAction:
    if not isinstance(action, DelegateTaskAction) or action.isolation is not None or action.agent is None:
        return action
    try:
        profile = read_project_agent(workspace, action.agent)
    except (OSError, UnicodeError, ValueError):
        return action
    if profile.get("isolation") == "worktree":
        return replace(action, isolation="worktree")
    return action


def _execute_special_tool(
    workspace: RunWorkspace,
    action: AskUserAction | DelegateTaskAction | SendMessageAction,
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
    if isinstance(action, SendMessageAction):
        step = start_task_step(workspace, steps, iteration, action, logger)
        log_action(logger, action)
        try:
            delivered = send_background_delegate_message(workspace, action.to, action.message)
            if delivered is not None:
                append_session_event(
                    workspace.session_dir,
                    "subagent_message_sent",
                    {"subagent_id": action.to, "resumed": False},
                )
                complete_task_step(workspace, step, delivered, iteration, logger)
                return delivered
            transcript = read_subagent_transcript(workspace, action.to)
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
                    resume_transcript=transcript,
                    followup_message=action.message,
                    inbound_messages=inbound_messages,
                    depth=transcript.depth,
                    parent_subagent_id=transcript.parent_id,
                ),
                task_id=action.to,
                resumed=True,
                depth=transcript.depth,
                parent_id=transcript.parent_id,
            )
            append_session_event(
                workspace.session_dir,
                "subagent_message_sent",
                {"subagent_id": action.to, "resumed": True},
            )
        except SubagentTranscriptError as error:
            delegate_observation = ToolErrorObservation(
                kind="tool_error", tool="SendMessage", message=str(error)
            )
        complete_task_step(workspace, step, delegate_observation, iteration, logger)
        return delegate_observation
    step = start_task_step(workspace, steps, iteration, action, logger)
    log_action(logger, action)
    if action.run_in_background:
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
            ),
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
        )
    complete_task_step(workspace, step, delegate_observation, iteration, logger)
    return delegate_observation
