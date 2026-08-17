from __future__ import annotations

from pathlib import Path

from .process_background_lookup import background_process_for_root
from .process_io_helpers import write_process_content_sha256
from .process_lifecycle import close_background_handles
from .process_pty import (
    MAX_PROCESS_STDIN_BYTES,
    process_stdin_available,
    write_process_stdin,
)
from .process_registry import persistent_process_running, read_persistent_process_record
from .process_write_runtime import (
    persistent_check_write_observation,
    persistent_write_observation,
    unknown_check_write_observation,
    unknown_write_observation,
)
from .types import CheckWriteProcessObservation, WriteProcessObservation


def check_write_background_process(root: Path, process_id: str, content: str) -> CheckWriteProcessObservation:
    content_sha256 = write_process_content_sha256(content)
    background = background_process_for_root(root, process_id)
    if background is None:
        record = read_persistent_process_record(root, process_id)
        if record is not None:
            running = persistent_process_running(record)
            return persistent_check_write_observation(
                process_id=process_id,
                record=record,
                running=running,
                content=content,
                content_sha256=content_sha256,
            )
        return unknown_check_write_observation(
            process_id=process_id,
            content=content,
            content_sha256=content_sha256,
        )

    exit_code = background.process.poll()
    running = exit_code is None
    stdin = background.process.stdin
    within_limit = len(content.encode("utf-8")) <= MAX_PROCESS_STDIN_BYTES
    writable = running and within_limit and (
        process_stdin_available(background.stdin_path)
        if background.stdin_path is not None
        else stdin is not None and not stdin.closed
    )
    if not running:
        close_background_handles(background)
    message = (
        f"Can write {len(content)} character(s) to process {process_id}."
        if writable
        else f"Cannot write to process {process_id}; stdin is unavailable, too large, or the process has exited."
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
    background = background_process_for_root(root, process_id)
    if background is None:
        record = read_persistent_process_record(root, process_id)
        if record is not None:
            running = persistent_process_running(record)
            return persistent_write_observation(
                process_id=process_id,
                record=record,
                running=running,
                content=content,
                content_sha256=content_sha256,
            )
        return unknown_write_observation(
            process_id=process_id,
            content=content,
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
    if background.stdin_path is not None:
        error = write_process_stdin(background.stdin_path, content)
        return WriteProcessObservation(
            kind="write_process",
            process_id=process_id,
            pid=background.process.pid,
            ok=error is None,
            running=background.process.poll() is None,
            command=background.command,
            cwd=background.cwd,
            content_chars=len(content),
            message=(
                f"Wrote {len(content)} character(s) to process {process_id}."
                if error is None
                else f"Failed to write to process {process_id}: {error}."
            ),
            content_sha256=content_sha256,
        )
    if len(content.encode("utf-8")) > MAX_PROCESS_STDIN_BYTES:
        return WriteProcessObservation(
            kind="write_process",
            process_id=process_id,
            pid=background.process.pid,
            ok=False,
            running=True,
            command=background.command,
            cwd=background.cwd,
            content_chars=len(content),
            message=f"Cannot write to process {process_id}; stdin exceeds {MAX_PROCESS_STDIN_BYTES} bytes.",
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
