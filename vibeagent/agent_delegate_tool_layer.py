from __future__ import annotations

from collections.abc import Callable

from .auto_mode import AutoModeRuntime
from .agent_execution_support import (
    create_auto_checkpoint_before_action,
    should_auto_checkpoint_before_action,
)
from .agent_hook_prompt import HookModelRuntime
from .agent_hook_results import HookRunResult
from .agent_tool_execution import execute_parsed_tool_action
from .types import AgentLogger, ApprovalHandler, ApprovalPolicy, Observation, TaskStep
from .workspace_core import RunWorkspace
from .workspace_hooks import ProjectHooks
from .workspace_permissions import ProjectPermissions


def execute_delegate_with_tool_layer(
    workspace: RunWorkspace,
    parsed: object,
    *,
    observations: list[Observation],
    steps: list[TaskStep],
    iteration: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
    approval_handler: ApprovalHandler | None,
    tool_name: str,
    auto_checkpoint_attempted: bool,
    approval_policy: ApprovalPolicy,
    hooks: ProjectHooks,
    permissions: ProjectPermissions,
    tool_input: dict[str, object] | None = None,
    apply_updated_input: Callable[[dict[str, object]], object] | None = None,
    tool_use_id: str | None = None,
    hook_model_runtime: HookModelRuntime | None = None,
    auto_mode_runtime: AutoModeRuntime | None = None,
    execute_action_safely_func: Callable[..., Observation],
) -> tuple[
    Observation,
    bool,
    tuple[HookRunResult, ...],
    str | None,
    object | None,
    bool,
]:
    execution = execute_parsed_tool_action(
        workspace,
        parsed,
        observations,
        steps,
        iteration,
        command_timeout_ms,
        logger,
        approval_handler,
        tool_name,
        auto_checkpoint_attempted,
        execute_action_safely_func,
        should_auto_checkpoint_before_action,
        create_auto_checkpoint_before_action,
        approval_policy,
        hooks,
        permissions,
        tool_input,
        apply_updated_input,
        False,
        tool_use_id,
        hook_model_runtime,
        auto_mode_runtime,
    )
    if execution.auto_checkpoint is not None:
        observations.append(execution.auto_checkpoint)
    observations.extend(execution.additional_observations)
    return (
        execution.observation,
        execution.auto_checkpoint_attempted,
        execution.hook_results,
        execution.halt_turn_message,
        execution.updated_tool_output,
        execution.updated_tool_output_set,
    )


__all__ = ["execute_delegate_with_tool_layer"]
