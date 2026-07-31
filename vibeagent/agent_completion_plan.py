from __future__ import annotations

from .agent_completion_kinds import MULTISTEP_CODING_FOLLOWUP_KINDS, PROJECT_CHANGE_OBSERVATION_KINDS
from .agent_observation_utils import observation_failed, summarize
from .types import Observation, PlanItem


def build_unfinished_plan_warning(plan: list[PlanItem]) -> str | None:
    unfinished = [item for item in plan if item.status != "completed"]
    if not unfinished:
        return None
    in_progress = [item for item in unfinished if item.status == "in_progress"]
    pending = [item for item in unfinished if item.status == "pending"]
    labels = [f"{item.status}: {summarize(item.step, 80)}" for item in unfinished[:3]]
    suffix = f"; {'; '.join(labels)}" if labels else ""
    status_parts: list[str] = []
    if in_progress:
        status_parts.append(f"{len(in_progress)} in_progress")
    if pending:
        status_parts.append(f"{len(pending)} pending")
    status_text = ", ".join(status_parts) if status_parts else f"{len(unfinished)} unfinished"
    return f"Task plan still has unfinished item(s): {status_text}{suffix}."


def build_missing_plan_warning(success: bool, observations: list[Observation], plan: list[PlanItem]) -> str | None:
    if not success or plan:
        return None
    if not observations_show_multistep_coding_work(observations):
        return None
    return "Task plan is missing for multi-step coding work; call update_plan with a short checklist before finishing."


def observations_show_multistep_coding_work(observations: list[Observation]) -> bool:
    successful_project_changes = [
        observation
        for observation in observations
        if observation.kind in PROJECT_CHANGE_OBSERVATION_KINDS and not observation_failed(observation)
    ]
    if not successful_project_changes:
        return False
    if len(successful_project_changes) >= 2:
        return True
    first_change_index = next(
        index
        for index, observation in enumerate(observations)
        if observation.kind in PROJECT_CHANGE_OBSERVATION_KINDS and not observation_failed(observation)
    )
    return any(observation.kind in MULTISTEP_CODING_FOLLOWUP_KINDS for observation in observations[first_change_index + 1 :])
