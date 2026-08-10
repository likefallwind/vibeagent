from __future__ import annotations

import inspect
import json
import os
from contextlib import contextmanager
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path
from typing import Callable, Iterator, ParamSpec, TypeVar

from .workspace_core import RunWorkspace

try:
    import fcntl as _fcntl
except ImportError:  # pragma: no cover - exercised on Windows
    _fcntl = None

try:
    import msvcrt as _msvcrt
except ImportError:  # pragma: no cover - exercised on Unix
    _msvcrt = None


P = ParamSpec("P")
R = TypeVar("R")
LOCK_FILE_NAME = "turn.lock"


class SessionTurnBusyError(RuntimeError):
    pass


@contextmanager
def session_turn_lock(workspace: RunWorkspace) -> Iterator[None]:
    path = workspace.session_dir / LOCK_FILE_NAME
    _validate_lock_path(path)
    workspace.session_dir.mkdir(parents=True, exist_ok=True)
    _validate_lock_path(path)
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except OSError as error:
        raise SessionTurnBusyError(f"Cannot open session turn lock for {workspace.run_id}: {error}") from error
    locked = False
    try:
        try:
            _acquire_lock(descriptor)
            locked = True
        except BlockingIOError as error:
            owner = _read_owner(descriptor)
            detail = f" ({owner})" if owner else ""
            raise SessionTurnBusyError(
                f"Session {workspace.run_id} already has an active agent turn{detail}. "
                "Wait for it to finish or use --fork-session."
            ) from error
        _write_owner(descriptor, workspace.run_id)
        yield
    finally:
        try:
            if locked:
                _release_lock(descriptor)
        finally:
            os.close(descriptor)


def lock_existing_session_turn(func: Callable[P, R]) -> Callable[P, R]:
    signature = inspect.signature(func)

    @wraps(func)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        workspace = signature.bind_partial(*args, **kwargs).arguments.get("workspace")
        if not isinstance(workspace, RunWorkspace):
            return func(*args, **kwargs)
        with session_turn_lock(workspace):
            return func(*args, **kwargs)

    return wrapped


def _write_owner(descriptor: int, run_id: str) -> None:
    payload = {
        "pid": os.getpid(),
        "run_id": run_id,
        "started_at": datetime.now(UTC).isoformat(),
    }
    encoded = (json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    os.ftruncate(descriptor, 0)
    os.lseek(descriptor, 0, os.SEEK_SET)
    os.write(descriptor, encoded)
    os.fsync(descriptor)


def _acquire_lock(descriptor: int) -> None:
    if _fcntl is not None:
        _fcntl.flock(descriptor, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
        return
    if _msvcrt is None:  # pragma: no cover - unsupported interpreter platform
        raise RuntimeError("Session turn locking is unavailable on this platform.")
    if os.fstat(descriptor).st_size == 0:
        os.write(descriptor, b"\n")
    os.lseek(descriptor, 0, os.SEEK_SET)
    try:
        _msvcrt.locking(descriptor, _msvcrt.LK_NBLCK, 1)
    except OSError as error:  # Windows reports lock contention as EACCES.
        raise BlockingIOError(str(error)) from error


def _release_lock(descriptor: int) -> None:
    if _fcntl is not None:
        _fcntl.flock(descriptor, _fcntl.LOCK_UN)
        return
    if _msvcrt is not None:  # pragma: no branch - one backend is always selected
        os.lseek(descriptor, 0, os.SEEK_SET)
        _msvcrt.locking(descriptor, _msvcrt.LK_UNLCK, 1)


def _read_owner(descriptor: int) -> str:
    try:
        os.lseek(descriptor, 0, os.SEEK_SET)
        payload = json.loads(os.read(descriptor, 4_096).decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return ""
    if not isinstance(payload, dict):
        return ""
    pid = payload.get("pid")
    started_at = payload.get("started_at")
    parts = []
    if isinstance(pid, int):
        parts.append(f"pid={pid}")
    if isinstance(started_at, str):
        parts.append(f"started={started_at}")
    return " ".join(parts)


def _validate_lock_path(path: Path) -> None:
    if path.parent.is_symlink() or (path.parent.exists() and not path.parent.is_dir()):
        raise SessionTurnBusyError(f"Session path is not a regular directory: {path.parent}")
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise SessionTurnBusyError(f"Session turn lock is not a regular file: {path}")


__all__ = [
    "LOCK_FILE_NAME",
    "SessionTurnBusyError",
    "lock_existing_session_turn",
    "session_turn_lock",
]
