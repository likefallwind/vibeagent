from __future__ import annotations

from pathlib import Path

from .process_background_lookup import background_process_for_root
from .process_io_helpers import filter_output_lines as _filter_output_lines
from .process_lifecycle import close_background_handles, signal_name
from .process_registry import (
    persistent_process_running,
    process_signal_name,
    read_persistent_process_exit_code,
    read_persistent_process_record,
)
from .process_wait_runtime import read_text_tail
from .types import ReadProcessObservation


def read_background_process(
    root: Path,
    process_id: str,
    max_output_chars: int | None = None,
    output_filter: str | None = None,
) -> ReadProcessObservation:
    background = background_process_for_root(root, process_id)
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
