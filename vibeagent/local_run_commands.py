from __future__ import annotations

from pathlib import Path

from .local_runtime_execution import execute_local_action
from .local_runtime_reports import (
    command_results_clean,
    empty_command_output_analysis,
    format_check_run_sequence_report_text,
    format_run_report_text,
    format_run_sequence_report_text,
    serialize_command_check,
    serialize_command_result,
    sum_command_result_duration_ms,
    validate_run_output_context_options,
)
from .types import CheckRunCommandsAction, RunCommandAction, RunCommandItem, RunCommandsAction
from .workspace_core import create_local_workspace


def get_run_text(
    project_root: str | Path = ".",
    command: str | None = None,
    cwd: str | None = None,
    timeout_ms: int = 30_000,
    max_output_chars: int = 12_000,
    extract_output_contexts: bool = False,
    extract_output_diagnostics: bool = False,
    context_lines: int = 5,
    max_diagnostics: int = 50,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
) -> str:
    return format_run_report_text(
        get_run_report(
            project_root,
            command,
            cwd=cwd,
            timeout_ms=timeout_ms,
            max_output_chars=max_output_chars,
            extract_output_contexts=extract_output_contexts,
            extract_output_diagnostics=extract_output_diagnostics,
            context_lines=context_lines,
            max_diagnostics=max_diagnostics,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        )
    )


def get_run_report(
    project_root: str | Path = ".",
    command: str | None = None,
    cwd: str | None = None,
    timeout_ms: int = 30_000,
    max_output_chars: int = 12_000,
    extract_output_contexts: bool = False,
    extract_output_diagnostics: bool = False,
    context_lines: int = 5,
    max_diagnostics: int = 50,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
) -> dict[str, object]:
    root = Path(project_root).resolve()

    def failure(message: str) -> dict[str, object]:
        return {
            "projectRoot": str(root),
            "ok": False,
            "command": (command or "").strip(),
            "cwd": cwd or ".",
            "exitCode": None,
            "timedOut": False,
            "signal": None,
            "sandboxed": False,
            "sandboxWarning": None,
            "timeoutMs": timeout_ms,
            "maxOutputChars": max_output_chars,
            "stdout": "",
            "stderr": "",
            "stdoutTruncated": False,
            "stderrTruncated": False,
            "analysis": empty_command_output_analysis(),
            "message": message,
        }

    if command is None or not command.strip():
        return failure("Usage: /run <shell command>")
    if timeout_ms < 100:
        return failure("Usage: /run <shell command>\nError: timeout_ms must be at least 100.")
    if timeout_ms > 600_000:
        return failure("Usage: /run <shell command>\nError: timeout_ms must be at most 600000.")
    if max_output_chars < 1_000:
        return failure("Usage: /run <shell command>\nError: max_output_chars must be at least 1000.")
    if max_output_chars > 50_000:
        return failure("Usage: /run <shell command>\nError: max_output_chars must be at most 50000.")
    output_context_error = validate_run_output_context_options(
        context_lines=context_lines,
        max_diagnostics=max_diagnostics,
        max_contexts=max_contexts,
        max_bytes_per_context=max_bytes_per_context,
        usage="Usage: /run <shell command>",
    )
    if output_context_error:
        return failure(output_context_error)

    workspace = create_local_workspace(root, "local-run")
    observation = execute_local_action(
        workspace,
        RunCommandAction(
            type="run_command",
            command=command.strip(),
            timeout_ms=timeout_ms,
            cwd=cwd,
            max_output_chars=max_output_chars,
            extract_output_contexts=extract_output_contexts,
            extract_output_diagnostics=extract_output_diagnostics,
            context_lines=context_lines,
            max_diagnostics=max_diagnostics,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        ),
        command_timeout_ms=timeout_ms,
    )
    if observation.kind != "run_command":
        return failure(f"Unexpected observation: {observation.kind}")
    result = observation.result
    ok = result.exit_code == 0 and not result.timed_out
    return {
        "projectRoot": str(root),
        **serialize_command_result(result),
        "message": "Command completed." if ok else "Command failed.",
    }


def get_run_sequence_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    commands: list[str] | None = None,
    cwd: str | None = None,
    timeout_ms: int = 30_000,
    max_output_chars: int = 12_000,
    stop_on_failure: bool = True,
    extract_output_contexts: bool = False,
    extract_output_diagnostics: bool = False,
    context_lines: int = 5,
    max_diagnostics: int = 50,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
) -> str:
    return format_run_sequence_report_text(
        get_run_sequence_report(
            project_root,
            argument,
            commands=commands,
            cwd=cwd,
            timeout_ms=timeout_ms,
            max_output_chars=max_output_chars,
            stop_on_failure=stop_on_failure,
            extract_output_contexts=extract_output_contexts,
            extract_output_diagnostics=extract_output_diagnostics,
            context_lines=context_lines,
            max_diagnostics=max_diagnostics,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        )
    )


def get_run_sequence_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    commands: list[str] | None = None,
    cwd: str | None = None,
    timeout_ms: int = 30_000,
    max_output_chars: int = 12_000,
    stop_on_failure: bool = True,
    extract_output_contexts: bool = False,
    extract_output_diagnostics: bool = False,
    context_lines: int = 5,
    max_diagnostics: int = 50,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
) -> dict[str, object]:
    root = Path(project_root).resolve()

    def failure(message: str, selected_commands: list[str] | None = None) -> dict[str, object]:
        selected = list(selected_commands or [])
        return {
            "projectRoot": str(root),
            "ok": False,
            "clean": False,
            "commands": {"shown": 0, "total": len(selected), "requested": selected},
            "stopOnFailure": stop_on_failure,
            "stoppedEarly": False,
            "results": [],
            "message": message,
        }

    try:
        selected_commands = parse_run_sequence_request(argument, commands)
    except ValueError as error:
        return failure(f"Usage: /run-seq <cmd> ;; <cmd>\nError: {error}")
    if timeout_ms < 100:
        return failure("Usage: /run-seq <cmd> ;; <cmd>\nError: timeout_ms must be at least 100.", selected_commands)
    if timeout_ms > 600_000:
        return failure("Usage: /run-seq <cmd> ;; <cmd>\nError: timeout_ms must be at most 600000.", selected_commands)
    if max_output_chars < 1_000:
        return failure("Usage: /run-seq <cmd> ;; <cmd>\nError: max_output_chars must be at least 1000.", selected_commands)
    if max_output_chars > 50_000:
        return failure("Usage: /run-seq <cmd> ;; <cmd>\nError: max_output_chars must be at most 50000.", selected_commands)
    output_context_error = validate_run_output_context_options(
        context_lines=context_lines,
        max_diagnostics=max_diagnostics,
        max_contexts=max_contexts,
        max_bytes_per_context=max_bytes_per_context,
        usage="Usage: /run-seq <cmd> ;; <cmd>",
    )
    if output_context_error:
        return failure(output_context_error, selected_commands)

    workspace = create_local_workspace(root, "local-run-sequence")
    observation = execute_local_action(
        workspace,
        RunCommandsAction(
            type="run_commands",
            commands=[
                RunCommandItem(
                    command=command,
                    cwd=cwd,
                    timeout_ms=timeout_ms,
                    max_output_chars=max_output_chars,
                    extract_output_contexts=extract_output_contexts,
                    extract_output_diagnostics=extract_output_diagnostics,
                    context_lines=context_lines,
                    max_diagnostics=max_diagnostics,
                    max_contexts=max_contexts,
                    max_bytes_per_context=max_bytes_per_context,
                )
                for command in selected_commands
            ],
            stop_on_failure=stop_on_failure,
        ),
        command_timeout_ms=timeout_ms,
    )
    if observation.kind != "run_commands":
        return failure(f"Unexpected observation: {observation.kind}", selected_commands)

    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "clean": observation.ok and command_results_clean(list(observation.results)),
        "commands": {
            "shown": len(observation.results),
            "total": len(selected_commands),
            "requested": selected_commands,
        },
        "stopOnFailure": stop_on_failure,
        "stoppedEarly": observation.stopped_early,
        "durationMs": sum_command_result_duration_ms(list(observation.results)),
        "results": [serialize_command_result(result, index=index) for index, result in enumerate(observation.results, start=1)],
        "message": observation.message,
    }


def parse_run_sequence_request(argument: str | None = None, commands: list[str] | None = None) -> list[str]:
    if argument and commands is not None:
        raise ValueError("run-seq argument cannot be combined with explicit commands.")
    if commands is not None:
        selected = [command.strip() for command in commands if command.strip()]
    elif argument and argument.strip():
        selected = [part.strip() for part in argument.split(";;") if part.strip()]
    else:
        selected = []
    if not selected:
        raise ValueError("at least one command is required.")
    if len(selected) > 10:
        raise ValueError("expected at most 10 commands.")
    return selected


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
        selected = list(selected_commands or [])
        return {
            "projectRoot": str(root),
            "ok": False,
            "commands": {"shown": 0, "total": len(selected), "requested": selected},
            "checks": [],
            "message": message,
        }

    try:
        selected_commands = parse_run_sequence_request(argument, commands)
    except ValueError as error:
        return failure(f"Usage: /check-run-seq <cmd> ;; <cmd>\nError: {error}")

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
