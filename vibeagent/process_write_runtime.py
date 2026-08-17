from __future__ import annotations

from .process_registry import PersistentProcessRecord
from .process_pty import (
    MAX_PROCESS_STDIN_BYTES,
    process_stdin_available,
    write_process_stdin,
)
from .types import CheckWriteProcessObservation, WriteProcessObservation


def persistent_write_unavailable_message(process_id: str, running: bool) -> str:
    return (
        f"Cannot write to process {process_id}; stdin is only available in the runtime that started it."
        if running
        else f"Cannot write to process {process_id}; process has exited."
    )


def persistent_check_write_observation(
    *,
    process_id: str,
    record: PersistentProcessRecord,
    running: bool,
    content: str,
    content_sha256: str,
) -> CheckWriteProcessObservation:
    within_limit = len(content.encode("utf-8")) <= MAX_PROCESS_STDIN_BYTES
    writable = running and within_limit and process_stdin_available(record.stdin_path)
    if writable:
        message = f"Can write {len(content)} character(s) to process {process_id}."
    elif not running:
        message = f"Cannot write to process {process_id}; process has exited."
    elif not within_limit:
        message = f"Cannot write to process {process_id}; stdin exceeds {MAX_PROCESS_STDIN_BYTES} bytes."
    else:
        message = persistent_write_unavailable_message(process_id, running)
    return CheckWriteProcessObservation(
        kind="check_write_process",
        process_id=process_id,
        pid=record.pid,
        ok=writable,
        running=running,
        command=record.command,
        cwd=record.cwd,
        content_chars=len(content),
        message=message,
        content_sha256=content_sha256,
    )


def unknown_check_write_observation(
    *,
    process_id: str,
    content: str,
    content_sha256: str,
) -> CheckWriteProcessObservation:
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


def persistent_write_observation(
    *,
    process_id: str,
    record: PersistentProcessRecord,
    running: bool,
    content: str,
    content_sha256: str,
) -> WriteProcessObservation:
    if not running:
        error = "process has exited"
    elif record.stdin_path is None:
        error = "stdin is only available in the runtime that started it"
    else:
        error = write_process_stdin(record.stdin_path, content)
    return WriteProcessObservation(
        kind="write_process",
        process_id=process_id,
        pid=record.pid,
        ok=error is None,
        running=running,
        command=record.command,
        cwd=record.cwd,
        content_chars=len(content),
        message=(
            f"Wrote {len(content)} character(s) to process {process_id}."
            if error is None
            else f"Cannot write to process {process_id}; {error}."
        ),
        content_sha256=content_sha256,
    )


def unknown_write_observation(
    *,
    process_id: str,
    content: str,
    content_sha256: str,
) -> WriteProcessObservation:
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
