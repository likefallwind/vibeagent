from __future__ import annotations

import os
import shlex
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .command_safety import get_blocked_command_reason
from .command_sandbox import prepare_command_launch
from .output_conversion import output_context_results_from_dicts, output_diagnostics_from_dicts
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
    ProcessOutputContextsAction,
    ProcessOutputContextsObservation,
    ProcessOutputDiagnosticsAction,
    ProcessOutputDiagnosticsObservation,
    RunCommandAction,
    RunCommandItem,
    StartCommandObservation,
)
from .workspace_core import RunWorkspace
from .workspace_resolve import resolve_command_cwd
from .workspace import read_output_contexts_result, read_output_diagnostics_result


@dataclass
class BackgroundProcess:
    id: str
    command: str
    cwd: str
    process: subprocess.Popen[str]
    stdout_path: Path
    stderr_path: Path
    exit_code_path: Path
    stdout_handle: Any
    stderr_handle: Any


BACKGROUND_PROCESSES: dict[str, BackgroundProcess] = {}


def run_command(
    cwd: str | Path,
    command: str,
    timeout_ms: int = 30_000,
    project_root: str | Path | None = None,
    max_output_chars: int = 12_000,
    argv: tuple[str, ...] | None = None,
    sandboxed: bool = False,
    sandbox_warning: str | None = None,
) -> CommandResult:
    # Run shell command in controlled cwd, capture stdout/stderr, and enforce execution timeout.
    timed_out = False
    started = time.monotonic()
    process = subprocess.Popen(
        argv or command,
        cwd=Path(cwd),
        shell=argv is None,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=os.name != "nt",
    )

    try:
        stdout, stderr = process.communicate(timeout=timeout_ms / 1000)
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate_process(process)
        stdout, stderr = process.communicate()
    duration_ms = max(0, round((time.monotonic() - started) * 1000))

    stdout_value, stdout_truncated = truncate_command_output(stdout or "", max_output_chars)
    stderr_text = stderr or ""
    if sandbox_warning:
        stderr_text = f"{sandbox_warning}\n{stderr_text}".rstrip() + "\n"
    stderr_value, stderr_truncated = truncate_command_output(stderr_text, max_output_chars)
    return CommandResult(
        command=command,
        exit_code=process.returncode,
        stdout=stdout_value,
        stderr=stderr_value,
        timed_out=timed_out,
        signal=_signal_name(process.returncode) if process.returncode and process.returncode < 0 else None,
        timeout_ms=timeout_ms,
        cwd=relative_cwd(Path(cwd), project_root),
        stdout_truncated=stdout_truncated,
        stderr_truncated=stderr_truncated,
        max_output_chars=max_output_chars,
        duration_ms=duration_ms,
        sandboxed=sandboxed,
        sandbox_warning=sandbox_warning,
    )


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
    )
    return attach_output_analysis_to_command_result(workspace, action, result)


def start_background_command(workspace: RunWorkspace, command: str, cwd: str | None = None) -> StartCommandObservation:
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


def wrap_background_command(command: str, exit_code_path: Path) -> str:
    if os.name == "nt":
        escaped_exit_code_path = str(exit_code_path).replace('"', '""')
        quoted_exit_code_path = f'"{escaped_exit_code_path}"'
        return (
            f"{command}\r\n"
            "set __vibeagent_exit_code=%ERRORLEVEL%\r\n"
            f"echo %__vibeagent_exit_code%> {quoted_exit_code_path}\r\n"
            "exit /b %__vibeagent_exit_code%"
        )
    quoted_exit_code_path = shlex.quote(exit_code_path.as_posix())
    return (
        f"{command}\n"
        "__vibeagent_exit_code=$?\n"
        f"printf '%s\\n' \"$__vibeagent_exit_code\" > {quoted_exit_code_path}\n"
        "exit \"$__vibeagent_exit_code\""
    )


def read_background_process_output_contexts(
    workspace: RunWorkspace,
    action: ProcessOutputContextsAction,
) -> ProcessOutputContextsObservation:
    process = read_background_process(
        workspace.root,
        action.process_id,
        max_output_chars=action.max_output_chars,
    )
    if not process.ok:
        return ProcessOutputContextsObservation(
            kind="process_output_contexts",
            process_id=action.process_id,
            pid=process.pid,
            ok=False,
            running=False,
            exit_code=process.exit_code,
            signal=process.signal,
            contexts=[],
            total_refs=0,
            truncated=False,
            stdout_chars=0,
            stderr_chars=0,
            max_output_chars=action.max_output_chars,
            message=process.message,
        )

    text = "\n".join(part for part in [process.stdout, process.stderr] if part)
    if not text.strip():
        return ProcessOutputContextsObservation(
            kind="process_output_contexts",
            process_id=action.process_id,
            pid=process.pid,
            ok=True,
            running=process.running,
            exit_code=process.exit_code,
            signal=process.signal,
            contexts=[],
            total_refs=0,
            truncated=False,
            stdout_chars=len(process.stdout),
            stderr_chars=len(process.stderr),
            max_output_chars=action.max_output_chars,
            message=f"Process {action.process_id} output contained no file:line references.",
        )

    try:
        result = read_output_contexts_result(
            workspace,
            text,
            context_lines=action.context_lines,
            max_contexts=action.max_contexts,
            max_bytes_per_context=action.max_bytes_per_context,
        )
    except ValueError as error:
        return ProcessOutputContextsObservation(
            kind="process_output_contexts",
            process_id=action.process_id,
            pid=process.pid,
            ok=False,
            running=process.running,
            exit_code=process.exit_code,
            signal=process.signal,
            contexts=[],
            total_refs=0,
            truncated=False,
            stdout_chars=len(process.stdout),
            stderr_chars=len(process.stderr),
            max_output_chars=action.max_output_chars,
            message=str(error),
        )

    contexts = output_context_results_from_dicts(result["contexts"])
    total_refs = int(result["total_refs"])
    return ProcessOutputContextsObservation(
        kind="process_output_contexts",
        process_id=action.process_id,
        pid=process.pid,
        ok=True,
        running=process.running,
        exit_code=process.exit_code,
        signal=process.signal,
        contexts=contexts,
        total_refs=total_refs,
        truncated=bool(result["truncated"]),
        stdout_chars=len(process.stdout),
        stderr_chars=len(process.stderr),
        max_output_chars=action.max_output_chars,
        message=f"Extracted {len(contexts)}/{total_refs} output context(s) from process {action.process_id}.",
    )


def read_background_process_output_diagnostics(
    workspace: RunWorkspace,
    action: ProcessOutputDiagnosticsAction,
) -> ProcessOutputDiagnosticsObservation:
    process = read_background_process(
        workspace.root,
        action.process_id,
        max_output_chars=action.max_output_chars,
    )
    if not process.ok:
        return ProcessOutputDiagnosticsObservation(
            kind="process_output_diagnostics",
            process_id=action.process_id,
            pid=process.pid,
            ok=False,
            running=False,
            exit_code=process.exit_code,
            signal=process.signal,
            diagnostics=[],
            contexts=[],
            total_diagnostics=0,
            total_refs=0,
            diagnostics_truncated=False,
            contexts_truncated=False,
            stdout_chars=0,
            stderr_chars=0,
            max_output_chars=action.max_output_chars,
            message=process.message,
        )

    text = "\n".join(part for part in [process.stdout, process.stderr] if part)
    if not text.strip():
        return ProcessOutputDiagnosticsObservation(
            kind="process_output_diagnostics",
            process_id=action.process_id,
            pid=process.pid,
            ok=True,
            running=process.running,
            exit_code=process.exit_code,
            signal=process.signal,
            diagnostics=[],
            contexts=[],
            total_diagnostics=0,
            total_refs=0,
            diagnostics_truncated=False,
            contexts_truncated=False,
            stdout_chars=len(process.stdout),
            stderr_chars=len(process.stderr),
            max_output_chars=action.max_output_chars,
            message=f"Process {action.process_id} output contained no diagnostic lines.",
        )

    try:
        result = read_output_diagnostics_result(
            workspace,
            text,
            context_lines=action.context_lines,
            max_diagnostics=action.max_diagnostics,
            max_contexts=action.max_contexts,
            max_bytes_per_context=action.max_bytes_per_context,
        )
    except ValueError as error:
        return ProcessOutputDiagnosticsObservation(
            kind="process_output_diagnostics",
            process_id=action.process_id,
            pid=process.pid,
            ok=False,
            running=process.running,
            exit_code=process.exit_code,
            signal=process.signal,
            diagnostics=[],
            contexts=[],
            total_diagnostics=0,
            total_refs=0,
            diagnostics_truncated=False,
            contexts_truncated=False,
            stdout_chars=len(process.stdout),
            stderr_chars=len(process.stderr),
            max_output_chars=action.max_output_chars,
            message=str(error),
        )

    diagnostics = output_diagnostics_from_dicts(result["diagnostics"])
    contexts = output_context_results_from_dicts(result["contexts"])
    total_diagnostics = int(result["total_diagnostics"])
    total_refs = int(result["total_refs"])
    return ProcessOutputDiagnosticsObservation(
        kind="process_output_diagnostics",
        process_id=action.process_id,
        pid=process.pid,
        ok=True,
        running=process.running,
        exit_code=process.exit_code,
        signal=process.signal,
        diagnostics=diagnostics,
        contexts=contexts,
        total_diagnostics=total_diagnostics,
        total_refs=total_refs,
        diagnostics_truncated=bool(result["diagnostics_truncated"]),
        contexts_truncated=bool(result["contexts_truncated"]),
        stdout_chars=len(process.stdout),
        stderr_chars=len(process.stderr),
        max_output_chars=action.max_output_chars,
        message=(
            f"Extracted {len(diagnostics)}/{total_diagnostics} diagnostic(s) "
            f"and {len(contexts)}/{total_refs} source context(s) from process {action.process_id}."
        ),
    )


def relative_cwd(cwd: Path, project_root: str | Path | None) -> str:
    if project_root is None:
        return "."
    try:
        relative = cwd.resolve().relative_to(Path(project_root).resolve())
    except ValueError:
        return cwd.as_posix()
    return relative.as_posix() or "."


def truncate_command_output(value: str, max_chars: int) -> tuple[str, bool]:
    if len(value) <= max_chars:
        return value, False
    marker = f"\n[truncated to {max_chars} chars: showing head and tail]\n"
    if max_chars <= len(marker) + 2:
        return value[:max_chars], True
    keep = max_chars - len(marker)
    head = keep // 2
    tail = keep - head
    return f"{value[:head]}{marker}{value[-tail:]}", True
