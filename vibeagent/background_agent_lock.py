from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
from typing import Iterator

from .background_agent_store import (
    background_agent_runtime_root,
    ensure_background_agent_runtime_root,
    ensure_private_directory,
)
from .background_agent_types import BACKGROUND_AGENT_ID_PATTERN

try:
    import fcntl as _fcntl
except ImportError:  # pragma: no cover - exercised on Windows
    _fcntl = None

try:
    import msvcrt as _msvcrt
except ImportError:  # pragma: no cover - exercised on Unix
    _msvcrt = None


@contextmanager
def background_agent_transition_lock(
    project_root: Path,
    agent_id: str,
) -> Iterator[None]:
    root = project_root.resolve()
    _require_agent_id(agent_id)
    ensure_background_agent_runtime_root(root)
    lock_root = ensure_private_directory(background_agent_lock_root(root))
    path = lock_root / f"{agent_id}.lock"
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError(f"Background agent lock is not a regular file: {path}")
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        _acquire_lock(descriptor)
        yield
    finally:
        try:
            _release_lock(descriptor)
        finally:
            os.close(descriptor)


def background_agent_lock_root(project_root: Path) -> Path:
    return background_agent_runtime_root(project_root) / "locks"


def _require_agent_id(agent_id: str) -> None:
    if BACKGROUND_AGENT_ID_PATTERN.fullmatch(agent_id) is None:
        raise ValueError(f"Invalid background agent id: {agent_id}")


def _acquire_lock(descriptor: int) -> None:
    if _fcntl is not None:
        _fcntl.flock(descriptor, _fcntl.LOCK_EX)
        return
    if _msvcrt is None:  # pragma: no cover - unsupported interpreter platform
        raise RuntimeError("Background agent locking is unavailable on this platform.")
    if os.fstat(descriptor).st_size == 0:
        os.write(descriptor, b"\n")
    os.lseek(descriptor, 0, os.SEEK_SET)
    _msvcrt.locking(descriptor, _msvcrt.LK_LOCK, 1)


def _release_lock(descriptor: int) -> None:
    if _fcntl is not None:
        _fcntl.flock(descriptor, _fcntl.LOCK_UN)
    elif _msvcrt is not None:  # pragma: no branch - one backend is always selected
        os.lseek(descriptor, 0, os.SEEK_SET)
        _msvcrt.locking(descriptor, _msvcrt.LK_UNLCK, 1)


__all__ = ["background_agent_transition_lock"]
