from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from typing import Any

from .process_io_helpers import filter_output_lines as _filter_output_lines
from .process_io_helpers import write_process_content_sha256
from .process_lifecycle import close_background_handles, signal_name
from .process_registry import (
    persistent_process_running,
    process_signal_name,
    read_persistent_process_exit_code,
    read_persistent_process_record,
)
from .process_wait_runtime import (
    match_process_output,
    read_text_tail,
    wait_background_process_output,
    wait_persistent_process,
)
from .types import CheckWriteProcessObservation, ReadProcessObservation, WaitProcessObservation, WriteProcessObservation


def _background_processes() -> dict[str, Any]:
    runtime_module = sys.modules.get("vibeagent.process_runtime")
    value = getattr(runtime_module, "BACKGROUND_PROCESSES", None) if runtime_module is not None else None
    return value if isinstance(value, dict) else {}


def read_background_process(
    root: Path,
    process_id: str,
    max_output_chars: int | None = None,
    output_filter: str | None = None,
) -> ReadProcessObservation:
    background = _background_processes().get(process_id)
    if background is None:
        record = read_persistent_process_record(root, process_id)
        if record is not None:
            resolved_max_output_chars = max_output_chars or record.max_output_chars or 4_000
            running = persistent_process_running(record)
            exit_code = None if running else read_persistent_process_exit_code(record)
            stdout = _filter_output_lines(read_text_tail(record.stdout_path, resolved_max_output_chars), output_filter)
            stderr = _filter_output_lines(read_text_tail(record.stderr_path, resolved_max_output_chars), output_filter)
            state = "running" if running else "exited or unavailable"
            return ReadProcessObservation(
                kind="read_process",
                process_id=process_id,
                pid=record.pid,
                ok=True,
                running=running,
                exit_code=exit_code,
                signal=process_signal_name(exit_code),
                stdout=stdout,
                stderr=stderr,
                max_output_chars=resolved_max_output_chars,
                message=f"Process {process_id} is {state}.",
            )
        resolved_max_output_chars = max_output_chars or 4_000
        return ReadProcessObservation(
            kind="read_process",
            process_id=process_id,
            pid=None,
            ok=False,
            running=False,
            exit_code=None,
            signal=None,
            stdout="",
            stderr="",
            max_output_chars=resolved_max_output_chars,
            message="Unknown background process id.",
        )

    resolved_max_output_chars = max_output_chars or getattr(background, "max_output_chars", None) or 4_000
    exit_code = background.process.poll()
    running = exit_code is None
    if not running:
        close_background_handles(background)
    stdout = _filter_output_lines(read_text_tail(background.stdout_path, resolved_max_output_chars), output_filter)
    stderr = _filter_output_lines(read_text_tail(background.stderr_path, resolved_max_output_chars), output_filter)
    return ReadProcessObservation(
        kind="read_process",
        process_id=process_id,
        pid=background.process.pid,
        ok=True,
        running=running,
        exit_code=exit_code,
        signal=signal_name(exit_code) if exit_code and exit_code < 0 else None,
        stdout=stdout,
        stderr=stderr,
        max_output_chars=resolved_max_output_chars,
        message=f"Process {process_id} is {'running' if running else 'exited'}.",
    )


def wait_background_process(
    root: Path,
    process_id: str,
    timeout_ms: int = 5_000,
    stdout_contains: str | None = None,
    stderr_contains: str | None = None,
    regex: bool = False,
    max_output_chars: int | None = None,
) -> WaitProcessObservation:
    background = _background_processes().get(process_id)
    if background is None:
        record = read_persistent_process_record(root, process_id)
        if record is not None:
            resolved_max_output_chars = max_output_chars or record.max_output_chars or 4_000
            return wait_persistent_process(
                record,
                timeout_ms=timeout_ms,
                stdout_contains=stdout_contains,
                stderr_contains=stderr_contains,
                regex=regex,
                max_output_chars=resolved_max_output_chars,
            )
        resolved_max_output_chars = max_output_chars or 4_000
        return WaitProcessObservation(
            kind="wait_process",
            process_id=process_id,
            pid=None,
            ok=False,
            running=False,
            timed_out=False,
            matched=False,
            matched_stream=None,
            matched_pattern=None,
            timeout_ms=timeout_ms,
            exit_code=None,
            signal=None,
            stdout="",
            stderr="",
            max_output_chars=resolved_max_output_chars,
            message="Unknown background process id.",
        )

    resolved_max_output_chars = max_output_chars or getattr(background, "max_output_chars", None) or 4_000
    wait_for_output = stdout_contains is not None or stderr_contains is not None
    if wait_for_output:
        return wait_background_process_output(
            background,
            timeout_ms=timeout_ms,
            stdout_contains=stdout_contains,
            stderr_contains=stderr_contains,
            regex=regex,
            max_output_chars=resolved_max_output_chars,
        )

    timed_out = False
    try:
        exit_code = background.process.wait(timeout=timeout_ms / 1000)
    except subprocess.TimeoutExpired:
        timed_out = True
        exit_code = background.process.poll()

    running = exit_code is None
    if not running:
        close_background_handles(background)
    stdout = read_text_tail(background.stdout_path, resolved_max_output_chars)
    stderr = read_text_tail(background.stderr_path, resolved_max_output_chars)
    state = "still running" if running else "exited"
    timeout_note = " after timeout" if timed_out else ""
    return WaitProcessObservation(
        kind="wait_process",
        process_id=process_id,
        pid=background.process.pid,
        ok=True,
        running=running,
        timed_out=timed_out,
        matched=False,
        matched_stream=None,
        matched_pattern=None,
        timeout_ms=timeout_ms,
        exit_code=exit_code,
        signal=signal_name(exit_code) if exit_code and exit_code < 0 else None,
        stdout=stdout,
        stderr=stderr,
        max_output_chars=resolved_max_output_chars,
        message=f"Process {process_id} is {state}{timeout_note}.",
    )


def check_write_background_process(root: Path, process_id: str, content: str) -> CheckWriteProcessObservation:
    content_sha256 = write_process_content_sha256(content)
    background = _background_processes().get(process_id)
    if background is None:
        record = read_persistent_process_record(root, process_id)
        if record is not None:
            running = persistent_process_running(record)
            message = (
                f"Cannot write to process {process_id}; stdin is only available in the runtime that started it."
                if running
                else f"Cannot write to process {process_id}; process has exited."
            )
            return CheckWriteProcessObservation(
                kind="check_write_process",
                process_id=process_id,
                pid=record.pid,
                ok=False,
                running=running,
                command=record.command,
                cwd=record.cwd,
                content_chars=len(content),
                message=message,
                content_sha256=content_sha256,
            )
        return CheckWriteProcessObservation(
            kind="check_write_process",
            process_id=process_id,
            pid=None,
            ok=False,
            running=False,
            command=None,
            cwd=None,
            content_chars=len(content),
            message="Unknown background process id.",
            content_sha256=content_sha256,
        )

    exit_code = background.process.poll()
    running = exit_code is None
    stdin = background.process.stdin
    writable = running and stdin is not None and not stdin.closed
    if not running:
        close_background_handles(background)
    message = (
        f"Can write {len(content)} character(s) to process {process_id}."
        if writable
        else f"Cannot write to process {process_id}; stdin is closed or the process has exited."
    )
    return CheckWriteProcessObservation(
        kind="check_write_process",
        process_id=process_id,
        pid=background.process.pid,
        ok=writable,
        running=running,
        command=background.command,
        cwd=background.cwd,
        content_chars=len(content),
        message=message,
        content_sha256=content_sha256,
    )


def write_background_process(root: Path, process_id: str, content: str) -> WriteProcessObservation:
    content_sha256 = write_process_content_sha256(content)
    background = _background_processes().get(process_id)
    if background is None:
        record = read_persistent_process_record(root, process_id)
        if record is not None:
            running = persistent_process_running(record)
            message = (
                f"Cannot write to process {process_id}; stdin is only available in the runtime that started it."
                if running
                else f"Cannot write to process {process_id}; process has exited."
            )
            return WriteProcessObservation(
                kind="write_process",
                process_id=process_id,
                pid=record.pid,
                ok=False,
                running=running,
                command=record.command,
                cwd=record.cwd,
                content_chars=len(content),
                message=message,
                content_sha256=content_sha256,
            )
        return WriteProcessObservation(
            kind="write_process",
            process_id=process_id,
            pid=None,
            ok=False,
            running=False,
            command=None,
            cwd=None,
            content_chars=len(content),
            message="Unknown background process id.",
            content_sha256=content_sha256,
        )

    exit_code = background.process.poll()
    running = exit_code is None
    stdin = background.process.stdin
    if not running:
        close_background_handles(background)
        return WriteProcessObservation(
            kind="write_process",
            process_id=process_id,
            pid=background.process.pid,
            ok=False,
            running=False,
            command=background.command,
            cwd=background.cwd,
            content_chars=len(content),
            message=f"Cannot write to process {process_id}; process has exited.",
            content_sha256=content_sha256,
        )
    if stdin is None or stdin.closed:
        return WriteProcessObservation(
            kind="write_process",
            process_id=process_id,
            pid=background.process.pid,
            ok=False,
            running=True,
            command=background.command,
            cwd=background.cwd,
            content_chars=len(content),
            message=f"Cannot write to process {process_id}; stdin is closed.",
            content_sha256=content_sha256,
        )

    try:
        stdin.write(content)
        stdin.flush()
    except (BrokenPipeError, OSError, ValueError) as error:
        return WriteProcessObservation(
            kind="write_process",
            process_id=process_id,
            pid=background.process.pid,
            ok=False,
            running=background.process.poll() is None,
            command=background.command,
            cwd=background.cwd,
            content_chars=len(content),
            message=f"Failed to write to process {process_id}: {error}.",
            content_sha256=content_sha256,
        )

    return WriteProcessObservation(
        kind="write_process",
        process_id=process_id,
        pid=background.process.pid,
        ok=True,
        running=background.process.poll() is None,
        command=background.command,
        cwd=background.cwd,
        content_chars=len(content),
        message=f"Wrote {len(content)} character(s) to process {process_id}.",
        content_sha256=content_sha256,
    )
