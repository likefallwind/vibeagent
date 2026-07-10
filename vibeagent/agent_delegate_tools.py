from __future__ import annotations

from dataclasses import dataclass

from .actions import ActionParseError, execute_action, parse_tool_action
from .agent_execution_support import (
    create_auto_checkpoint_before_action,
    execute_action_safely,
    should_auto_checkpoint_before_action,
)
from .agent_parallel_safety import PARALLEL_SAFE_TOOL_NAMES, is_parallel_safe_action
from .agent_runtime_utils import tool_error_observation
from .agent_tool_execution import execute_parsed_tool_action
from .agent_tool_registry import (
    activate_agent_tool_names,
    agent_tool_definitions,
    initial_agent_tool_names,
    prepare_action_for_policy,
    tool_available_for_policy,
    tool_search_activation_names,
)
from .tool_definitions import AGENT_TOOL_DEFINITIONS
from .types import (
    AgentLogger,
    ApprovalHandler,
    ApprovalPolicy,
    FinishAction,
    Observation,
    TaskStep,
    ToolErrorObservation,
)
from .workspace_core import RunWorkspace


DELEGATE_TOOL_NAMES = {
    name
    for name in PARALLEL_SAFE_TOOL_NAMES
    if not name.startswith("check_") and name not in {"final_review"}
}
DELEGATE_TOOL_DEFINITIONS = [
    tool
    for tool in AGENT_TOOL_DEFINITIONS
    if tool["name"] in DELEGATE_TOOL_NAMES or tool["name"] == "finish"
]
CODE_DELEGATE_EXCLUDED_TOOL_NAMES = frozenset({"ask_user", "delegate_task", "update_plan"})


@dataclass(frozen=True)
class DelegateToolCallExecution:
    observation: Observation | None
    finish_action: FinishAction | None
    auto_checkpoint_attempted: bool


def code_delegate_initial_tool_names(approval_policy: ApprovalPolicy) -> set[str]:
    return {
        name
        for name in initial_agent_tool_names()
        if tool_available_for_policy(name, approval_policy, CODE_DELEGATE_EXCLUDED_TOOL_NAMES)
    }


def delegate_tool_definitions(
    mode: str,
    active_tool_names: set[str],
    approval_policy: ApprovalPolicy,
) -> list[dict[str, object]]:
    if mode == "explore":
        return DELEGATE_TOOL_DEFINITIONS
    return agent_tool_definitions(
        active_tool_names,
        approval_policy,
        CODE_DELEGATE_EXCLUDED_TOOL_NAMES,
    )


def execute_delegate_tool_call(
    workspace: RunWorkspace,
    *,
    mode: str,
    tool_name: str,
    tool_input: object,
    active_tool_names: set[str],
    observations: list[Observation],
    steps: list[TaskStep],
    iteration: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
    approval_handler: ApprovalHandler | None,
    approval_policy: ApprovalPolicy,
    auto_checkpoint_attempted: bool,
) -> DelegateToolCallExecution:
    if mode == "code":
        activate_agent_tool_names(
            active_tool_names,
            [tool_name],
            approval_policy,
            CODE_DELEGATE_EXCLUDED_TOOL_NAMES,
        )
    try:
        parsed = prepare_action_for_policy(parse_tool_action(tool_name, tool_input), approval_policy)
        if isinstance(parsed, FinishAction):
            return DelegateToolCallExecution(None, parsed, auto_checkpoint_attempted)
        observation, checkpoint_attempted = execute_delegate_action(
            workspace,
            mode=mode,
            tool_name=tool_name,
            parsed=parsed,
            observations=observations,
            steps=steps,
            iteration=iteration,
            command_timeout_ms=command_timeout_ms,
            logger=logger,
            approval_handler=approval_handler,
            approval_policy=approval_policy,
            auto_checkpoint_attempted=auto_checkpoint_attempted,
        )
    except ActionParseError as error:
        observation = tool_error_observation(tool_name, error)
        checkpoint_attempted = auto_checkpoint_attempted
    except Exception as error:
        observation = ToolErrorObservation(
            kind="tool_error",
            tool=tool_name or "unknown",
            message=f"Subagent tool execution failed: {error}",
        )
        checkpoint_attempted = auto_checkpoint_attempted

    observations.append(observation)
    if mode == "code":
        activate_agent_tool_names(
            active_tool_names,
            tool_search_activation_names(observation),
            approval_policy,
            CODE_DELEGATE_EXCLUDED_TOOL_NAMES,
        )
    return DelegateToolCallExecution(observation, None, checkpoint_attempted)


def execute_delegate_action(
    workspace: RunWorkspace,
    *,
    mode: str,
    tool_name: str,
    parsed: object,
    observations: list[Observation],
    steps: list[TaskStep],
    iteration: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
    approval_handler: ApprovalHandler | None,
    approval_policy: ApprovalPolicy,
    auto_checkpoint_attempted: bool,
) -> tuple[Observation, bool]:
    if mode == "explore":
        if tool_name not in DELEGATE_TOOL_NAMES or not is_parallel_safe_action(parsed):
            return (
                ToolErrorObservation(
                    kind="tool_error",
                    tool=tool_name or "unknown",
                    message="Subagent tool is not allowed in read-only delegation mode.",
                ),
                auto_checkpoint_attempted,
            )
        return execute_action(workspace, parsed, command_timeout_ms), auto_checkpoint_attempted
    if tool_name in CODE_DELEGATE_EXCLUDED_TOOL_NAMES:
        return (
            ToolErrorObservation(
                kind="tool_error",
                tool=tool_name or "unknown",
                message="Subagent tool is not allowed because coding subagents cannot ask the user, update the parent plan, or delegate again.",
            ),
            auto_checkpoint_attempted,
        )

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
        execute_action_safely,
        should_auto_checkpoint_before_action,
        create_auto_checkpoint_before_action,
        approval_policy,
    )
    if execution.auto_checkpoint is not None:
        observations.append(execution.auto_checkpoint)
    return execution.observation, execution.auto_checkpoint_attempted
