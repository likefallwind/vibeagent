from __future__ import annotations

from .agent_completion_kinds import PROJECT_CHANGE_OBSERVATION_KINDS, VERIFICATION_INVALIDATING_OBSERVATION_KINDS
from .agent_observation_utils import observation_failed
from .types import Observation
from .verification_command_utils import command_keys_from_objects, verification_commands_from_final_review


def build_verification_checks(success: bool, observations: list[Observation]) -> list[str]:
    if not success:
        return []
    final_review = next((observation for observation in reversed(observations) if observation.kind == "final_review"), None)
    if final_review is None:
        return []
    verification_commands = final_review_verification_commands(final_review)
    if not verification_commands:
        return []
    last_change_index = latest_successful_verification_invalidating_change_index(observations)
    if last_change_index is None:
        if int(getattr(final_review, "total_files", 0) or 0) <= 0:
            return []
        final_review_index = latest_observation_index(observations, {"final_review"})
        if final_review_index is None:
            return []
        last_change_index = final_review_index

    checks: list[str] = []
    seen: set[str] = set()
    for observation in observations[last_change_index + 1 :]:
        for label in successful_suggested_check_labels(observation, verification_commands):
            if label not in seen:
                checks.append(label)
                seen.add(label)
    return checks


def build_pending_verification_checks(success: bool, observations: list[Observation]) -> list[str]:
    verification_commands, statuses = suggested_check_statuses_after_latest_change(success, observations)
    if not verification_commands:
        return []
    completed_commands = set(statuses)
    return [suggested_check_label(command, cwd) for command, cwd in sorted(verification_commands - completed_commands)]


def build_failed_verification_checks(success: bool, observations: list[Observation]) -> list[str]:
    _, statuses = suggested_check_statuses_after_latest_change(success, observations)
    return [label for _, (passed, label) in sorted(statuses.items()) if not passed]


def suggested_check_statuses_after_latest_change(
    success: bool,
    observations: list[Observation],
) -> tuple[set[tuple[str, str]], dict[tuple[str, str], tuple[bool, str]]]:
    if not success:
        return set(), {}
    final_review = next((observation for observation in reversed(observations) if observation.kind == "final_review"), None)
    if final_review is None:
        return set(), {}
    verification_commands = final_review_verification_commands(final_review)
    if not verification_commands:
        return set(), {}
    last_change_index = latest_successful_verification_invalidating_change_index(observations)
    if last_change_index is None:
        if int(getattr(final_review, "total_files", 0) or 0) <= 0:
            return verification_commands, {}
        final_review_index = latest_observation_index(observations, {"final_review"})
        if final_review_index is None:
            return verification_commands, {}
        last_change_index = final_review_index

    statuses: dict[tuple[str, str], tuple[bool, str]] = {}
    for observation in observations[last_change_index + 1 :]:
        for command, cwd in successful_suggested_check_commands(observation, verification_commands):
            statuses[(command, cwd)] = (True, suggested_check_label(command, cwd))
        for command, cwd, label in failed_suggested_check_results(observation, verification_commands):
            statuses[(command, cwd)] = (False, label)
    return verification_commands, statuses


def final_review_verification_commands(final_review: Observation) -> set[tuple[str, str]]:
    return verification_commands_from_final_review(final_review)


def final_review_suggested_commands(final_review: Observation) -> set[tuple[str, str]]:
    return command_keys_from_objects(getattr(final_review, "suggested_checks", []))


def final_review_focused_test_commands(final_review: Observation) -> set[tuple[str, str]]:
    return command_keys_from_objects(getattr(final_review, "focused_test_commands", []))


def latest_successful_project_change_index(observations: list[Observation]) -> int | None:
    for index in range(len(observations) - 1, -1, -1):
        observation = observations[index]
        if observation.kind in PROJECT_CHANGE_OBSERVATION_KINDS and not observation_failed(observation):
            return index
    return None


def latest_successful_verification_invalidating_change_index(observations: list[Observation]) -> int | None:
    for index in range(len(observations) - 1, -1, -1):
        observation = observations[index]
        if observation.kind in VERIFICATION_INVALIDATING_OBSERVATION_KINDS and not observation_failed(observation):
            return index
    return None


def latest_observation_index(observations: list[Observation], kinds: set[str]) -> int | None:
    for index in range(len(observations) - 1, -1, -1):
        if observations[index].kind in kinds:
            return index
    return None


def observation_runs_suggested_check_successfully(
    observation: Observation,
    suggested_commands: set[tuple[str, str]],
) -> bool:
    return bool(successful_suggested_check_commands(observation, suggested_commands))


def successful_suggested_check_commands(
    observation: Observation,
    suggested_commands: set[tuple[str, str]],
) -> set[tuple[str, str]]:
    if observation.kind == "run_command":
        return command_result_suggested_check_commands(observation.result, suggested_commands)
    if observation.kind in {"run_commands", "run_suggested_checks", "run_focused_test_commands", "run_session_verification"}:
        commands: set[tuple[str, str]] = set()
        for result in observation.results:
            commands.update(command_result_suggested_check_commands(result, suggested_commands))
        return commands
    return set()


def successful_suggested_check_labels(
    observation: Observation,
    suggested_commands: set[tuple[str, str]],
) -> list[str]:
    return [suggested_check_label(command, cwd) for command, cwd in successful_suggested_check_commands(observation, suggested_commands)]


def failed_suggested_check_labels(
    observation: Observation,
    suggested_commands: set[tuple[str, str]],
) -> list[str]:
    return [label for _, _, label in failed_suggested_check_results(observation, suggested_commands)]


def failed_suggested_check_results(
    observation: Observation,
    suggested_commands: set[tuple[str, str]],
) -> list[tuple[str, str, str]]:
    if observation.kind == "run_command":
        result = command_result_failed_suggested_check_result(observation.result, suggested_commands)
        return [result] if result is not None else []
    if observation.kind in {"run_commands", "run_suggested_checks", "run_focused_test_commands", "run_session_verification"}:
        failures: list[tuple[str, str, str]] = []
        for result in observation.results:
            failure = command_result_failed_suggested_check_result(result, suggested_commands)
            if failure is not None:
                failures.append(failure)
        return failures
    return []


def command_result_suggested_check_commands(
    result: object,
    suggested_commands: set[tuple[str, str]],
) -> set[tuple[str, str]]:
    if not command_result_matches_successful_suggested_check(result, suggested_commands):
        return set()
    command = str(getattr(result, "command", ""))
    cwd = str(getattr(result, "cwd", ".") or ".")
    return {(command, cwd)}


def command_result_failed_suggested_check_labels(
    result: object,
    suggested_commands: set[tuple[str, str]],
) -> list[str]:
    failure = command_result_failed_suggested_check_result(result, suggested_commands)
    return [failure[2]] if failure is not None else []


def command_result_failed_suggested_check_result(
    result: object,
    suggested_commands: set[tuple[str, str]],
) -> tuple[str, str, str] | None:
    command = str(getattr(result, "command", ""))
    cwd = str(getattr(result, "cwd", ".") or ".")
    if (command, cwd) not in suggested_commands:
        return None
    if getattr(result, "exit_code", None) == 0 and not getattr(result, "timed_out", False):
        return None
    if getattr(result, "timed_out", False):
        reason = "timed out"
    else:
        exit_code = getattr(result, "exit_code", None)
        reason = f"exit={exit_code}" if exit_code is not None else "no exit code"
    return command, cwd, f"{suggested_check_label(command, cwd)} ({reason})"


def suggested_check_label(command: str, cwd: str) -> str:
    if cwd == ".":
        return command
    return f"{command} (cwd: {cwd})"


def command_result_matches_successful_suggested_check(
    result: object,
    suggested_commands: set[tuple[str, str]],
) -> bool:
    if getattr(result, "exit_code", None) != 0 or getattr(result, "timed_out", False):
        return False
    command = str(getattr(result, "command", ""))
    cwd = str(getattr(result, "cwd", ".") or ".")
    return (command, cwd) in suggested_commands
