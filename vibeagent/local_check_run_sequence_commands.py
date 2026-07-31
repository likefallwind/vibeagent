from __future__ import annotations

from pathlib import Path

from .local_run_failures import CHECK_RUN_SEQUENCE_USAGE, check_run_sequence_failure_report, usage_error
from .local_run_sequence_commands import parse_run_sequence_request
from .local_runtime_execution import execute_local_action
from .local_runtime_reports import format_check_run_sequence_report_text, serialize_command_check
from .types import CheckRunCommandsAction, RunCommandItem
from .workspace_core import create_local_workspace


def get_check_run_sequence_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    commands: list[str] | None = None,
    cwd: str | None = None,
) -> str:
    return format_check_run_sequence_report_text(
        get_check_run_sequence_report(project_root, argument, commands=commands, cwd=cwd)
    )


def get_check_run_sequence_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    commands: list[str] | None = None,
    cwd: str | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()

    def failure(message: str, selected_commands: list[str] | None = None) -> dict[str, object]:
        return check_run_sequence_failure_report(root, message, selected_commands=selected_commands)

    try:
        selected_commands = parse_run_sequence_request(argument, commands)
    except ValueError as error:
        return failure(usage_error(CHECK_RUN_SEQUENCE_USAGE, error))

    workspace = create_local_workspace(root, "local-check-run-sequence")
    observation = execute_local_action(
        workspace,
        CheckRunCommandsAction(
            type="check_run_commands",
            commands=[RunCommandItem(command=command, cwd=cwd) for command in selected_commands],
        ),
    )
    if observation.kind != "check_run_commands":
        return failure(f"Unexpected observation: {observation.kind}", selected_commands)

    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "commands": {
            "shown": len(observation.checks),
            "total": len(selected_commands),
            "requested": selected_commands,
        },
        "checks": [serialize_command_check(check, index=index) for index, check in enumerate(observation.checks, start=1)],
        "message": observation.message,
    }
