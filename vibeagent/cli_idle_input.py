from __future__ import annotations

from collections.abc import Callable
from queue import Empty, Queue
from threading import Thread


def input_with_idle_callback(
    prompt: str,
    idle_callback: Callable[[], None],
    *,
    input_func: Callable[[str], str],
    interval_seconds: float = 1.0,
) -> str:
    results: Queue[tuple[bool, object]] = Queue(maxsize=1)

    def read_input() -> None:
        try:
            results.put((True, input_func(prompt)))
        except BaseException as error:
            results.put((False, error))

    Thread(target=read_input, name="vibeagent-input", daemon=True).start()
    while True:
        try:
            ok, value = results.get(timeout=interval_seconds)
        except Empty:
            idle_callback()
            continue
        if ok:
            return str(value)
        assert isinstance(value, BaseException)
        raise value


__all__ = ["input_with_idle_callback"]
