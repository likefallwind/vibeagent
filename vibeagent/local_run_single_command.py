from __future__ import annotations

from pathlib import Path

from .local_run_failures import RUN_USAGE, run_failure_report, usage_error
from .local_runtime_execution import execute_local_action
from .local_runtime_reports import (
    format_run_report_text,
    serialize_command_result,
    validate_run_output_context_options,
)
from .types import RunCommandAction
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
        return run_failure_report(
            root,
            message,
            command=command,
            cwd=cwd,
            timeout_ms=timeout_ms,
            max_output_chars=max_output_chars,
        )

    if command is None or not command.strip():
        return failure(RUN_USAGE)
    if timeout_ms < 100:
        return failure(usage_error(RUN_USAGE, "timeout_ms must be at least 100."))
    if timeout_ms > 600_000:
        return failure(usage_error(RUN_USAGE, "timeout_ms must be at most 600000."))
    if max_output_chars < 1_000:
        return failure(usage_error(RUN_USAGE, "max_output_chars must be at least 1000."))
    if max_output_chars > 50_000:
        return failure(usage_error(RUN_USAGE, "max_output_chars must be at most 50000."))
    output_context_error = validate_run_output_context_options(
        context_lines=context_lines,
        max_diagnostics=max_diagnostics,
        max_contexts=max_contexts,
        max_bytes_per_context=max_bytes_per_context,
        usage=RUN_USAGE,
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
