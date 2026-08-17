from __future__ import annotations

import errno
import os
from pathlib import Path
import select
import stat
import sys
import time
from typing import Sequence


MAX_PROCESS_STDIN_BYTES = 64 * 1024
PROCESS_STDIN_WRITE_TIMEOUT_SECONDS = 2.0


class ProcessPtyError(ValueError):
    pass


def prepare_process_pty_launch(argv: Sequence[str], stdin_path: Path) -> tuple[str, ...]:
    if os.name != "posix":
        raise ProcessPtyError("--exec PTY-backed jobs require a POSIX runtime.")
    try:
        os.mkfifo(stdin_path, 0o600)
    except OSError as error:
        raise ProcessPtyError(f"Cannot create background job stdin transport: {error}.") from error
    return (
        sys.executable,
        "-m",
        "vibeagent.process_pty_relay",
        stdin_path.as_posix(),
        "--",
        *tuple(argv),
    )


def process_stdin_available(path: Path | None) -> bool:
    if path is None or os.name != "posix":
        return False
    try:
        info = path.lstat()
    except OSError:
        return False
    return (
        stat.S_ISFIFO(info.st_mode)
        and info.st_uid == os.getuid()
        and stat.S_IMODE(info.st_mode) & 0o077 == 0
    )


def write_process_stdin(path: Path, content: str) -> str | None:
    data = content.encode("utf-8")
    if len(data) > MAX_PROCESS_STDIN_BYTES:
        return f"stdin content exceeds {MAX_PROCESS_STDIN_BYTES} bytes"
    if not process_stdin_available(path):
        return "persistent stdin transport is unavailable"

    lock_descriptor: int | None = None
    fifo_descriptor: int | None = None
    try:
        lock_descriptor = _open_stdin_lock(path)
        fifo_descriptor = _open_fifo_writer(path)
        _write_all(fifo_descriptor, data)
    except OSError as error:
        return str(error)
    finally:
        if fifo_descriptor is not None:
            os.close(fifo_descriptor)
        if lock_descriptor is not None:
            _close_stdin_lock(lock_descriptor)
    return None


def remove_process_stdin(path: Path | None) -> None:
    if path is None:
        return
    try:
        path.unlink()
    except OSError:
        pass


def _open_stdin_lock(stdin_path: Path) -> int:
    import fcntl

    lock_path = stdin_path.with_suffix(".stdin.lock")
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(lock_path, flags, 0o600)
    try:
        info = os.fstat(descriptor)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) & 0o077 != 0
        ):
            raise OSError("unsafe persistent stdin lock")
        fcntl.flock(descriptor, fcntl.LOCK_EX)
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _close_stdin_lock(descriptor: int) -> None:
    import fcntl

    try:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
    finally:
        os.close(descriptor)


def _open_fifo_writer(path: Path) -> int:
    deadline = time.monotonic() + PROCESS_STDIN_WRITE_TIMEOUT_SECONDS
    flags = os.O_WRONLY | os.O_NONBLOCK
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    while True:
        try:
            descriptor = os.open(path, flags)
            if not stat.S_ISFIFO(os.fstat(descriptor).st_mode):
                os.close(descriptor)
                raise OSError("persistent stdin path is not a FIFO")
            return descriptor
        except OSError as error:
            if error.errno not in {errno.ENXIO, errno.ENOENT} or time.monotonic() >= deadline:
                raise
            time.sleep(0.02)


def _write_all(descriptor: int, data: bytes) -> None:
    deadline = time.monotonic() + PROCESS_STDIN_WRITE_TIMEOUT_SECONDS
    offset = 0
    while offset < len(data):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise OSError("timed out writing persistent stdin")
        _, writable, _ = select.select([], [descriptor], [], remaining)
        if not writable:
            raise OSError("timed out writing persistent stdin")
        try:
            offset += os.write(descriptor, data[offset:])
        except BlockingIOError:
            continue


__all__ = [
    "MAX_PROCESS_STDIN_BYTES",
    "ProcessPtyError",
    "prepare_process_pty_launch",
    "process_stdin_available",
    "remove_process_stdin",
    "write_process_stdin",
]
