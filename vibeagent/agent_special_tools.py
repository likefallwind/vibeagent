from __future__ import annotations

from .agent_action_logging import log_action
from .agent_delegate import execute_delegate_task_action
from .agent_hooks import ExecuteActionSafely, HookWrappedToolResult, run_hooks_around_tool
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
    TaskStep,
    UserInputHandler,
)
from .workspace_core import RunWorkspace
from .workspace_hooks import ProjectHooks
from .workspace_permissions import ProjectPermissions


def execute_special_tool_action(
    workspace: RunWorkspace,
    action: AskUserAction | DelegateTaskAction,
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
    )


def _execute_special_tool(
    workspace: RunWorkspace,
    action: AskUserAction | DelegateTaskAction,
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
    step = start_task_step(workspace, steps, iteration, action, logger)
    log_action(logger, action)
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
