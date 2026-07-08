from __future__ import annotations

import os
from pathlib import Path
import re
import time
from typing import Any

from .process_lifecycle import close_background_handles, signal_name
from .process_registry import (
    PersistentProcessRecord,
    persistent_process_running,
    process_signal_name,
    read_persistent_process_exit_code,
)
from .types import WaitProcessObservation


def wait_persistent_process(
    record: PersistentProcessRecord,
    *,
    timeout_ms: int,
    stdout_contains: str | None,
    stderr_contains: str | None,
    regex: bool,
    max_output_chars: int,
) -> WaitProcessObservation:
    deadline = time.monotonic() + (timeout_ms / 1000)
    wait_for_output = stdout_contains is not None or stderr_contains is not None
    timed_out = False
    while True:
        running = persistent_process_running(record)
        exit_code = None if running else read_persistent_process_exit_code(record)
        stdout = read_text_tail(record.stdout_path, max_output_chars)
        stderr = read_text_tail(record.stderr_path, max_output_chars)
        if wait_for_output:
            try:
                matched, matched_stream, matched_pattern = match_process_output(
                    stdout,
                    stderr,
                    stdout_contains=stdout_contains,
                    stderr_contains=stderr_contains,
                    regex=regex,
                )
            except re.error as error:
                return WaitProcessObservation(
                    kind="wait_process",
                    process_id=record.id,
                    pid=record.pid,
                    ok=False,
                    running=running,
                    timed_out=False,
                    matched=False,
                    matched_stream=None,
                    matched_pattern=None,
                    timeout_ms=timeout_ms,
                    exit_code=exit_code,
                    signal=process_signal_name(exit_code),
                    stdout=stdout,
                    stderr=stderr,
                    max_output_chars=max_output_chars,
                    message=f"Invalid wait_process regex: {error}.",
                )
            if matched:
                return WaitProcessObservation(
                    kind="wait_process",
                    process_id=record.id,
                    pid=record.pid,
                    ok=True,
                    running=running,
                    timed_out=False,
                    matched=True,
                    matched_stream=matched_stream,
                    matched_pattern=matched_pattern,
                    timeout_ms=timeout_ms,
                    exit_code=exit_code,
                    signal=process_signal_name(exit_code),
                    stdout=stdout,
                    stderr=stderr,
                    max_output_chars=max_output_chars,
                    message=f"Process {record.id} matched {matched_stream} output pattern.",
                )
            if not running:
                return WaitProcessObservation(
                    kind="wait_process",
                    process_id=record.id,
                    pid=record.pid,
                    ok=True,
                    running=False,
                    timed_out=False,
                    matched=False,
                    matched_stream=None,
                    matched_pattern=None,
                    timeout_ms=timeout_ms,
                    exit_code=None,
                    signal=None,
                    stdout=stdout,
                    stderr=stderr,
                    max_output_chars=max_output_chars,
                    message=f"Process {record.id} exited before output pattern matched.",
                )
        elif not running:
            return WaitProcessObservation(
                kind="wait_process",
                process_id=record.id,
                pid=record.pid,
                ok=True,
                running=False,
                timed_out=False,
                matched=False,
                matched_stream=None,
                matched_pattern=None,
                timeout_ms=timeout_ms,
                exit_code=exit_code,
                signal=process_signal_name(exit_code),
                stdout=stdout,
                stderr=stderr,
                max_output_chars=max_output_chars,
                message=f"Process {record.id} exited.",
            )

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            timed_out = True
        if timed_out:
            return WaitProcessObservation(
                kind="wait_process",
                process_id=record.id,
                pid=record.pid,
                ok=True,
                running=running,
                timed_out=True,
                matched=False,
                matched_stream=None,
                matched_pattern=None,
                timeout_ms=timeout_ms,
                exit_code=exit_code,
                signal=process_signal_name(exit_code),
                stdout=stdout,
                stderr=stderr,
                max_output_chars=max_output_chars,
                message=(
                    f"Process {record.id} is still running after timeout; no output pattern matched."
                    if wait_for_output
                    else f"Process {record.id} is still running after timeout."
                ),
            )
        time.sleep(min(0.1, remaining))


def wait_background_process_output(
    background: Any,
    *,
    timeout_ms: int,
    stdout_contains: str | None,
    stderr_contains: str | None,
    regex: bool,
    max_output_chars: int,
) -> WaitProcessObservation:
    deadline = time.monotonic() + (timeout_ms / 1000)
    while True:
        exit_code = background.process.poll()
        running = exit_code is None
        if not running:
            close_background_handles(background)
        stdout = read_text_tail(background.stdout_path, max_output_chars)
        stderr = read_text_tail(background.stderr_path, max_output_chars)
        try:
            matched, matched_stream, matched_pattern = match_process_output(
                stdout,
                stderr,
                stdout_contains=stdout_contains,
                stderr_contains=stderr_contains,
                regex=regex,
            )
        except re.error as error:
            return WaitProcessObservation(
                kind="wait_process",
                process_id=background.id,
                pid=background.process.pid,
                ok=False,
                running=running,
                timed_out=False,
                matched=False,
                matched_stream=None,
                matched_pattern=None,
                timeout_ms=timeout_ms,
                exit_code=exit_code,
                signal=signal_name(exit_code) if exit_code and exit_code < 0 else None,
                stdout=stdout,
                stderr=stderr,
                max_output_chars=max_output_chars,
                message=f"Invalid wait_process regex: {error}.",
            )

        if matched:
            return WaitProcessObservation(
                kind="wait_process",
                process_id=background.id,
                pid=background.process.pid,
                ok=True,
                running=running,
                timed_out=False,
                matched=True,
                matched_stream=matched_stream,
                matched_pattern=matched_pattern,
                timeout_ms=timeout_ms,
                exit_code=exit_code,
                signal=signal_name(exit_code) if exit_code and exit_code < 0 else None,
                stdout=stdout,
                stderr=stderr,
                max_output_chars=max_output_chars,
                message=f"Process {background.id} matched {matched_stream} output pattern.",
            )

        if not running:
            return WaitProcessObservation(
                kind="wait_process",
                process_id=background.id,
                pid=background.process.pid,
                ok=True,
                running=False,
                timed_out=False,
                matched=False,
                matched_stream=None,
                matched_pattern=None,
                timeout_ms=timeout_ms,
                exit_code=exit_code,
                signal=signal_name(exit_code) if exit_code and exit_code < 0 else None,
                stdout=stdout,
                stderr=stderr,
                max_output_chars=max_output_chars,
                message=f"Process {background.id} exited before output pattern matched.",
            )

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return WaitProcessObservation(
                kind="wait_process",
                process_id=background.id,
                pid=background.process.pid,
                ok=True,
                running=True,
                timed_out=True,
                matched=False,
                matched_stream=None,
                matched_pattern=None,
                timeout_ms=timeout_ms,
                exit_code=None,
                signal=None,
                stdout=stdout,
                stderr=stderr,
                max_output_chars=max_output_chars,
                message=f"Process {background.id} is still running after timeout; no output pattern matched.",
            )
        time.sleep(min(0.1, remaining))


def match_process_output(
    stdout: str,
    stderr: str,
    *,
    stdout_contains: str | None,
    stderr_contains: str | None,
    regex: bool,
) -> tuple[bool, str | None, str | None]:
    patterns = (("stdout", stdout, stdout_contains), ("stderr", stderr, stderr_contains))
    for stream, text, pattern in patterns:
        if pattern is None:
            continue
        if regex:
            if re.search(pattern, text):
                return True, stream, pattern
        elif pattern in text:
            return True, stream, pattern
    return False, None, None


def read_text_tail(path: Path, max_bytes: int = 4_000) -> str:
    if not path.exists():
        return ""
    with path.open("rb") as handle:
        handle.seek(0, os.SEEK_END)
        size = handle.tell()
        handle.seek(max(0, size - max_bytes), os.SEEK_SET)
        return handle.read().decode("utf-8", errors="replace")
