from __future__ import annotations

import json
from typing import BinaryIO


LSP_MAX_HEADER_BYTES = 16_384
LSP_MAX_MESSAGE_BYTES = 8_000_000


def read_lsp_message(stream: BinaryIO) -> dict[str, object]:
    headers: dict[str, str] = {}
    consumed = 0
    while True:
        line = stream.readline(LSP_MAX_HEADER_BYTES + 1)
        if not line:
            raise EOFError("LSP server closed stdout.")
        consumed += len(line)
        if consumed > LSP_MAX_HEADER_BYTES:
            raise ValueError("LSP response headers are too large.")
        if line in {b"\r\n", b"\n"}:
            break
        try:
            name, value = line.decode("ascii").split(":", 1)
        except (UnicodeDecodeError, ValueError) as error:
            raise ValueError("LSP response contains an invalid header.") from error
        headers[name.strip().lower()] = value.strip()
    length_text = headers.get("content-length")
    if length_text is None or not length_text.isdigit():
        raise ValueError("LSP response is missing a valid Content-Length header.")
    length = int(length_text)
    if length > LSP_MAX_MESSAGE_BYTES:
        raise ValueError(f"LSP response exceeds {LSP_MAX_MESSAGE_BYTES} bytes.")
    payload = stream.read(length)
    if len(payload) != length:
        raise EOFError("LSP server closed stdout during a response.")
    try:
        message = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"LSP response is invalid JSON: {error}") from error
    if not isinstance(message, dict):
        raise ValueError("LSP response must be a JSON object.")
    return message


def encode_lsp_message(message: dict[str, object]) -> bytes:
    payload = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(payload) > LSP_MAX_MESSAGE_BYTES:
        raise ValueError(f"LSP request exceeds {LSP_MAX_MESSAGE_BYTES} bytes.")
    return f"Content-Length: {len(payload)}\r\n\r\n".encode("ascii") + payload


__all__ = ["encode_lsp_message", "read_lsp_message"]
