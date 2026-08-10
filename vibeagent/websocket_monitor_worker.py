from __future__ import annotations

import json
import socket
import sys
from pathlib import Path
from typing import Callable

from websockets.exceptions import ConnectionClosed
from websockets.sync.client import connect

from .action_process_types import MonitorWebSocketSource
from .redaction import redact_sensitive_text
from .websocket_monitor_safety import (
    parse_websocket_source,
    resolve_public_websocket_endpoint,
)


MAX_WEBSOCKET_MESSAGE_BYTES = 1_048_576


def stream_websocket_events(
    source: MonitorWebSocketSource,
    *,
    connect_func: Callable[..., object] = connect,
) -> int:
    parsed, addresses = resolve_public_websocket_endpoint(source)
    port = parsed.port or (443 if parsed.scheme == "wss" else 80)
    raw_socket = _connect_public_address(addresses, port)
    try:
        connection = connect_func(
            source.url,
            sock=raw_socket,
            subprotocols=list(source.protocols) or None,
            proxy=None,
            open_timeout=10,
            close_timeout=5,
            max_size=MAX_WEBSOCKET_MESSAGE_BYTES,
        )
    except Exception:
        raw_socket.close()
        raise
    try:
        with connection:  # type: ignore[attr-defined]
            while True:
                try:
                    message = connection.recv()  # type: ignore[attr-defined]
                except ConnectionClosed as closed:
                    close_code = closed.rcvd.code if closed.rcvd is not None else None
                    _emit(
                        "close",
                        f"WebSocket closed with code {close_code if close_code is not None else 'unknown'}.",
                        close_code=close_code,
                    )
                    return 0
                if isinstance(message, bytes):
                    _emit("binary", f"[binary frame, {len(message)} bytes]")
                    continue
                encoded_size = len(message.encode("utf-8"))
                if encoded_size > MAX_WEBSOCKET_MESSAGE_BYTES:
                    raise ValueError(
                        f"WebSocket text message exceeded {MAX_WEBSOCKET_MESSAGE_BYTES} bytes."
                    )
                _emit("text", message)
    except Exception as error:
        print(
            "WebSocket monitor failed: "
            + redact_sensitive_text(f"{type(error).__name__}: {error}"),
            file=sys.stderr,
            flush=True,
        )
        return 1


def load_websocket_source(path: Path) -> MonitorWebSocketSource:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    finally:
        path.unlink(missing_ok=True)
    return parse_websocket_source(payload)


def _connect_public_address(addresses: tuple[object, ...], port: int) -> socket.socket:
    errors: list[str] = []
    for address in addresses:
        try:
            return socket.create_connection((str(address), port), timeout=10)
        except OSError as error:
            errors.append(str(error))
    detail = "; ".join(errors[-3:]) or "no public addresses"
    raise OSError(f"Could not connect to a resolved public WebSocket address: {detail}")


def _emit(kind: str, message: str, *, close_code: int | None = None) -> None:
    print(
        json.dumps(
            {"kind": kind, "message": message, "closeCode": close_code},
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        flush=True,
    )


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("WebSocket monitor worker requires one config path.", file=sys.stderr)
        return 2
    try:
        source = load_websocket_source(Path(args[0]))
        return stream_websocket_events(source)
    except Exception as error:
        print(
            "WebSocket monitor setup failed: "
            + redact_sensitive_text(f"{type(error).__name__}: {error}"),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
