from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from typing import Any


MAX_SSE_EVENT_BYTES = 2 * 1024 * 1024


class SseProtocolError(RuntimeError):
    pass


def iter_sse_json(
    lines: Iterable[bytes | str],
    *,
    max_event_bytes: int = MAX_SSE_EVENT_BYTES,
) -> Iterator[dict[str, Any]]:
    data_lines: list[str] = []
    event_bytes = 0

    def decode_event() -> dict[str, Any] | None:
        nonlocal data_lines, event_bytes
        if not data_lines:
            return None
        payload = "\n".join(data_lines)
        data_lines = []
        event_bytes = 0
        if payload == "[DONE]":
            return None
        try:
            event = json.loads(payload)
        except json.JSONDecodeError as error:
            raise SseProtocolError(f"SSE event data was not valid JSON: {error}") from error
        if not isinstance(event, dict):
            raise SseProtocolError("SSE event data must be a JSON object.")
        return event

    for raw_line in lines:
        if isinstance(raw_line, bytes):
            try:
                line = raw_line.decode("utf-8")
            except UnicodeDecodeError as error:
                raise SseProtocolError(f"SSE stream was not valid UTF-8: {error}") from error
        else:
            line = raw_line
        line = line.rstrip("\r\n")
        if not line:
            event = decode_event()
            if event is not None:
                yield event
            continue
        if line.startswith(":"):
            continue
        field, separator, value = line.partition(":")
        if separator and value.startswith(" "):
            value = value[1:]
        if field != "data":
            continue
        event_bytes += len(value.encode("utf-8"))
        if event_bytes > max_event_bytes:
            raise SseProtocolError(f"SSE event exceeded the {max_event_bytes}-byte limit.")
        data_lines.append(value)

    event = decode_event()
    if event is not None:
        yield event


__all__ = ["MAX_SSE_EVENT_BYTES", "SseProtocolError", "iter_sse_json"]
