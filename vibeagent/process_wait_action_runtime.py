from __future__ import annotations

from pathlib import Path
import subprocess

from .process_background_lookup import background_process_for_root
from .process_lifecycle import close_background_handles, signal_name
from .process_registry import read_persistent_process_record
from .process_wait_runtime import read_text_tail, wait_background_process_output, wait_persistent_process
from .types import WaitProcessObservation


def wait_background_process(
    root: Path,
    process_id: str,
    timeout_ms: int = 5_000,
    stdout_contains: str | None = None,
    stderr_contains: str | None = None,
    regex: bool = False,
    max_output_chars: int | None = None,
) -> WaitProcessObservation:
    background = background_process_for_root(root, process_id)
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
