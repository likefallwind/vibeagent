from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import SplitResult, urlsplit

from .action_process_types import MonitorWebSocketSource


MAX_WEBSOCKET_PROTOCOLS = 20
MAX_WEBSOCKET_PROTOCOL_CHARS = 128
_PROTOCOL_TOKEN = re.compile(r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+")


def parse_websocket_source(value: object) -> MonitorWebSocketSource:
    if not isinstance(value, dict):
        raise ValueError("monitor ws must be an object.")
    if set(value) - {"url", "protocols"}:
        raise ValueError("monitor ws supports only url and protocols.")
    url = value.get("url")
    if not isinstance(url, str):
        raise ValueError("monitor ws.url must be a string.")
    _parse_websocket_url(url)
    raw_protocols = value.get("protocols", [])
    if not isinstance(raw_protocols, list):
        raise ValueError("monitor ws.protocols must be a list of strings.")
    if len(raw_protocols) > MAX_WEBSOCKET_PROTOCOLS:
        raise ValueError(
            f"monitor ws.protocols must contain at most {MAX_WEBSOCKET_PROTOCOLS} entries."
        )
    protocols: list[str] = []
    for protocol in raw_protocols:
        if (
            not isinstance(protocol, str)
            or not protocol
            or len(protocol) > MAX_WEBSOCKET_PROTOCOL_CHARS
            or _PROTOCOL_TOKEN.fullmatch(protocol) is None
        ):
            raise ValueError("monitor ws.protocols entries must be valid WebSocket subprotocol tokens.")
        if protocol in protocols:
            raise ValueError("monitor ws.protocols must not contain duplicates.")
        protocols.append(protocol)
    return MonitorWebSocketSource(url=url, protocols=tuple(protocols))


def resolve_public_websocket_endpoint(
    source: MonitorWebSocketSource,
) -> tuple[SplitResult, tuple[ipaddress.IPv4Address | ipaddress.IPv6Address, ...]]:
    parsed = _parse_websocket_url(source.url)
    assert parsed.hostname is not None
    port = parsed.port or (443 if parsed.scheme == "wss" else 80)
    try:
        addresses = {
            ipaddress.ip_address(item[4][0])
            for item in socket.getaddrinfo(
                parsed.hostname,
                port,
                type=socket.SOCK_STREAM,
            )
        }
    except (socket.gaierror, ValueError) as error:
        raise ValueError(
            f"Could not resolve WebSocket host {parsed.hostname!r}: {error}."
        ) from error
    if not addresses:
        raise ValueError(
            f"WebSocket host {parsed.hostname!r} did not resolve to an IP address."
        )
    rejected = sorted(
        (
            address
            for address in addresses
            if not address.is_global
            or address.is_multicast
            or address.is_reserved
            or address.is_unspecified
        ),
        key=str,
    )
    if rejected:
        rendered = ", ".join(str(address) for address in rejected)
        raise ValueError(
            "WebSocket host must resolve only to public addresses; "
            f"rejected: {rendered}."
        )
    return parsed, tuple(sorted(addresses, key=str))


def _parse_websocket_url(url: str) -> SplitResult:
    if (
        not url
        or not url.isascii()
        or any(ord(character) < 0x21 or ord(character) > 0x7E for character in url)
        or "\\" in url
    ):
        raise ValueError(
            "monitor ws.url must contain printable ASCII without whitespace or backslashes."
        )
    parsed = urlsplit(url)
    if parsed.scheme not in {"ws", "wss"} or not parsed.hostname:
        raise ValueError("monitor ws.url must use ws:// or wss:// and include a host.")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("monitor ws.url credentials are not allowed.")
    if parsed.fragment:
        raise ValueError("monitor ws.url fragments are not allowed.")
    try:
        parsed.port
    except ValueError as error:
        raise ValueError(f"monitor ws.url has an invalid port: {error}.") from error
    return parsed


__all__ = [
    "parse_websocket_source",
    "resolve_public_websocket_endpoint",
]
