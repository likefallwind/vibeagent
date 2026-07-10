from __future__ import annotations

from collections.abc import Callable

from .actions import execute_action
from .agent_auto_checkpoint import (
    create_auto_checkpoint_before_action as _create_auto_checkpoint_before_action,
    should_auto_checkpoint_before_action as _should_auto_checkpoint_before_action,
)
from .types import AgentLogger, Observation, TaskStep, ToolErrorObservation
from .workspace_core import RunWorkspace


ExecuteAction = Callable[[RunWorkspace, object, int], Observation]
ExecuteActionSafely = Callable[[RunWorkspace, object, int, str], Observation]


def execute_action_safely(
    workspace: RunWorkspace,
    action: object,
    command_timeout_ms: int,
    tool_name: str,
    execute_action_func: ExecuteAction = execute_action,
) -> Observation:
    try:
        return execute_action_func(workspace, action, command_timeout_ms)
    except Exception as error:
        return ToolErrorObservation(
            kind="tool_error",
            tool=tool_name or str(getattr(action, "type", "unknown")) or "unknown",
            message=f"Tool execution failed: {error}",
        )


def should_auto_checkpoint_before_action(workspace: RunWorkspace, action: object) -> bool:
    return _should_auto_checkpoint_before_action(workspace, action)


def create_auto_checkpoint_before_action(
    workspace: RunWorkspace,
    action: object,
    steps: list[TaskStep],
    iteration: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
    execute_action_safely_func: ExecuteActionSafely = execute_action_safely,
) -> Observation | None:
    return _create_auto_checkpoint_before_action(
        workspace,
        action,
        steps,
        iteration,
        command_timeout_ms,
        logger,
        execute_action_safely_func,
    )
