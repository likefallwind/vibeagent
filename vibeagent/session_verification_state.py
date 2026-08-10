from __future__ import annotations

from typing import Any

from .agent_completion_kinds import PROJECT_CHANGE_OBSERVATION_KINDS, VCS_METADATA_OBSERVATION_KINDS
from .session_failure_reports import command_result_failed
from .session_types import SessionEvent
from .verification_command_utils import (
    command_keys_from_dicts,
    failed_verification_command_label,
    matching_verification_command_key,
    verification_command_label,
    verification_commands_from_final_review_payload,
)


SESSION_PROJECT_CHANGE_RESULT_KINDS = PROJECT_CHANGE_OBSERVATION_KINDS


SESSION_VERIFICATION_INVALIDATING_RESULT_KINDS = SESSION_PROJECT_CHANGE_RESULT_KINDS - VCS_METADATA_OBSERVATION_KINDS


def session_verification_from_events(events: list[SessionEvent]) -> tuple[list[str], list[str], list[str]]:
    verification_commands: set[tuple[str, str]] = set()
    last_change_index: int | None = None
    final_review_index: int | None = None
    for index, event in enumerate(events):
        if event.malformed or event.type != "tool_result":
            continue
        result = event.payload.get("result")
        if not isinstance(result, dict):
            continue
        kind = result.get("kind")
        if kind == "final_review":
            verification_commands = session_final_review_verification_commands(result)
            final_review_index = index
        if kind in SESSION_VERIFICATION_INVALIDATING_RESULT_KINDS and result.get("ok") is not False:
            last_change_index = index

    if last_change_index is None:
        return [], [], []
    if final_review_index is None or final_review_index < last_change_index:
        verification_commands = set()

    statuses: dict[tuple[str, str], tuple[bool, str]] = {}
    for event in events[last_change_index + 1 :]:
        if event.malformed or event.type != "tool_result":
            continue
        result = event.payload.get("result")
        if not isinstance(result, dict):
            continue
        verification_commands.update(session_run_verification_selected_command_keys(result))
        for command_result in session_iter_command_results(result):
            result_key = session_command_result_key(command_result)
            key = matching_verification_command_key(result_key[0], result_key[1], verification_commands)
            if key is None:
                continue
            if command_result_failed(command_result) or command_result_has_source_output_issues(command_result):
                statuses[key] = (False, session_failed_suggested_check_label(command_result))
            else:
                statuses[key] = (True, session_suggested_check_label(*key))

    if not verification_commands:
        return [], [], []

    verified = [label for _, (passed, label) in sorted(statuses.items()) if passed]
    failed_checks = [label for _, (passed, label) in sorted(statuses.items()) if not passed]
    completed_commands = set(statuses)
    pending = [
        session_suggested_check_label(command, cwd)
        for command, cwd in sorted(verification_commands - completed_commands)
    ]
    return verified, pending, failed_checks


def session_final_review_verification_commands(result: dict[str, Any]) -> set[tuple[str, str]]:
    return verification_commands_from_final_review_payload(result)


def session_final_review_suggested_commands(result: dict[str, Any]) -> set[tuple[str, str]]:
    return command_keys_from_dicts(result.get("suggested_checks"))


def session_final_review_focused_test_commands(result: dict[str, Any]) -> set[tuple[str, str]]:
    return command_keys_from_dicts(result.get("focused_test_commands"))


def session_run_verification_selected_command_keys(result: dict[str, Any]) -> set[tuple[str, str]]:
    if result.get("kind") != "run_session_verification":
        return set()
    selected = result.get("selected_commands")
    if not isinstance(selected, list):
        selected = result.get("selectedCommands")
    return command_keys_from_dicts(selected)


def session_iter_command_results(result: dict[str, Any]) -> list[dict[str, Any]]:
    kind = result.get("kind")
    if kind == "run_command":
        command_result = result.get("result")
        return [command_result] if isinstance(command_result, dict) else []
    if kind in {"run_commands", "run_suggested_checks", "run_focused_test_commands", "run_session_verification"}:
        command_results = result.get("results")
        if isinstance(command_results, list):
            return [item for item in command_results if isinstance(item, dict)]
    return []


def session_command_result_key(result: dict[str, Any]) -> tuple[str, str]:
    command = result.get("command")
    cwd = result.get("cwd")
    return (command if isinstance(command, str) else "", cwd if isinstance(cwd, str) and cwd else ".")


def session_suggested_check_label(command: str, cwd: str) -> str:
    return verification_command_label(command, cwd)


def session_failed_suggested_check_label(result: dict[str, Any]) -> str:
    command, cwd = session_command_result_key(result)
    if result.get("timed_out") is True:
        reason = "timed out"
    elif result.get("exit_code") != 0:
        exit_code = result.get("exit_code")
        reason = f"exit={exit_code}" if isinstance(exit_code, int) else "no exit code"
    elif command_result_has_source_output_issues(result):
        reason = "output diagnostics"
    else:
        reason = "no exit code"
    return failed_verification_command_label(command, cwd, reason)


def command_result_has_source_output_issues(result: dict[str, Any]) -> bool:
    diagnostics = result.get("output_diagnostics")
    if isinstance(diagnostics, list):
        for diagnostic in diagnostics:
            if isinstance(diagnostic, dict) and isinstance(diagnostic.get("path"), str) and diagnostic["path"].strip():
                return True
    contexts = result.get("output_contexts")
    if isinstance(contexts, list):
        for context in contexts:
            if isinstance(context, dict) and isinstance(context.get("path"), str) and context["path"].strip():
                return True
    return False
