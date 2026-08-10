from __future__ import annotations

from dataclasses import asdict
from collections.abc import Callable

from .agent_delegate import execute_delegate_task_action
from .agent_delegate_profile import resolve_profile_action
from .background_delegate_runtime import start_background_delegate_task
from .config_execution import ExecutionConfig
from .dynamic_workflow_types import WorkflowAgentRequest
from .types import (
    AgentLogger,
    ApprovalDecision,
    ApprovalHandler,
    ApprovalPolicy,
    ApprovalRequest,
    ChatClient,
    DelegateTaskAction,
)
from .workspace_core import RunWorkspace
from .workspace_hooks import ProjectHooks
from .workspace_permissions import ProjectPermissions


def execute_workflow_agent_request(
    workspace: RunWorkspace,
    request: WorkflowAgentRequest,
    client: ChatClient,
    *,
    execution_config: ExecutionConfig,
    approval_handler: ApprovalHandler | None,
    approval_policy: ApprovalPolicy,
    hooks: ProjectHooks,
    permissions: ProjectPermissions,
    logger: AgentLogger | None = None,
    cancel_requested: Callable[[], bool],
) -> dict[str, object]:
    action = DelegateTaskAction(
        type="delegate_task",
        task=request.task,
        context=request.context,
        max_iterations=request.max_iterations,
        mode=request.mode,
        agent=request.agent,
        isolation=request.isolation,
    )
    action = resolve_profile_action(workspace, action)
    parent_iteration = int(request.call_id.rsplit("-", 1)[-1])
    subagent_id = f"wf-{(request.workflow_id or 'direct').removeprefix('workflow-')}-{request.call_id}"

    def execute(
        task_id: str,
        background_cancel: Callable[[], bool] | None = None,
        inbound_messages: Callable[[bool], list[str]] | None = None,
    ):
        return execute_delegate_task_action(
            workspace,
            action,
            client,
            parent_iteration=parent_iteration,
            subagent_id=task_id,
            max_output_tokens=execution_config.max_output_tokens,
            model_retries=execution_config.model_retries,
            model_retry_delay_ms=execution_config.model_retry_delay_ms,
            model_timeout_ms=execution_config.model_timeout_ms,
            command_timeout_ms=execution_config.command_timeout_ms,
            logger=logger,
            approval_handler=approval_handler,
            approval_policy=approval_policy,
            hooks=hooks,
            permissions=permissions,
            cancel_requested=lambda: cancel_requested()
            or (background_cancel is not None and background_cancel()),
            inbound_messages=inbound_messages,
        )

    if action.run_in_background:
        observation = start_background_delegate_task(
            workspace,
            action,
            lambda task_id, background_cancel, inbound: execute(
                task_id,
                background_cancel,
                inbound,
            ),
            task_id=subagent_id,
        )
    else:
        observation = execute(subagent_id)
    return asdict(observation)


def background_workflow_approval_handler(
    approval_policy: ApprovalPolicy,
    approval_handler: ApprovalHandler | None,
) -> ApprovalHandler | None:
    if approval_policy != "ask":
        return approval_handler

    def deny_interactive_prompt(request: ApprovalRequest) -> ApprovalDecision:
        return ApprovalDecision(
            approved=False,
            message=(
                f"Denied {request.action_type}: background workflows cannot open an interactive approval prompt. "
                "Use /approval allow before starting the workflow or configure a trusted project permission rule."
            ),
        )

    return deny_interactive_prompt


__all__ = ["background_workflow_approval_handler", "execute_workflow_agent_request"]
