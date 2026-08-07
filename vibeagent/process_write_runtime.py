from __future__ import annotations

from .process_registry import PersistentProcessRecord
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
    return CheckWriteProcessObservation(
        kind="check_write_process",
        process_id=process_id,
        pid=record.pid,
        ok=False,
        running=running,
        command=record.command,
        cwd=record.cwd,
        content_chars=len(content),
        message=persistent_write_unavailable_message(process_id, running),
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
    return WriteProcessObservation(
        kind="write_process",
        process_id=process_id,
        pid=record.pid,
        ok=False,
        running=running,
        command=record.command,
        cwd=record.cwd,
        content_chars=len(content),
        message=persistent_write_unavailable_message(process_id, running),
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
