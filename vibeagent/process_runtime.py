from __future__ import annotations

import os
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .command_safety import get_blocked_command_reason
from .command_sandbox import prepare_command_launch
from .output_conversion import output_context_results_from_dicts, output_diagnostics_from_dicts
from .process_command_runtime import run_command, relative_cwd, truncate_command_output, wrap_background_command
from .process_lifecycle import close_background_handles as _close_background_handles
from .process_lifecycle import signal_name as _signal_name
from .process_lifecycle import terminate_process as _terminate_process
from .process_io_runtime import (
    check_write_background_process,
    match_process_output,
    read_background_process,
    read_text_tail,
    wait_background_process,
    wait_background_process_output,
    wait_persistent_process,
    write_background_process,
)
from .process_output_analysis import (
    attach_output_analysis_to_command_result,
    attach_output_analysis_to_process_observation,
    command_result_failed,
    process_observation_failed,
)
from .process_output_runtime import read_background_process_output_contexts, read_background_process_output_diagnostics
from .process_registry import (
    PersistentProcessRecord,
    parse_persistent_process_record,
    process_record_path,
    process_registry_dir,
    process_signal_name,
    read_persistent_process_record,
    read_process_start_ticks,
    relative_process_log_path,
    resolve_process_log_path,
    write_persistent_process_record,
)
from .process_stop_runtime import (
    check_stop_all_background_processes,
    check_stop_background_process,
    list_background_processes,
    stop_all_background_processes,
    stop_background_process,
)
from .types import (
    CommandResult,
    RunCommandAction,
    RunCommandItem,
    StartCommandObservation,
)
from .workspace_core import RunWorkspace
from .workspace_resolve import resolve_command_cwd


@dataclass
class BackgroundProcess:
    id: str
    command: str
    cwd: str
    process: subprocess.Popen[str]
    stdout_path: Path
    stderr_path: Path
    exit_code_path: Path
    max_output_chars: int
    stdout_handle: Any
    stderr_handle: Any


BACKGROUND_PROCESSES: dict[str, BackgroundProcess] = {}


def release_background_process_handle(process_id: str) -> None:
    background = BACKGROUND_PROCESSES.pop(process_id, None)
    if background is not None:
        try:
            background.process.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            _terminate_process(background.process)
        _close_background_handles(background)


def execute_run_command_item(
    workspace: RunWorkspace,
    action: RunCommandAction | RunCommandItem,
    command_timeout_ms: int,
) -> CommandResult:
    timeout_ms = action.timeout_ms or command_timeout_ms
    max_output_chars = action.max_output_chars or 12_000
    blocked = get_blocked_command_reason(action.command)
    if blocked:
        return CommandResult(
            command=action.command,
            exit_code=None,
            stdout="",
            stderr=f"Command blocked: {blocked}",
            timed_out=False,
            signal=None,
            timeout_ms=timeout_ms,
            cwd=action.cwd or ".",
            max_output_chars=max_output_chars,
        )
    try:
        command_cwd = resolve_command_cwd(workspace, action.cwd)
    except ValueError as error:
        return CommandResult(
            command=action.command,
            exit_code=None,
            stdout="",
            stderr=str(error),
            timed_out=False,
            signal=None,
            timeout_ms=timeout_ms,
            cwd=action.cwd or ".",
            max_output_chars=max_output_chars,
        )
    launch = prepare_command_launch(workspace, action.command, command_cwd)
    if launch.error is not None:
        return CommandResult(
            command=action.command,
            exit_code=None,
            stdout="",
            stderr=f"Command sandbox blocked: {launch.error}",
            timed_out=False,
            signal=None,
            timeout_ms=timeout_ms,
            cwd=action.cwd or ".",
            max_output_chars=max_output_chars,
            sandboxed=False,
        )
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
    return attach_output_analysis_to_command_result(workspace, action, result)


def start_background_command(
    workspace: RunWorkspace,
    command: str,
    cwd: str | None = None,
    max_output_chars: int = 4_000,
) -> StartCommandObservation:
    blocked = get_blocked_command_reason(command)
    if blocked:
        return StartCommandObservation(
            kind="start_command",
            process_id="",
            pid=None,
            command=command,
            cwd=cwd or ".",
            ok=False,
            message=f"Command blocked: {blocked}",
            stdout_path="",
            stderr_path="",
        )

    try:
        command_cwd = resolve_command_cwd(workspace, cwd)
    except ValueError as error:
        return StartCommandObservation(
            kind="start_command",
            process_id="",
            pid=None,
            command=command,
            cwd=cwd or ".",
            ok=False,
            message=str(error),
            stdout_path="",
            stderr_path="",
        )

    process_id = uuid.uuid4().hex[:12]
    process_dir = workspace.session_dir / "processes"
    process_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = process_dir / f"{process_id}.stdout.log"
    stderr_path = process_dir / f"{process_id}.stderr.log"
    exit_code_path = process_dir / f"{process_id}.exitcode"
    stdout_handle = stdout_path.open("w", encoding="utf-8")
    stderr_handle = stderr_path.open("w", encoding="utf-8")
    wrapped_command = wrap_background_command(command, exit_code_path)
    launch = prepare_command_launch(workspace, command, command_cwd, executed_command=wrapped_command)
    if launch.error is not None:
        stdout_handle.close()
        stderr_handle.close()
        return StartCommandObservation(
            kind="start_command",
            process_id="",
            pid=None,
            command=command,
            cwd=relative_cwd(command_cwd, workspace.root),
            ok=False,
            message=f"Command sandbox blocked: {launch.error}",
            stdout_path=stdout_path.as_posix(),
            stderr_path=stderr_path.as_posix(),
        )
    if launch.warning:
        stderr_handle.write(f"{launch.warning}\n")
        stderr_handle.flush()
    try:
        process = subprocess.Popen(
            launch.argv,
            cwd=command_cwd,
            shell=False,
            stdin=subprocess.PIPE,
            stdout=stdout_handle,
            stderr=stderr_handle,
            text=True,
            start_new_session=os.name != "nt",
            env=launch.environment,
        )
    except OSError as error:
        stdout_handle.close()
        stderr_handle.close()
        return StartCommandObservation(
            kind="start_command",
            process_id="",
            pid=None,
            command=command,
            cwd=relative_cwd(command_cwd, workspace.root),
            ok=False,
            message=str(error),
            stdout_path=stdout_path.as_posix(),
            stderr_path=stderr_path.as_posix(),
        )

    BACKGROUND_PROCESSES[process_id] = BackgroundProcess(
        id=process_id,
        command=command,
        cwd=relative_cwd(command_cwd, workspace.root),
        process=process,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        exit_code_path=exit_code_path,
        max_output_chars=max_output_chars,
        stdout_handle=stdout_handle,
        stderr_handle=stderr_handle,
    )
    write_persistent_process_record(
        workspace,
        PersistentProcessRecord(
            id=process_id,
            command=command,
            cwd=relative_cwd(command_cwd, workspace.root),
            pid=process.pid,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            exit_code_path=exit_code_path,
            start_ticks=read_process_start_ticks(process.pid),
            max_output_chars=max_output_chars,
        ),
    )
    return StartCommandObservation(
        kind="start_command",
        process_id=process_id,
        pid=process.pid,
        command=command,
        cwd=relative_cwd(command_cwd, workspace.root),
        ok=True,
        message=f"Started process {process_id}.",
        stdout_path=stdout_path.as_posix(),
        stderr_path=stderr_path.as_posix(),
        sandboxed=launch.sandboxed,
        sandbox_warning=launch.warning,
    )
