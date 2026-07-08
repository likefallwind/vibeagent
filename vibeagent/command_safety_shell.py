from __future__ import annotations

from pathlib import Path
import re

from .command_safety_filesystem import (
    command_contains_dangerous_git_clean,
    command_contains_dangerous_rm,
    command_path_arguments,
    command_recursively_changes_broad_permissions,
    command_writes_to_device,
    is_dangerous_recursive_delete_target,
    is_raw_device_write_target,
    permission_invocation_targets_broad_path_recursively,
    shell_command_invocations,
)
from .command_safety_wrappers import (
    segment_invokes_network_fetch,
    segment_invokes_script_interpreter,
    shell_command_segments,
    shell_pipeline_segments,
    strip_command_wrapper_options,
    strip_dbus_launch_prefix,
    strip_dbus_run_session_prefix,
    strip_env_command_prefix,
    strip_ionice_prefix,
    strip_nice_prefix,
    strip_stdbuf_prefix,
    strip_systemd_run_prefix,
    strip_taskset_prefix,
    strip_timeout_prefix,
    unwrapped_shell_command_parts,
    unwrapped_shell_executable_name,
)


def command_pipes_network_script_to_shell(lowered_command: str) -> bool:
    segments = shell_pipeline_segments(lowered_command)
    if len(segments) < 2:
        return False
    for index, segment in enumerate(segments[:-1]):
        if not segment_invokes_network_fetch(segment):
            continue
        for sink in segments[index + 1 :]:
            if segment_invokes_script_interpreter(sink):
                return True
    return False


POWERSHELL_EXECUTABLES = {"powershell", "powershell.exe", "pwsh", "pwsh.exe"}
POWERSHELL_NETWORK_FETCH = re.compile(r"\b(?:iwr|irm|invoke-webrequest|invoke-restmethod)\b")
POWERSHELL_EXECUTE_EXPRESSION = re.compile(r"\b(?:iex|invoke-expression)\b")


def command_executes_powershell_network_script(lowered_command: str) -> bool:
    if command_segments_execute_powershell_network_script(lowered_command):
        return True
    segment = r"(^|[;&|]\s*)"
    wrappers = r"(?:(?:nohup|setsid)\s+|env\s+(?:(?:--|-[A-Za-z0-9_-]+|[a-z_][a-z0-9_]*=\S+)\s+)*)*"
    executable_path = r"(?:[^\s;&|]*/)?"
    powershell = rf"{executable_path}(?:powershell|pwsh)(?:\.exe)?\b"
    fetch = r"\b(?:iwr|irm|invoke-webrequest|invoke-restmethod)\b"
    execute = r"\|\s*(?:[^\s;&|]*/)?(?:iex|invoke-expression)\b"
    return bool(re.search(segment + wrappers + powershell + r".*" + fetch + r".*" + execute, lowered_command))


def command_segments_execute_powershell_network_script(lowered_command: str) -> bool:
    for segment in shell_command_segments(lowered_command):
        if powershell_segment_executes_network_script(segment):
            return True

    pipeline = shell_pipeline_segments(lowered_command)
    if len(pipeline) < 2:
        return False
    for index, segment in enumerate(pipeline[:-1]):
        if not segment_invokes_powershell_fetch(segment):
            continue
        if any(segment_invokes_powershell_expression(sink) for sink in pipeline[index + 1 :]):
            return True
    return False


def powershell_segment_executes_network_script(parts: list[str]) -> bool:
    remaining = unwrapped_shell_command_parts(parts)
    if not remaining:
        return False
    executable = Path(remaining[0]).name.lower()
    if executable not in POWERSHELL_EXECUTABLES:
        return False
    args = " ".join(remaining[1:])
    return bool(POWERSHELL_NETWORK_FETCH.search(args) and POWERSHELL_EXECUTE_EXPRESSION.search(args))


def segment_invokes_powershell_fetch(parts: list[str]) -> bool:
    remaining = unwrapped_shell_command_parts(parts)
    if not remaining:
        return False
    executable = Path(remaining[0]).name.lower()
    return executable in POWERSHELL_EXECUTABLES and POWERSHELL_NETWORK_FETCH.search(" ".join(remaining[1:])) is not None


def segment_invokes_powershell_expression(parts: list[str]) -> bool:
    remaining = unwrapped_shell_command_parts(parts)
    if not remaining:
        return False
    executable = Path(remaining[0]).name.lower()
    return executable in {"iex", "invoke-expression"}


__all__ = [
    "command_contains_dangerous_git_clean",
    "command_contains_dangerous_rm",
    "command_executes_powershell_network_script",
    "command_segments_execute_powershell_network_script",
    "command_path_arguments",
    "command_pipes_network_script_to_shell",
    "command_recursively_changes_broad_permissions",
    "command_writes_to_device",
    "is_dangerous_recursive_delete_target",
    "is_raw_device_write_target",
    "permission_invocation_targets_broad_path_recursively",
    "powershell_segment_executes_network_script",
    "segment_invokes_powershell_expression",
    "segment_invokes_powershell_fetch",
    "segment_invokes_network_fetch",
    "segment_invokes_script_interpreter",
    "shell_command_invocations",
    "shell_command_segments",
    "shell_pipeline_segments",
    "strip_command_wrapper_options",
    "strip_dbus_launch_prefix",
    "strip_dbus_run_session_prefix",
    "strip_env_command_prefix",
    "strip_ionice_prefix",
    "strip_nice_prefix",
    "strip_stdbuf_prefix",
    "strip_systemd_run_prefix",
    "strip_taskset_prefix",
    "strip_timeout_prefix",
    "unwrapped_shell_command_parts",
    "unwrapped_shell_executable_name",
]
