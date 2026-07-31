from __future__ import annotations

from .process_runtime import execute_run_command_item
from .types import CommandResult, RunCommandItem, RunFocusedTestCommandsAction, RunSuggestedChecksAction


def run_project_check_command(
    workspace,
    command: str,
    cwd: str,
    action: RunSuggestedChecksAction | RunFocusedTestCommandsAction,
    command_timeout_ms: int,
) -> CommandResult:
    return execute_run_command_item(
        workspace,
        RunCommandItem(
            command=command,
            cwd=cwd,
            timeout_ms=action.timeout_ms,
            max_output_chars=action.max_output_chars,
            extract_output_contexts=action.extract_output_contexts,
            extract_output_diagnostics=action.extract_output_diagnostics,
            context_lines=action.context_lines,
            max_diagnostics=action.max_diagnostics,
            max_contexts=action.max_contexts,
            max_bytes_per_context=action.max_bytes_per_context,
        ),
        command_timeout_ms,
    )
