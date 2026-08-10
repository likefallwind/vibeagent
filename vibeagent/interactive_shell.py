from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from .agent_runtime_utils import append_session_event
from .agent_tool_results import record_tool_result_event
from .local_runtime_execution import execute_local_action
from .types import CommandResult, RunCommandAction, RunCommandObservation
from .workspace_core import create_run_workspace


SHELL_MODE_USAGE = "Usage: ! <cmd>"


@dataclass(frozen=True)
class InteractiveShellResult:
    run_id: str
    text: str
    result: CommandResult


def parse_shell_mode_input(value: str) -> str | None:
    if not value.startswith("!"):
        return None
    return value[1:].strip()


def run_interactive_shell(
    project_root: str | Path,
    command: str,
    *,
    run_id: str | None = None,
    timeout_ms: int = 30_000,
    max_output_chars: int = 12_000,
) -> InteractiveShellResult:
    selected_command = command.strip()
    if not selected_command:
        raise ValueError(SHELL_MODE_USAGE)

    workspace = create_run_workspace(project_root, run_id)
    tool_id = f"interactive-shell-{uuid4().hex[:12]}"
    append_session_event(
        workspace.session_dir,
        "tool_call",
        {
            "iteration": 0,
            "id": tool_id,
            "name": "Bash",
            "input": {"command": selected_command},
            "source": "interactive_shell",
        },
    )
    observation = execute_local_action(
        workspace,
        RunCommandAction(
            type="run_command",
            command=selected_command,
            timeout_ms=timeout_ms,
            max_output_chars=max_output_chars,
            maintain_cwd=True,
        ),
        command_timeout_ms=timeout_ms,
    )
    if not isinstance(observation, RunCommandObservation):
        raise RuntimeError(f"Unexpected shell observation: {getattr(observation, 'kind', 'unknown')}")
    record_tool_result_event(
        workspace,
        tool_id=tool_id,
        tool_name="Bash",
        observation=observation,
        iteration=0,
        event_extra={"source": "interactive_shell"},
    )
    return InteractiveShellResult(
        run_id=workspace.run_id,
        text=format_interactive_shell_result(observation.result),
        result=observation.result,
    )


def format_interactive_shell_result(result: CommandResult) -> str:
    sections: list[str] = []
    if result.stdout:
        sections.append(result.stdout.rstrip("\n"))
    if result.stderr:
        sections.append(result.stderr.rstrip("\n"))
    if result.stdout_truncated or result.stderr_truncated:
        sections.append("[output truncated]")
    if result.sandbox_warning:
        sections.append(f"[sandbox warning: {result.sandbox_warning}]")

    if result.timed_out:
        sections.append(f"[timed out after {result.timeout_ms} ms]")
    elif result.exit_code is None:
        sections.append("[command not run]")
    elif result.exit_code != 0:
        suffix = f", signal {result.signal}" if result.signal else ""
        sections.append(f"[exit {result.exit_code}{suffix}]")
    elif not sections:
        sections.append("[exit 0]")
    return "\n".join(sections)


__all__ = [
    "InteractiveShellResult",
    "SHELL_MODE_USAGE",
    "format_interactive_shell_result",
    "parse_shell_mode_input",
    "run_interactive_shell",
]
