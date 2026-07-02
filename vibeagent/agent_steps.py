from __future__ import annotations

from .agent_action_labels import build_step_label
from .agent_action_targets import build_action_target
from .agent_observation_utils import observation_failed
from .agent_runtime_utils import append_session_event, summarize_command
from .types import AgentLogger, Observation, TaskStep
from .workspace_core import RunWorkspace


def start_task_step(
    workspace: RunWorkspace,
    steps: list[TaskStep],
    iteration: int,
    action: object,
    logger: AgentLogger | None,
) -> TaskStep:
    step = TaskStep(
        id=len(steps) + 1,
        label=build_step_label(action),
        action_type=str(getattr(action, "type", "unknown")),
        target=build_action_target(action),
        status="running",
    )
    steps.append(step)
    append_session_event(workspace.session_dir, "step_started", {"iteration": iteration, "step": step})
    if logger:
        logger("step started", step.label)
    return step


def complete_task_step(
    workspace: RunWorkspace,
    step: TaskStep,
    observation: Observation,
    iteration: int,
    logger: AgentLogger | None,
) -> None:
    if observation.kind == "approval_denied":
        step.status = "denied"
    elif observation_failed(observation):
        step.status = "failed"
    else:
        step.status = "completed"
    step.message = observation_summary(observation)
    append_session_event(workspace.session_dir, "step_completed", {"iteration": iteration, "step": step})
    if logger:
        logger("step completed", f"{step.label} -> {step.status}")


def observation_summary(observation: Observation) -> str:
    if observation.kind == "run_command":
        return summarize_command(observation.result)
    if observation.kind == "run_commands":
        return observation.message
    return str(getattr(observation, "message", observation.kind))
