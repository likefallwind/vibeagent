from __future__ import annotations

import os
import shlex
import subprocess
import time
from pathlib import Path

from .command_output_artifacts import persist_truncated_command_output_streams
from .command_output_observers import current_command_output_observer
from .process_command_capture import (
    MAX_COMPLETE_OUTPUT_BYTES,
    capture_command_output,
    truncate_command_output,
)
from .process_lifecycle import signal_name as _signal_name
from .process_lifecycle import terminate_process as _terminate_process
from .tool_memory_limit import (
    ToolMemoryLaunch,
    ToolMemoryLimitError,
    cleanup_tool_memory_launch,
    prepare_tool_memory_launch,
)
from .tool_memory_systemd import (
    inspect_tool_memory_result,
    stop_tool_memory_unit,
    tool_memory_exceeded_message,
)
from .types import CommandResult
from .workspace_core import RunWorkspace


def run_command(
    cwd: str | Path,
    command: str,
    timeout_ms: int = 30_000,
    project_root: str | Path | None = None,
    max_output_chars: int = 12_000,
    argv: tuple[str, ...] | None = None,
    sandboxed: bool = False,
    sandbox_warning: str | None = None,
    environment: dict[str, str] | None = None,
    output_workspace: RunWorkspace | None = None,
) -> CommandResult:
    # Run shell command in controlled cwd, capture stdout/stderr, and enforce execution timeout.
    started = time.monotonic()
    command_cwd = Path(cwd)
    command_environment = dict(os.environ if environment is None else environment)
    memory_launch: ToolMemoryLaunch | None = None
    command_argv = tuple(argv) if argv is not None else ("/bin/sh", "-c", command)
    try:
        memory_launch = prepare_tool_memory_launch(
            command_argv,
            command_cwd,
            command_environment,
        )
    except ToolMemoryLimitError as error:
        return _command_setup_error(
            command,
            command_cwd,
            project_root,
            timeout_ms,
            max_output_chars,
            str(error),
            sandboxed=sandboxed,
            sandbox_warning=sandbox_warning,
        )
    try:
        process = subprocess.Popen(
            memory_launch.argv if memory_launch is not None else (argv or command),
            cwd=command_cwd,
            shell=memory_launch is None and argv is None,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=os.name != "nt",
            env=command_environment,
        )
    except BaseException:
        cleanup_tool_memory_launch(memory_launch)
        raise

    try:
        capture = capture_command_output(
            process,
            timeout_ms=timeout_ms,
            max_output_chars=max_output_chars,
            observer=current_command_output_observer(),
            preserve_complete=output_workspace is not None,
            terminate=lambda: _terminate_command_process(process, memory_launch, command_environment),
        )
        timed_out = capture.timed_out
    except BaseException:
        _terminate_command_process(process, memory_launch, command_environment)
        cleanup_tool_memory_launch(memory_launch)
        raise
    try:
        memory_result = (
            inspect_tool_memory_result(memory_launch, command_environment)
            if memory_launch is not None and process.returncode != 0
            else None
        )
        duration_ms = max(0, round((time.monotonic() - started) * 1000))

        stdout_value, stdout_truncated = capture.stdout.render()
        stderr_prefix = f"{sandbox_warning}\n" if sandbox_warning else ""
        stderr_suffix = ""
        if memory_launch is not None and memory_result is not None and memory_result.exceeded:
            memory_message = tool_memory_exceeded_message(memory_launch, memory_result)
            if capture.stderr.total_chars and not capture.stderr.ends_with_newline:
                stderr_suffix += "\n"
            stderr_suffix += f"{memory_message}\n"
        elif sandbox_warning and capture.stderr.total_chars and not capture.stderr.ends_with_newline:
            stderr_suffix = "\n"
        stderr_value, stderr_truncated = capture.stderr.render(prefix=stderr_prefix, suffix=stderr_suffix)
        stdout_path = None
        stderr_path = None
        artifact_error = None
        if output_workspace is not None:
            stdout_path, stderr_path, artifact_error = persist_truncated_command_output_streams(
                output_workspace,
                capture.stdout.complete_stream,
                capture.stderr.complete_stream,
                stdout_truncated=stdout_truncated,
                stderr_truncated=stderr_truncated,
                stderr_prefix=stderr_prefix,
                stderr_suffix=stderr_suffix,
                stdout_unavailable_reason=(
                    f"output exceeds the {MAX_COMPLETE_OUTPUT_BYTES // 1024**2} MiB complete-artifact limit"
                    if capture.stdout.complete_overflow
                    else "complete output stream is unavailable"
                ),
                stderr_unavailable_reason=(
                    f"output exceeds the {MAX_COMPLETE_OUTPUT_BYTES // 1024**2} MiB complete-artifact limit"
                    if capture.stderr.complete_overflow
                    else "complete output stream is unavailable"
                ),
            )
        return CommandResult(
            command=command,
            exit_code=process.returncode,
            stdout=stdout_value,
            stderr=stderr_value,
            timed_out=timed_out,
            signal=(
                memory_result.signal_name
                if memory_result is not None and memory_result.signal_name is not None
                else _signal_name(process.returncode)
                if process.returncode and process.returncode < 0
                else None
            ),
            timeout_ms=timeout_ms,
            cwd=relative_cwd(Path(cwd), project_root),
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
            max_output_chars=max_output_chars,
            duration_ms=duration_ms,
            sandboxed=sandboxed,
            sandbox_warning=sandbox_warning,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            stdout_total_bytes=capture.stdout.total_bytes,
            stderr_total_bytes=(
                len(stderr_prefix.encode("utf-8"))
                + capture.stderr.total_bytes
                + len(stderr_suffix.encode("utf-8"))
            ),
            output_artifact_error=artifact_error,
        )
    finally:
        cleanup_tool_memory_launch(memory_launch)
        capture.close()


def _terminate_command_process(
    process: subprocess.Popen[str],
    memory_launch: ToolMemoryLaunch | None,
    environment: dict[str, str],
) -> None:
    if memory_launch is not None:
        stop_tool_memory_unit(
            memory_launch.unit,
            environment,
            systemctl=memory_launch.systemctl,
        )
    if os.name != "nt" or process.poll() is None:
        _terminate_process(process)


def _command_setup_error(
    command: str,
    cwd: Path,
    project_root: str | Path | None,
    timeout_ms: int,
    max_output_chars: int,
    message: str,
    *,
    sandboxed: bool,
    sandbox_warning: str | None,
) -> CommandResult:
    return CommandResult(
        command=command,
        exit_code=None,
        stdout="",
        stderr=message,
        timed_out=False,
        signal=None,
        timeout_ms=timeout_ms,
        cwd=relative_cwd(cwd, project_root),
        max_output_chars=max_output_chars,
        sandboxed=sandboxed,
        sandbox_warning=sandbox_warning,
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


def relative_cwd(cwd: Path, project_root: str | Path | None) -> str:
    if project_root is None:
        return "."
    try:
        relative = cwd.resolve().relative_to(Path(project_root).resolve())
    except ValueError:
        return cwd.as_posix()
    return relative.as_posix() or "."
