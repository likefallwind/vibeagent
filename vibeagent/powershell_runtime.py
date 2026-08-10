from __future__ import annotations

from dataclasses import dataclass
import os
import shutil
from typing import Mapping

from .command_sandbox import prepare_command_launch
from .plugin_environment import plugin_command_environment
from .powershell_safety import get_blocked_powershell_reason
from .process_command_runtime import run_command
from .process_output_analysis import attach_output_analysis_to_command_result
from .session_working_directory import (
    finalize_shell_cwd,
    prepare_shell_cwd,
    wrap_powershell_command_for_cwd_capture,
)
from .types import CommandResult, PowerShellAction
from .workspace_core import RunWorkspace


POWERSHELL_ENABLE_ENV = "CLAUDE_CODE_USE_POWERSHELL_TOOL"
_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_VALUES = frozenset({"0", "false", "no", "off"})


@dataclass(frozen=True)
class PowerShellAvailability:
    enabled: bool
    executable: str | None
    message: str


def powershell_tool_availability(workspace: RunWorkspace) -> PowerShellAvailability:
    try:
        environment = plugin_command_environment(workspace)
    except (OSError, ValueError) as error:
        return PowerShellAvailability(False, None, f"PowerShell environment error: {error}")
    return powershell_availability_from_environment(environment, windows=os.name == "nt")


def powershell_availability_from_environment(
    environment: Mapping[str, str],
    *,
    windows: bool,
) -> PowerShellAvailability:
    raw_flag = environment.get(POWERSHELL_ENABLE_ENV)
    flag = raw_flag.strip().lower() if raw_flag is not None else None
    if flag is not None and flag not in _TRUE_VALUES | _FALSE_VALUES:
        return PowerShellAvailability(
            False,
            None,
            f"{POWERSHELL_ENABLE_ENV} must be 1 or 0 (true/false also accepted).",
        )
    enabled = flag in _TRUE_VALUES or (windows and flag not in _FALSE_VALUES)
    if not enabled:
        return PowerShellAvailability(
            False,
            None,
            f"Set {POWERSHELL_ENABLE_ENV}=1 to enable the PowerShell tool.",
        )

    path = environment.get("PATH")
    candidates = ("pwsh.exe", "powershell.exe") if windows else ("pwsh",)
    for candidate in candidates:
        executable = shutil.which(candidate, path=path)
        if executable:
            return PowerShellAvailability(True, executable, f"Using {executable}.")
    requirement = "pwsh.exe or powershell.exe" if windows else "PowerShell 7 (pwsh)"
    return PowerShellAvailability(False, None, f"{requirement} was not found on PATH.")


def execute_powershell_action(
    workspace: RunWorkspace,
    action: PowerShellAction,
    command_timeout_ms: int,
) -> CommandResult:
    timeout_ms = action.timeout_ms or command_timeout_ms
    max_output_chars = action.max_output_chars or 12_000
    blocked = get_blocked_powershell_reason(action.command)
    if blocked is not None:
        return _failed_result(
            action,
            timeout_ms,
            max_output_chars,
            f"PowerShell command blocked: {blocked}",
        )
    try:
        cwd_context = prepare_shell_cwd(
            workspace,
            action.cwd,
            maintain=action.maintain_cwd,
        )
        command_cwd = cwd_context.cwd
    except ValueError as error:
        return _failed_result(action, timeout_ms, max_output_chars, str(error))

    availability = powershell_tool_availability(workspace)
    if not availability.enabled or availability.executable is None:
        return _failed_result(action, timeout_ms, max_output_chars, availability.message)

    executed_command = wrap_powershell_command_for_cwd_capture(
        action.command,
        cwd_context.capture_path,
    )
    native_argv = (
        availability.executable,
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        executed_command,
    )
    launch = prepare_command_launch(
        workspace,
        action.command,
        command_cwd,
        argv=native_argv,
    )
    if launch.error is not None:
        if cwd_context.capture_path is not None:
            cwd_context.capture_path.unlink(missing_ok=True)
        return _failed_result(
            action,
            timeout_ms,
            max_output_chars,
            f"Command sandbox blocked: {launch.error}",
        )
    try:
        result = run_command(
            command_cwd,
            action.command,
            timeout_ms,
            workspace.root,
            max_output_chars=max_output_chars,
            argv=launch.argv,
            sandboxed=launch.sandboxed,
            sandbox_warning=launch.warning,
            environment=launch.environment,
        )
        result = finalize_shell_cwd(workspace, cwd_context, result)
    finally:
        if cwd_context.capture_path is not None:
            cwd_context.capture_path.unlink(missing_ok=True)
    return attach_output_analysis_to_command_result(workspace, action, result)


def _failed_result(
    action: PowerShellAction,
    timeout_ms: int,
    max_output_chars: int,
    message: str,
) -> CommandResult:
    return CommandResult(
        command=action.command,
        exit_code=None,
        stdout="",
        stderr=message,
        timed_out=False,
        signal=None,
        timeout_ms=timeout_ms,
        cwd=action.cwd or ".",
        max_output_chars=max_output_chars,
    )


__all__ = [
    "POWERSHELL_ENABLE_ENV",
    "PowerShellAvailability",
    "execute_powershell_action",
    "powershell_availability_from_environment",
    "powershell_tool_availability",
]
