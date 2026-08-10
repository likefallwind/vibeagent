from __future__ import annotations

from collections.abc import Callable

from .actions import read_checkpoint_git_head
from .agent_completion_kinds import FINITE_COMMAND_OBSERVATION_KINDS, PROJECT_CHANGE_OBSERVATION_KINDS
from .agent_observation_utils import observation_failed
from .agent_steps import complete_task_step, observation_summary, start_task_step
from .agent_tool_results import record_tool_result_event
from .checkpoint_session import prune_session_checkpoints
from .redaction import redact_sensitive_text
from .types import AgentLogger, CheckpointCreateAction, Observation, TaskStep
from .workspace_core import RunWorkspace


ExecuteActionSafely = Callable[[RunWorkspace, object, int, str], Observation]


def should_auto_checkpoint_before_action(workspace: RunWorkspace, action: object) -> bool:
    action_type = str(getattr(action, "type", ""))
    checkpointed_action_kinds = PROJECT_CHANGE_OBSERVATION_KINDS | FINITE_COMMAND_OBSERVATION_KINDS
    if action_type not in checkpointed_action_kinds:
        return False
    return bool(read_checkpoint_git_head(workspace.root))


def create_auto_checkpoint_before_action(
    workspace: RunWorkspace,
    action: object,
    steps: list[TaskStep],
    iteration: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
    execute_action_safely_func: ExecuteActionSafely,
) -> Observation | None:
    action_type = str(getattr(action, "type", "project change"))
    return _create_auto_checkpoint(
        workspace,
        label=f"auto before {action_type}",
        log_target=f"before {action_type}",
        event_extra={"before_action_type": action_type},
        tool_id="auto-checkpoint",
        steps=steps,
        iteration=iteration,
        command_timeout_ms=command_timeout_ms,
        logger=logger,
        execute_action_safely_func=execute_action_safely_func,
    )


def create_auto_checkpoint_for_prompt(
    workspace: RunWorkspace,
    task: str,
    steps: list[TaskStep],
    command_timeout_ms: int,
    logger: AgentLogger | None,
    execute_action_safely_func: ExecuteActionSafely,
) -> Observation | None:
    if not read_checkpoint_git_head(workspace.root):
        return None
    safe_task = " ".join(redact_sensitive_text(task).split())
    label = f"prompt: {safe_task[:96]}" if safe_task else "prompt checkpoint"
    observation = _create_auto_checkpoint(
        workspace,
        label=label,
        log_target="for user prompt",
        event_extra={"prompt_checkpoint": True},
        tool_id="prompt-checkpoint",
        steps=steps,
        iteration=0,
        command_timeout_ms=command_timeout_ms,
        logger=logger,
        execute_action_safely_func=execute_action_safely_func,
    )
    if observation is not None and not observation_failed(observation):
        deleted, warnings = prune_session_checkpoints(workspace.root, workspace.run_id)
        if logger and deleted:
            logger("checkpoint retention", f"Pruned {len(deleted)} old session checkpoint(s).")
        if logger:
            for warning in warnings:
                logger("checkpoint retention warning", warning)
    return observation


def _create_auto_checkpoint(
    workspace: RunWorkspace,
    *,
    label: str,
    log_target: str,
    event_extra: dict[str, object],
    tool_id: str,
    steps: list[TaskStep],
    iteration: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
    execute_action_safely_func: ExecuteActionSafely,
) -> Observation | None:
    checkpoint_action = CheckpointCreateAction(type="checkpoint_create", label=label)
    if logger:
        logger("auto checkpoint", f"Creating checkpoint {log_target}.")
    step = start_task_step(workspace, steps, iteration, checkpoint_action, logger)
    observation = execute_action_safely_func(workspace, checkpoint_action, command_timeout_ms, "checkpoint_create")
    complete_task_step(workspace, step, observation, iteration, logger)
    record_tool_result_event(
        workspace,
        tool_id=tool_id,
        tool_name="checkpoint_create",
        observation=observation,
        iteration=iteration,
        auto=True,
        event_extra=event_extra,
    )
    if observation_failed(observation):
        if logger:
            logger("auto checkpoint skipped", observation_summary(observation))
    return observation
