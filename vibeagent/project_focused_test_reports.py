from __future__ import annotations

from typing import Any

from .check_report_helpers import serialize_focused_test_command
from .local_runtime_commands import serialize_command_check


def usage_message(usage: str, message: object) -> str:
    return f"{usage}\n  message: {message}"


def usage_error(usage: str, error: object) -> str:
    return f"{usage}\nError: {error}"


def empty_related_tests_report(project_root: str, message: str) -> dict[str, object]:
    return {
        "projectRoot": project_root,
        "ok": False,
        "targetPaths": [],
        "testFiles": 0,
        "candidates": {"shown": 0, "total": 0, "items": []},
        "truncated": False,
        "message": message,
    }


def empty_focused_test_commands_report(project_root: str, message: str) -> dict[str, object]:
    return {
        "projectRoot": project_root,
        "ok": False,
        "targetPaths": [],
        "relatedTests": {"total": 0},
        "commands": {"shown": 0, "total": 0, "items": []},
        "truncated": False,
        "message": message,
    }


def empty_check_focused_test_commands_report(
    project_root: str,
    message: str,
    *,
    max_commands: int,
) -> dict[str, object]:
    return {
        "projectRoot": project_root,
        "ok": False,
        "targetPaths": [],
        "relatedTests": {"total": 0},
        "focusedCommands": {"shown": 0, "total": 0, "max": max_commands, "items": []},
        "truncated": False,
        "checks": [],
        "message": message,
    }


def empty_run_focused_test_commands_report(
    project_root: str,
    message: str,
    *,
    max_commands: int,
    stop_on_failure: bool,
) -> dict[str, object]:
    return {
        "projectRoot": project_root,
        "ok": False,
        "clean": False,
        "targetPaths": [],
        "relatedTests": {"total": 0},
        "focusedCommands": {"shown": 0, "total": 0, "max": max_commands, "items": []},
        "ran": 0,
        "skippedUnavailable": 0,
        "truncated": False,
        "stopOnFailure": stop_on_failure,
        "stoppedEarly": False,
        "selectedCommandsNotRun": {"count": 0, "items": []},
        "results": [],
        "message": message,
    }


def serialize_related_test_candidates(candidates: list[Any]) -> list[dict[str, object]]:
    return [
        {
            "source": candidate.source_path,
            "test": candidate.test_path,
            "score": candidate.score,
            "reason": candidate.reason,
        }
        for candidate in candidates
    ]


def serialize_focused_test_command_items(commands: list[Any]) -> list[dict[str, object]]:
    return [
        serialize_focused_test_command(command, index=index)
        for index, command in enumerate(commands, start=1)
    ]


def serialize_command_check_items(checks: list[Any]) -> list[dict[str, object]]:
    return [
        serialize_command_check(check, index=index)
        for index, check in enumerate(checks, start=1)
    ]
