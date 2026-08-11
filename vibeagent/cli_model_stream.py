from __future__ import annotations

import sys
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from typing import Any, Iterator, TextIO

from .model_streaming import supports_model_streaming


class TerminalModelStreamRenderer:
    """Render only user-facing text deltas from provider stream events."""

    def __init__(
        self,
        output: TextIO | None = None,
        *,
        on_display_start: Callable[[], None] | None = None,
        on_display_end: Callable[[], None] | None = None,
    ) -> None:
        self.output = output if output is not None else sys.stdout
        self._lock = Lock()
        self._active_key: tuple[int, int] | None = None
        self._chunks: list[str] = []
        self._line_open = False
        self._last_completed_text = ""
        self._message_started = False
        self._display_active = False
        self._on_display_start = on_display_start
        self._on_display_end = on_display_end

    def agent_event(
        self,
        _session_dir: Path,
        iteration: int,
        attempt: int,
        event: dict[str, Any],
    ) -> None:
        self._consume((iteration, attempt), event)

    def chat_event(self, attempt: int, event: dict[str, Any]) -> None:
        self._consume((1, attempt), event)

    def finish(self) -> None:
        with self._lock:
            self._finish_line()
            self._end_display()

    def matches_final_message(self, message: str | None) -> bool:
        return bool(
            message
            and self._last_completed_text
            and message.strip() == self._last_completed_text
        )

    def _consume(self, key: tuple[int, int], event: dict[str, Any]) -> None:
        with self._lock:
            if key != self._active_key:
                previous = self._active_key
                self._finish_line()
                self._active_key = key
                self._chunks = []
                self._last_completed_text = ""
                self._message_started = False
                if previous is not None and key[0] == previous[0] and key[1] > previous[1]:
                    self._start_display()
                    self.output.write(f"\nModel response retry {key[1]}:\n")
                    self.output.flush()

            if event.get("type") == "message_start":
                if self._message_started:
                    self._finish_line()
                    self._chunks = []
                    self._last_completed_text = ""
                    self._start_display()
                    self.output.write("\nModel response restarted:\n")
                    self.output.flush()
                self._message_started = True
                return

            if event.get("type") == "content_block_delta":
                delta = event.get("delta")
                if isinstance(delta, dict) and delta.get("type") == "text_delta":
                    text = delta.get("text")
                    if isinstance(text, str) and text:
                        if not self._line_open:
                            self._start_display()
                            self.output.write("\n")
                            self._line_open = True
                        self._chunks.append(text)
                        self.output.write(text)
                        self.output.flush()
                return

            if event.get("type") == "message_stop":
                self._finish_line()
                self._last_completed_text = "".join(self._chunks).strip()
                self._end_display()

    def _finish_line(self) -> None:
        if not self._line_open:
            return
        self.output.write("\n")
        self.output.flush()
        self._line_open = False

    def _start_display(self) -> None:
        if self._display_active:
            return
        if self._on_display_start is not None:
            self._on_display_start()
        self._display_active = True

    def _end_display(self) -> None:
        if not self._display_active:
            return
        self._display_active = False
        if self._on_display_end is not None:
            self._on_display_end()


@contextmanager
def terminal_model_stream_scope(
    client: object,
    *,
    output: TextIO | None = None,
    on_display_start: Callable[[], None] | None = None,
    on_display_end: Callable[[], None] | None = None,
) -> Iterator[TerminalModelStreamRenderer | None]:
    renderer = (
        TerminalModelStreamRenderer(
            output,
            on_display_start=on_display_start,
            on_display_end=on_display_end,
        )
        if supports_model_streaming(client)
        else None
    )
    try:
        yield renderer
    finally:
        if renderer is not None:
            renderer.finish()


__all__ = ["TerminalModelStreamRenderer", "terminal_model_stream_scope"]
