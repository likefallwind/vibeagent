from __future__ import annotations

from collections.abc import Iterator
from typing import TextIO


TEXT_LINE_READ_CHUNK_CHARS = 64 * 1024


class TextLineTooLongError(ValueError):
    def __init__(self, *, max_bytes: int, observed_bytes: int) -> None:
        super().__init__(f"Text line exceeds {max_bytes} UTF-8 bytes.")
        self.max_bytes = max_bytes
        self.observed_bytes = observed_bytes


def iter_bounded_text_lines(
    stream: TextIO,
    *,
    max_line_bytes: int,
    chunk_chars: int = TEXT_LINE_READ_CHUNK_CHARS,
) -> Iterator[str]:
    if max_line_bytes < 1:
        raise ValueError("Text line byte limit must be positive.")
    if chunk_chars < 1:
        raise ValueError("Text line read chunk size must be positive.")

    parts: list[str] = []
    total_bytes = 0
    while True:
        chunk = stream.readline(chunk_chars)
        if not chunk:
            if parts:
                yield "".join(parts)
            return
        total_bytes += len(chunk.encode("utf-8"))
        if total_bytes > max_line_bytes:
            raise TextLineTooLongError(max_bytes=max_line_bytes, observed_bytes=total_bytes)
        parts.append(chunk)
        if chunk.endswith("\n"):
            yield "".join(parts)
            parts = []
            total_bytes = 0


__all__ = [
    "TEXT_LINE_READ_CHUNK_CHARS",
    "TextLineTooLongError",
    "iter_bounded_text_lines",
]
