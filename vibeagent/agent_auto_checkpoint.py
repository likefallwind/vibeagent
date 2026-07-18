from __future__ import annotations

from collections.abc import Callable

from .actions import read_checkpoint_git_head
from .agent_completion_kinds import FINITE_COMMAND_OBSERVATION_KINDS, PROJECT_CHANGE_OBSERVATION_KINDS
from .agent_observation_utils import observation_failed
from .agent_steps import complete_task_step, observation_summary, start_task_step
from .agent_tool_results import record_tool_result_event
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
    checkpoint_action = CheckpointCreateAction(type="checkpoint_create", label=f"auto before {action_type}")
    if logger:
        logger("auto checkpoint", f"Creating checkpoint before {action_type}.")
    step = start_task_step(workspace, steps, iteration, checkpoint_action, logger)
    observation = execute_action_safely_func(workspace, checkpoint_action, command_timeout_ms, "checkpoint_create")
    complete_task_step(workspace, step, observation, iteration, logger)
    record_tool_result_event(
        workspace,
        tool_id="auto-checkpoint",
        tool_name="checkpoint_create",
        observation=observation,
        iteration=iteration,
        auto=True,
        event_extra={"before_action_type": action_type},
    )
    if observation_failed(observation):
        if logger:
            logger("auto checkpoint skipped", observation_summary(observation))
    return observation
