from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .config import resolve_execution_config
from .interactive_shell import SHELL_MODE_USAGE, parse_shell_mode_input, run_interactive_shell
from .workspace_core import RunWorkspace, create_local_workspace
from .workspace_shell_response import resolve_respond_to_bash_commands


SHELL_RESPONSE_TASK = (
    "Review the interactive shell command and its recorded output in "
    "the prior session context. Respond with the appropriate next "
    "coding action or explanation. Do not rerun the command unless needed."
)


@dataclass(frozen=True)
class InteractiveShellTurnRequest:
    project_root: Path
    task: str
    resume_run_id: str | None
    resume_context: str | None
    pending_workspace: RunWorkspace | None
    additional_directories: tuple[Path, ...]
    safe_mode: bool
    bare_mode: bool
    setting_sources: tuple[str, ...]
    settings_override_json: str | None
    invocation_plugin_dirs: tuple[Path, ...]


@dataclass(frozen=True)
class InteractiveShellTurnResult:
    task: str
    task_metadata: dict[str, object] | None
    resume_run_id: str | None
    resume_context: str | None
    output: str
    continue_loop: bool


def run_interactive_shell_turn(
    request: InteractiveShellTurnRequest,
    *,
    get_resume_context: Callable[[str], tuple[str | None, str | None, str]],
) -> InteractiveShellTurnResult | None:
    shell_command = parse_shell_mode_input(request.task)
    if shell_command is None:
        return None
    if not shell_command:
        return _result(request, output=SHELL_MODE_USAGE, continue_loop=True)

    settings_workspace = request.pending_workspace or create_local_workspace(
        request.project_root,
        request.resume_run_id or "interactive-shell-settings",
        additional_roots=request.additional_directories,
        safe_mode=request.safe_mode,
        bare_mode=request.bare_mode,
        setting_sources=request.setting_sources,
        settings_override_json=request.settings_override_json,
        invocation_plugin_dirs=request.invocation_plugin_dirs,
    )
    respond_to_shell = resolve_respond_to_bash_commands(settings_workspace)
    shell_result = run_interactive_shell(
        request.project_root,
        shell_command,
        run_id=request.resume_run_id,
        timeout_ms=resolve_execution_config(request.project_root).command_timeout_ms,
    )
    selected, next_context, _ = get_resume_context(shell_result.run_id)
    resume_run_id = selected or shell_result.run_id
    resume_context = next_context or request.resume_context
    if not respond_to_shell:
        return InteractiveShellTurnResult(
            task=request.task,
            task_metadata=None,
            resume_run_id=resume_run_id,
            resume_context=resume_context,
            output=shell_result.text,
            continue_loop=True,
        )
    return InteractiveShellTurnResult(
        task=SHELL_RESPONSE_TASK,
        task_metadata={"source": "interactive_shell"},
        resume_run_id=resume_run_id,
        resume_context=resume_context,
        output=shell_result.text,
        continue_loop=False,
    )


def _result(
    request: InteractiveShellTurnRequest,
    *,
    output: str,
    continue_loop: bool,
) -> InteractiveShellTurnResult:
    return InteractiveShellTurnResult(
        task=request.task,
        task_metadata=None,
        resume_run_id=request.resume_run_id,
        resume_context=request.resume_context,
        output=output,
        continue_loop=continue_loop,
    )


__all__ = [
    "InteractiveShellTurnRequest",
    "InteractiveShellTurnResult",
    "SHELL_RESPONSE_TASK",
    "run_interactive_shell_turn",
]
