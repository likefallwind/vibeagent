from __future__ import annotations

import os
import shlex
import subprocess
from threading import Thread
import time
from pathlib import Path

from .command_output_artifacts import persist_truncated_command_outputs
from .command_output_observers import CommandOutputObserver, current_command_output_observer
from .process_lifecycle import signal_name as _signal_name
from .process_lifecycle import terminate_process as _terminate_process
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
        env=environment,
    )

    output_observer = current_command_output_observer()
    if output_observer is None:
        try:
            stdout, stderr = process.communicate(timeout=timeout_ms / 1000)
        except subprocess.TimeoutExpired:
            timed_out = True
            _terminate_process(process)
            stdout, stderr = process.communicate()
    else:
        stdout, stderr, timed_out = _communicate_with_observer(
            process,
            timeout_ms,
            output_observer,
        )
    duration_ms = max(0, round((time.monotonic() - started) * 1000))

    stdout_value, stdout_truncated = truncate_command_output(stdout or "", max_output_chars)
    stderr_text = stderr or ""
    if sandbox_warning:
        stderr_text = f"{sandbox_warning}\n{stderr_text}".rstrip() + "\n"
    stderr_value, stderr_truncated = truncate_command_output(stderr_text, max_output_chars)
    stdout_path = None
    stderr_path = None
    artifact_error = None
    if output_workspace is not None:
        stdout_path, stderr_path, artifact_error = persist_truncated_command_outputs(
            output_workspace,
            stdout or "",
            stderr_text,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
        )
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
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        stdout_total_bytes=len((stdout or "").encode("utf-8")),
        stderr_total_bytes=len(stderr_text.encode("utf-8")),
        output_artifact_error=artifact_error,
    )


def _communicate_with_observer(
    process: subprocess.Popen[str],
    timeout_ms: int,
    observer: CommandOutputObserver,
) -> tuple[str, str, bool]:
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []

    def read_stream(stream, chunks: list[str], *, is_stdout: bool) -> None:
        if stream is None:
            return
        try:
            for chunk in iter(stream.readline, ""):
                chunks.append(chunk)
                observer(chunk if is_stdout else "", "" if is_stdout else chunk)
        finally:
            stream.close()

    readers = (
        Thread(target=read_stream, args=(process.stdout, stdout_chunks), kwargs={"is_stdout": True}, daemon=True),
        Thread(target=read_stream, args=(process.stderr, stderr_chunks), kwargs={"is_stdout": False}, daemon=True),
    )
    for reader in readers:
        reader.start()
    timed_out = False
    try:
        process.wait(timeout=timeout_ms / 1000)
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate_process(process)
        process.wait()
    for reader in readers:
        reader.join()
    return "".join(stdout_chunks), "".join(stderr_chunks), timed_out


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
