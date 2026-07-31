from __future__ import annotations

from .agent_completion_kinds import FINITE_COMMAND_OBSERVATION_KINDS
from .agent_completion_verification import (
    failed_suggested_check_results,
    final_review_focused_test_commands,
    final_review_suggested_commands,
    latest_successful_auto_final_review_change_index,
    successful_suggested_check_commands,
)
from .agent_observation_utils import observation_failed
from .types import Observation


def auto_final_review_reason(success: bool, observations: list[Observation]) -> str | None:
    if not success:
        return None
    final_review_index = latest_observation_index(observations, {"final_review"})
    project_change_index = latest_successful_auto_final_review_change_index(observations)
    if project_change_index is not None:
        if final_review_index is None:
            return "Project changes completed without final_review"
        if project_change_index > final_review_index:
            return "Project changes completed after final_review"
    process_start_index = latest_successful_process_start_index(observations)
    if process_start_index is not None:
        if final_review_index is None:
            return "Background command started without final_review"
        if process_start_index > final_review_index:
            return "Background command started after final_review"
    command_index = latest_successful_finite_command_index(observations)
    if command_index is not None:
        if final_review_index is None:
            return "Command execution completed without final_review"
        if command_index > final_review_index:
            command_matches_review_check = finite_command_matches_final_review_check(
                observations[command_index],
                observations[final_review_index],
            )
            if not command_matches_review_check:
                return "Command execution completed after final_review"
            if getattr(observations[final_review_index], "ready", None) is False:
                return "Final review refreshed after verification"
    return None


def should_auto_run_final_review(success: bool, observations: list[Observation]) -> bool:
    return auto_final_review_reason(success, observations) is not None


def latest_observation_index(observations: list[Observation], kinds: set[str]) -> int | None:
    for index in range(len(observations) - 1, -1, -1):
        if observations[index].kind in kinds:
            return index
    return None


def latest_successful_process_start_index(observations: list[Observation]) -> int | None:
    for index in range(len(observations) - 1, -1, -1):
        observation = observations[index]
        if observation.kind == "start_command" and bool(getattr(observation, "ok", False)):
            return index
    return None


def latest_successful_finite_command_index(observations: list[Observation]) -> int | None:
    for index in range(len(observations) - 1, -1, -1):
        observation = observations[index]
        if observation.kind in FINITE_COMMAND_OBSERVATION_KINDS:
            if not observation_failed(observation):
                return index
    return None


def finite_command_matches_final_review_check(command_observation: Observation, final_review: Observation) -> bool:
    check_commands = final_review_suggested_commands(final_review) | final_review_focused_test_commands(final_review)
    if not check_commands:
        return False
    return bool(
        successful_suggested_check_commands(command_observation, check_commands)
        or failed_suggested_check_results(command_observation, check_commands)
    )
