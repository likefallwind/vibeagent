from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .agent_action_logging import log_action
from .agent_approval import (
    build_approval_request,
    request_approval,
    summarize_approval_decision,
    summarize_approval_request,
)
from .agent_approval_preview import attach_approval_preview
from .agent_runtime_utils import append_session_event, build_repeated_list_observation, find_repeated_list_observation
from .agent_steps import complete_task_step, start_task_step
from .types import (
    AgentLogger,
    ApprovalDeniedObservation,
    ApprovalHandler,
    Observation,
    TaskStep,
)
from .workspace_core import RunWorkspace


ExecuteActionSafely = Callable[[RunWorkspace, object, int, str], Observation]
ShouldAutoCheckpoint = Callable[[RunWorkspace, object], bool]
CreateAutoCheckpoint = Callable[[RunWorkspace, object, list[TaskStep], int, int, AgentLogger | None], Observation | None]


@dataclass(frozen=True)
class ToolActionExecutionResult:
    observation: Observation
    auto_checkpoint: Observation | None
    auto_checkpoint_attempted: bool


def execute_parsed_tool_action(
    workspace: RunWorkspace,
    action: object,
    observations: list[Observation],
    steps: list[TaskStep],
    iteration: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
    approval_handler: ApprovalHandler | None,
    tool_name: str,
    auto_checkpoint_attempted: bool,
    execute_action_safely_func: ExecuteActionSafely,
    should_auto_checkpoint_before_action_func: ShouldAutoCheckpoint,
    create_auto_checkpoint_before_action_func: CreateAutoCheckpoint,
) -> ToolActionExecutionResult:
    step = start_task_step(workspace, steps, iteration, action, logger)
    log_action(logger, action)

    observation = _build_repeated_list_observation(action, observations)
    auto_checkpoint: Observation | None = None
    checkpoint_attempted = auto_checkpoint_attempted
    if observation is None:
        observation, auto_checkpoint, checkpoint_attempted = _execute_non_repeated_action(
            workspace,
            action,
            observations,
            steps,
            step,
            iteration,
            command_timeout_ms,
            logger,
            approval_handler,
            tool_name,
            auto_checkpoint_attempted,
            execute_action_safely_func,
            should_auto_checkpoint_before_action_func,
            create_auto_checkpoint_before_action_func,
        )

    complete_task_step(workspace, step, observation, iteration, logger)
    return ToolActionExecutionResult(
        observation=observation,
        auto_checkpoint=auto_checkpoint,
        auto_checkpoint_attempted=checkpoint_attempted,
    )


def _build_repeated_list_observation(action: object, observations: list[Observation]) -> Observation | None:
    repeated_list = find_repeated_list_observation(action, observations)
    if not repeated_list:
        return None
    return build_repeated_list_observation(repeated_list)


def _execute_non_repeated_action(
    workspace: RunWorkspace,
    action: object,
    observations: list[Observation],
    steps: list[TaskStep],
    step: TaskStep,
    iteration: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
    approval_handler: ApprovalHandler | None,
    tool_name: str,
    auto_checkpoint_attempted: bool,
    execute_action_safely_func: ExecuteActionSafely,
    should_auto_checkpoint_before_action_func: ShouldAutoCheckpoint,
    create_auto_checkpoint_before_action_func: CreateAutoCheckpoint,
) -> tuple[Observation, Observation | None, bool]:
    approval_request = build_approval_request(action)
    if approval_request:
        approval_request = attach_approval_preview(approval_request, action, observations)
        append_session_event(
            workspace.session_dir,
            "approval_requested",
            {"iteration": iteration, "step": step, "request": approval_request},
        )
        if logger:
            logger("approval required", summarize_approval_request(approval_request))
        decision = request_approval(approval_handler, approval_request)
        append_session_event(
            workspace.session_dir,
            "approval_decision",
            {"iteration": iteration, "step": step, "decision": decision},
        )
        if logger:
            status = "approval approved" if decision.approved else "approval denied"
            logger(status, summarize_approval_decision(approval_request, decision))
        if not decision.approved:
            return (
                ApprovalDeniedObservation(
                    kind="approval_denied",
                    action_type=approval_request.action_type,
                    target=approval_request.target,
                    message=decision.message or "Action was denied by approval policy.",
                ),
                None,
                auto_checkpoint_attempted,
            )

    auto_checkpoint, checkpoint_attempted = _maybe_create_auto_checkpoint(
        workspace,
        action,
        steps,
        iteration,
        command_timeout_ms,
        logger,
        auto_checkpoint_attempted,
        should_auto_checkpoint_before_action_func,
        create_auto_checkpoint_before_action_func,
    )
    observation = execute_action_safely_func(workspace, action, command_timeout_ms, tool_name)
    return observation, auto_checkpoint, checkpoint_attempted


def _maybe_create_auto_checkpoint(
    workspace: RunWorkspace,
    action: object,
    steps: list[TaskStep],
    iteration: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
    auto_checkpoint_attempted: bool,
    should_auto_checkpoint_before_action_func: ShouldAutoCheckpoint,
    create_auto_checkpoint_before_action_func: CreateAutoCheckpoint,
) -> tuple[Observation | None, bool]:
    if auto_checkpoint_attempted or not should_auto_checkpoint_before_action_func(workspace, action):
        return None, auto_checkpoint_attempted
    auto_checkpoint = create_auto_checkpoint_before_action_func(
        workspace,
        action,
        steps,
        iteration,
        command_timeout_ms,
        logger,
    )
    return auto_checkpoint, True
