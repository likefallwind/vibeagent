from __future__ import annotations

from typing import Any

from .session_failure_reports import command_result_failed
from .session_types import SessionEvent
from .verification_command_utils import command_keys_from_dicts, verification_commands_from_final_review_payload


SESSION_PROJECT_CHANGE_RESULT_KINDS = {
    "write_file",
    "write_files",
    "edit_file",
    "multi_edit_file",
    "replace_python_definition",
    "code_rename",
    "python_rename",
    "replace_lines",
    "insert_lines",
    "append_file",
    "regex_replace",
    "json_set",
    "json_remove",
    "json_patch",
    "patch_file",
    "patch_files",
    "delete_file",
    "delete_files",
    "move_file",
    "move_files",
    "copy_file",
    "copy_files",
    "move_dir",
    "move_dirs",
    "copy_dir",
    "copy_dirs",
    "create_dir",
    "create_dirs",
    "delete_empty_dir",
    "delete_empty_dirs",
    "set_executable",
    "git_stage",
    "git_unstage",
    "git_commit",
    "git_restore",
    "checkpoint_restore",
}


def session_verification_from_events(events: list[SessionEvent]) -> tuple[list[str], list[str], list[str]]:
    verification_commands: set[tuple[str, str]] = set()
    last_change_index: int | None = None
    for index, event in enumerate(events):
        if event.malformed or event.type != "tool_result":
            continue
        result = event.payload.get("result")
        if not isinstance(result, dict):
            continue
        kind = result.get("kind")
        if kind == "final_review":
            verification_commands = session_final_review_verification_commands(result)
        if kind in SESSION_PROJECT_CHANGE_RESULT_KINDS and result.get("ok") is not False:
            last_change_index = index

    if not verification_commands or last_change_index is None:
        return [], [], []

    statuses: dict[tuple[str, str], tuple[bool, str]] = {}
    for event in events[last_change_index + 1 :]:
        if event.malformed or event.type != "tool_result":
            continue
        result = event.payload.get("result")
        if not isinstance(result, dict):
            continue
        for command_result in session_iter_command_results(result):
            key = session_command_result_key(command_result)
            if key not in verification_commands:
                continue
            if command_result_failed(command_result):
                statuses[key] = (False, session_failed_suggested_check_label(command_result))
            else:
                statuses[key] = (True, session_suggested_check_label(*key))

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


def session_iter_command_results(result: dict[str, Any]) -> list[dict[str, Any]]:
    kind = result.get("kind")
    if kind == "run_command":
        command_result = result.get("result")
        return [command_result] if isinstance(command_result, dict) else []
    if kind in {"run_commands", "run_suggested_checks", "run_focused_test_commands"}:
        command_results = result.get("results")
        if isinstance(command_results, list):
            return [item for item in command_results if isinstance(item, dict)]
    return []


def session_command_result_key(result: dict[str, Any]) -> tuple[str, str]:
    command = result.get("command")
    cwd = result.get("cwd")
    return (command if isinstance(command, str) else "", cwd if isinstance(cwd, str) and cwd else ".")


def session_suggested_check_label(command: str, cwd: str) -> str:
    return command if cwd == "." else f"{command} (cwd: {cwd})"


def session_failed_suggested_check_label(result: dict[str, Any]) -> str:
    command, cwd = session_command_result_key(result)
    if result.get("timed_out") is True:
        reason = "timed out"
    else:
        exit_code = result.get("exit_code")
        reason = f"exit={exit_code}" if isinstance(exit_code, int) else "no exit code"
    return f"{session_suggested_check_label(command, cwd)} ({reason})"
