from __future__ import annotations

from pathlib import Path

from .actions import execute_action
from .project_focused_test_validation import parse_related_tests_argument
from .project_focused_test_reports import (
    empty_check_focused_test_commands_report,
    empty_focused_test_commands_report,
    empty_related_tests_report,
    serialize_command_check_items,
    serialize_focused_test_command_items,
    serialize_related_test_candidates,
    usage_message,
)
from .project_run_focused_test_commands import (
    get_run_focused_test_commands_report,
    get_run_focused_test_commands_text,
)
from .project_test_formatting import (
    format_check_focused_test_commands_report_text,
    format_focused_test_commands_report_text,
    format_related_tests_report_text,
)
from .types import (
    CheckFocusedTestCommandsAction,
    FocusedTestCommandsAction,
    RelatedTestsAction,
)
from .workspace_core import create_local_workspace

RELATED_TESTS_USAGE = "Usage: /related-tests [path...]"
FOCUSED_TESTS_USAGE = "Usage: /focused-tests [path...]"
CHECK_FOCUSED_TESTS_USAGE = "Usage: /check-focused-tests [path...]"


def get_related_tests_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    max_paths: int = 100,
    max_candidates: int = 200,
) -> str:
    return format_related_tests_report_text(
        get_related_tests_report(project_root, argument, max_paths=max_paths, max_candidates=max_candidates)
    )


def get_related_tests_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    max_paths: int = 100,
    max_candidates: int = 200,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        paths = parse_related_tests_argument(argument)
    except ValueError as error:
        return empty_related_tests_report(str(root), usage_message(RELATED_TESTS_USAGE, error))

    workspace = create_local_workspace(root, "local-related-tests")
    observation = execute_action(
        workspace,
        RelatedTestsAction(
            type="related_tests",
            paths=paths,
            max_paths=max_paths,
            max_candidates=max_candidates,
        ),
    )
    if observation.kind != "related_tests":
        return empty_related_tests_report(str(root), f"Unexpected observation: {observation.kind}")

    candidates = serialize_related_test_candidates(list(observation.candidates))
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "targetPaths": list(observation.target_paths),
        "testFiles": observation.test_files_total,
        "candidates": {
            "shown": len(candidates),
            "total": observation.total,
            "items": candidates,
        },
        "truncated": observation.truncated,
        "message": observation.message,
    }


def get_focused_test_commands_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    max_paths: int = 100,
    max_candidates: int = 200,
    max_commands: int = 50,
) -> str:
    return format_focused_test_commands_report_text(
        get_focused_test_commands_report(
            project_root,
            argument,
            max_paths=max_paths,
            max_candidates=max_candidates,
            max_commands=max_commands,
        )
    )


def get_focused_test_commands_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    max_paths: int = 100,
    max_candidates: int = 200,
    max_commands: int = 50,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        paths = parse_related_tests_argument(argument)
    except ValueError as error:
        return empty_focused_test_commands_report(str(root), usage_message(FOCUSED_TESTS_USAGE, error))

    workspace = create_local_workspace(root, "local-focused-tests")
    observation = execute_action(
        workspace,
        FocusedTestCommandsAction(
            type="focused_test_commands",
            paths=paths,
            max_paths=max_paths,
            max_candidates=max_candidates,
            max_commands=max_commands,
        ),
    )
    if observation.kind != "focused_test_commands":
        return empty_focused_test_commands_report(str(root), f"Unexpected observation: {observation.kind}")

    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "targetPaths": list(observation.target_paths),
        "relatedTests": {"total": observation.related_tests_total},
        "commands": {
            "shown": len(observation.commands),
            "total": observation.total,
            "items": serialize_focused_test_command_items(list(observation.commands)),
        },
        "truncated": observation.truncated,
        "message": observation.message,
    }


def get_check_focused_test_commands_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    max_paths: int = 100,
    max_candidates: int = 200,
    max_commands: int = 10,
) -> str:
    return format_check_focused_test_commands_report_text(
        get_check_focused_test_commands_report(
            project_root,
            argument,
            max_paths=max_paths,
            max_candidates=max_candidates,
            max_commands=max_commands,
        )
    )


def get_check_focused_test_commands_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    max_paths: int = 100,
    max_candidates: int = 200,
    max_commands: int = 10,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        paths = parse_related_tests_argument(argument)
    except ValueError as error:
        return empty_check_focused_test_commands_report(
            str(root),
            usage_message(CHECK_FOCUSED_TESTS_USAGE, error),
            max_commands=max_commands,
        )

    workspace = create_local_workspace(root, "local-check-focused-tests")
    observation = execute_action(
        workspace,
        CheckFocusedTestCommandsAction(
            type="check_focused_test_commands",
            paths=paths,
            max_paths=max_paths,
            max_candidates=max_candidates,
            max_commands=max_commands,
        ),
    )
    if observation.kind != "check_focused_test_commands":
        return empty_check_focused_test_commands_report(
            str(root),
            f"Unexpected observation: {observation.kind}",
            max_commands=max_commands,
        )

    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "targetPaths": list(observation.target_paths),
        "relatedTests": {"total": observation.related_tests_total},
        "focusedCommands": {
            "shown": len(observation.focused_commands),
            "total": observation.total,
            "max": observation.max_commands,
            "items": serialize_focused_test_command_items(list(observation.focused_commands)),
        },
        "truncated": observation.truncated,
        "checks": serialize_command_check_items(list(observation.checks)),
        "message": observation.message,
    }
