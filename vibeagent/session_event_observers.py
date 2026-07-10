from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from typing import Any


SessionEventObserver = Callable[[Path, dict[str, Any]], None]

_observer_lock = RLock()
_observers: dict[Path, list[SessionEventObserver]] = {}


@contextmanager
def observe_session_events(session_dir: Path, observer: SessionEventObserver) -> Iterator[None]:
    key = session_dir.resolve()
    with _observer_lock:
        _observers.setdefault(key, []).append(observer)
    try:
        yield
    finally:
        with _observer_lock:
            observers = _observers.get(key, [])
            if observer in observers:
                observers.remove(observer)
            if not observers:
                _observers.pop(key, None)


def notify_session_event_observers(session_dir: Path, event: dict[str, Any]) -> None:
    key = session_dir.resolve()
    with _observer_lock:
        observers = tuple(_observers.get(key, ()))
    for observer in observers:
        observer(session_dir, event)


__all__ = ["SessionEventObserver", "notify_session_event_observers", "observe_session_events"]
