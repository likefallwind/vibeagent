from __future__ import annotations

from typing import Any

from .session import read_session_events
from .session_failure_reports import command_result_failed
from .session_verification_state import (
    SESSION_PROJECT_CHANGE_RESULT_KINDS as PROJECT_CHANGE_RESULT_KINDS,
    command_result_has_source_output_issues,
    session_command_result_key,
    session_failed_suggested_check_label,
    session_iter_command_results,
)
from .types import FocusedTestCommand, SuggestedCheck
from .verification_command_utils import verification_command_label, verification_commands_from_objects
from .workspace_core import RunWorkspace


def final_review_session_verification_issues(
    workspace: RunWorkspace,
    suggested_checks: list[SuggestedCheck],
    focused_test_commands: list[FocusedTestCommand] | None = None,
) -> tuple[list[str], list[str]]:
    verification_commands = verification_commands_from_objects(suggested_checks, focused_test_commands or [])
    if not verification_commands:
        return [], []

    events = read_session_events(workspace.root, workspace.run_id)
    last_change_index = latest_successful_project_change_event_index(events)
    if last_change_index is None:
        return [], []

    statuses: dict[tuple[str, str], tuple[bool, str]] = {}
    stopped_not_run_labels: list[str] = []
    for event in events[last_change_index + 1 :]:
        result = event.payload.get("result") if not event.malformed and event.type == "tool_result" else None
        if not isinstance(result, dict):
            continue
        if result.get("kind") == "run_session_verification":
            stopped_not_run_labels = final_review_stopped_session_verification_labels(
                result,
                verification_commands,
            )
        for command_result in session_iter_command_results(result):
            key = session_command_result_key(command_result)
            if key not in verification_commands:
                continue
            passed = (
                not command_result_failed(command_result)
                and not command_result_has_source_output_issues(command_result)
            )
            label = suggested_check_label(*key) if passed else session_failed_suggested_check_label(command_result)
            statuses[key] = (passed, label)

    verified_commands = {key for key, (passed, _) in statuses.items() if passed}
    failed_labels = [label for _, (passed, label) in sorted(statuses.items()) if not passed]
    failed_commands = {key for key, (passed, _) in statuses.items() if not passed}
    pending_labels = [
        suggested_check_label(command, cwd)
        for command, cwd in sorted(verification_commands - verified_commands - failed_commands)
    ]
    blockers: list[str] = []
    warnings: list[str] = []
    if failed_labels:
        blockers.append("Suggested verification checks failed after the latest project change.")
        warnings.append("Failed suggested check(s): " + ", ".join(failed_labels[:5]) + ".")
    if pending_labels:
        blockers.append("Suggested verification checks are still pending after the latest project change.")
        warnings.append("Pending suggested check(s): " + ", ".join(pending_labels[:5]) + ".")
    if stopped_not_run_labels:
        warnings.append(
            "Session verification stopped before running selected check(s): "
            + ", ".join(stopped_not_run_labels[:5])
            + "."
        )
    return blockers, warnings


def final_review_stopped_session_verification_labels(
    result: dict[str, Any],
    verification_commands: set[tuple[str, str]],
) -> list[str]:
    if not bool(result.get("stopped_early") or result.get("stoppedEarly")):
        return []
    selected = result.get("selected_commands")
    if not isinstance(selected, list):
        selected = result.get("selectedCommands")
    results = result.get("results")
    if not isinstance(selected, list) or not isinstance(results, list):
        return []

    labels: list[str] = []
    ran_count = len([item for item in results if isinstance(item, dict)])
    for item in selected[ran_count:]:
        if not isinstance(item, dict):
            continue
        command = item.get("command")
        cwd = item.get("cwd") or "."
        if not isinstance(command, str) or not command.strip():
            continue
        command = command.strip()
        cwd = cwd.strip() if isinstance(cwd, str) and cwd.strip() else "."
        key = (command, cwd)
        if key not in verification_commands:
            continue
        status = str(item.get("status") or item.get("sourceStatus") or "").strip()
        label = suggested_check_label(command, cwd)
        labels.append(f"{label}: {status}" if status else label)
    return labels


def latest_successful_project_change_event_index(events: list[Any]) -> int | None:
    for index in range(len(events) - 1, -1, -1):
        event = events[index]
        if event.malformed or event.type != "tool_result":
            continue
        result = event.payload.get("result")
        if not isinstance(result, dict):
            continue
        if result.get("kind") in PROJECT_CHANGE_RESULT_KINDS and result.get("ok") is not False:
            return index
    return None


def suggested_check_label(command: str, cwd: str) -> str:
    return verification_command_label(command, cwd)
