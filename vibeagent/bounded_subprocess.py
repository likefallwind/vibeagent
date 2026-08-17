from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess

from .command_output_observers import CommandOutputObserver
from .process_command_capture import capture_command_output
from .process_termination import terminate_process


@dataclass(frozen=True)
class BoundedProcessResult:
    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    stdout_truncated: bool
    stderr_truncated: bool
    stdout_total_chars: int
    stderr_total_chars: int


def run_bounded_subprocess(
    args: list[str] | tuple[str, ...],
    *,
    cwd: str | Path | None = None,
    env: dict[str, str] | None = None,
    timeout_ms: int,
    max_output_chars: int,
    observer: CommandOutputObserver | None = None,
    errors: str | None = None,
) -> BoundedProcessResult:
    argv = tuple(args)
    if not argv:
        raise ValueError("Subprocess arguments must not be empty.")
    if timeout_ms < 1:
        raise ValueError("Subprocess timeout must be positive.")
    if max_output_chars < 1:
        raise ValueError("Subprocess output character limit must be positive.")

    process = subprocess.Popen(
        argv,
        cwd=Path(cwd) if cwd is not None else None,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors=errors,
        start_new_session=os.name != "nt",
    )
    capture = capture_command_output(
        process,
        timeout_ms=timeout_ms,
        max_output_chars=max_output_chars,
        observer=observer,
        preserve_complete=False,
        terminate=lambda: terminate_process(process),
    )
    try:
        stdout, stdout_truncated = capture.stdout.render()
        stderr, stderr_truncated = capture.stderr.render()
        if capture.timed_out:
            raise subprocess.TimeoutExpired(
                argv,
                timeout_ms / 1000,
                output=stdout,
                stderr=stderr,
            )
        if process.returncode is None:
            raise RuntimeError("Subprocess output capture finished before the process exited.")
        return BoundedProcessResult(
            args=argv,
            returncode=process.returncode,
            stdout=stdout,
            stderr=stderr,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
            stdout_total_chars=capture.stdout.total_chars,
            stderr_total_chars=capture.stderr.total_chars,
        )
    finally:
        capture.close()


__all__ = ["BoundedProcessResult", "run_bounded_subprocess"]
