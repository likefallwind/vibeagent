from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar


CommandOutputObserver = Callable[[str, str], None]

_current_observer: ContextVar[CommandOutputObserver | None] = ContextVar(
    "vibeagent_command_output_observer",
    default=None,
)


@contextmanager
def observe_command_output(observer: CommandOutputObserver) -> Iterator[None]:
    token = _current_observer.set(observer)
    try:
        yield
    finally:
        _current_observer.reset(token)


def current_command_output_observer() -> CommandOutputObserver | None:
    return _current_observer.get()


__all__ = [
    "CommandOutputObserver",
    "current_command_output_observer",
    "observe_command_output",
]
