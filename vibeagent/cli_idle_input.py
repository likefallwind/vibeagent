from __future__ import annotations

from collections.abc import Callable
from queue import Empty, Queue
import sys
from threading import Event, Thread, current_thread, main_thread


_BUILTIN_INPUT = input


def input_with_idle_callback(
    prompt: str,
    idle_callback: Callable[[], None],
    *,
    input_func: Callable[[str], str],
    interval_seconds: float = 1.0,
) -> str:
    if _can_use_main_thread_terminal_input(input_func):
        return _input_with_background_idle_callback(
            prompt,
            idle_callback,
            input_func=input_func,
            interval_seconds=interval_seconds,
        )

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


def _input_with_background_idle_callback(
    prompt: str,
    idle_callback: Callable[[], None],
    *,
    input_func: Callable[[str], str],
    interval_seconds: float,
) -> str:
    stop = Event()
    errors: Queue[BaseException] = Queue(maxsize=1)

    def run_idle_callbacks() -> None:
        while not stop.wait(interval_seconds):
            try:
                idle_callback()
            except BaseException as error:
                errors.put(error)
                return

    worker = Thread(target=run_idle_callbacks, name="vibeagent-idle", daemon=True)
    worker.start()
    input_error: BaseException | None = None
    value = ""
    try:
        value = input_func(prompt)
    except BaseException as error:
        input_error = error
    finally:
        stop.set()
        worker.join()

    if input_error is not None:
        raise input_error
    if not errors.empty():
        raise errors.get_nowait()
    return value


def _can_use_main_thread_terminal_input(input_func: Callable[[str], str]) -> bool:
    if input_func is not _BUILTIN_INPUT or current_thread() is not main_thread():
        return False
    try:
        return sys.stdin.isatty()
    except (AttributeError, OSError):
        return False


__all__ = ["input_with_idle_callback"]
