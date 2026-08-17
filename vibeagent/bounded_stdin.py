from __future__ import annotations

import sys
from typing import BinaryIO, TextIO


MAX_STDIN_INPUT_BYTES = 10 * 1024**2
STDIN_READ_CHUNK_BYTES = 64 * 1024


def read_bounded_stdin(
    stream: TextIO | None = None,
    *,
    max_bytes: int = MAX_STDIN_INPUT_BYTES,
) -> str:
    if max_bytes < 1:
        raise ValueError("stdin byte limit must be positive.")
    source = sys.stdin if stream is None else stream
    binary_source = getattr(source, "buffer", None)
    if binary_source is not None:
        return _read_binary_stdin(binary_source, max_bytes)
    return _read_text_stdin(source, max_bytes)


def _read_binary_stdin(source: BinaryIO, limit: int) -> str:
    payload = bytearray()
    while True:
        chunk = source.read(min(STDIN_READ_CHUNK_BYTES, limit + 1 - len(payload)))
        if not chunk:
            break
        payload.extend(chunk)
        if len(payload) > limit:
            raise _limit_error(limit)
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("stdin input must be valid UTF-8.") from error


def _read_text_stdin(source: TextIO, limit: int) -> str:
    chunks: list[str] = []
    used_bytes = 0
    while True:
        chunk = source.read(min(STDIN_READ_CHUNK_BYTES, limit + 1 - used_bytes))
        if not chunk:
            break
        used_bytes += len(chunk.encode("utf-8"))
        if used_bytes > limit:
            raise _limit_error(limit)
        chunks.append(chunk)
    return "".join(chunks)


def _limit_error(limit: int) -> ValueError:
    if limit >= 1024**2 and limit % 1024**2 == 0:
        formatted_limit = f"{limit // 1024**2} MiB"
    else:
        formatted_limit = f"{limit} bytes"
    return ValueError(
        f"stdin input exceeds the {formatted_limit} limit; pass large content by file path instead."
    )


__all__ = ["MAX_STDIN_INPUT_BYTES", "STDIN_READ_CHUNK_BYTES", "read_bounded_stdin"]
