from __future__ import annotations

import shlex
from urllib.parse import urlparse


def parse_port_request(
    argument: str | None = None,
    port: int | None = None,
    host: str = "127.0.0.1",
    timeout_ms: int = 1_000,
) -> tuple[int, str, int]:
    selected_port = port
    selected_host = host
    selected_timeout_ms = timeout_ms
    if argument and argument.strip():
        if port is not None:
            raise ValueError("port argument cannot be combined with explicit port.")
        try:
            parts = shlex.split(argument)
        except ValueError as error:
            raise ValueError(str(error)) from error
        if len(parts) > 3:
            raise ValueError("expected port, optional host, and optional timeout ms.")
        if parts:
            if not parts[0].isdigit():
                raise ValueError(f"invalid port: {parts[0]}")
            selected_port = int(parts[0])
        if len(parts) == 2:
            if parts[1].isdigit():
                selected_timeout_ms = int(parts[1])
            else:
                selected_host = parts[1]
        if len(parts) == 3:
            selected_host = parts[1]
            if not parts[2].isdigit():
                raise ValueError(f"invalid timeout ms: {parts[2]}")
            selected_timeout_ms = int(parts[2])
    if selected_port is None:
        raise ValueError("port is required.")
    if selected_port < 1 or selected_port > 65_535:
        raise ValueError("port must be between 1 and 65535.")
    if not selected_host.strip():
        raise ValueError("host must be a non-empty string.")
    return selected_port, selected_host.strip(), selected_timeout_ms


def parse_http_fetch_request(argument: str | None = None, url: str | None = None) -> str:
    selected_url = url.strip() if url else None
    if argument and argument.strip():
        if url is not None:
            raise ValueError("http-fetch argument cannot be combined with explicit url.")
        try:
            parts = shlex.split(argument)
        except ValueError as error:
            raise ValueError(str(error)) from error
        if len(parts) > 1:
            raise ValueError("http-fetch accepts only one URL.")
        selected_url = parts[0] if parts else None
    if not selected_url:
        raise ValueError("url is required.")
    parsed = urlparse(selected_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("url must be an http or https URL.")
    return selected_url


def parse_http_request(argument: str | None = None, url: str | None = None, contains: str | None = None) -> tuple[str, str | None]:
    selected_url = url.strip() if url else None
    selected_contains = contains
    if argument and argument.strip():
        if url is not None or contains is not None:
            raise ValueError("http argument cannot be combined with explicit url or contains.")
        try:
            parts = shlex.split(argument)
        except ValueError as error:
            raise ValueError(str(error)) from error
        if not parts:
            raise ValueError("url is required.")
        selected_url = parts[0]
        selected_contains = " ".join(parts[1:]) if len(parts) > 1 else None
    if not selected_url:
        raise ValueError("url is required.")
    if not (selected_url.startswith("http://") or selected_url.startswith("https://")):
        raise ValueError("url must be an http or https URL.")
    if selected_contains is not None and not selected_contains:
        raise ValueError("contains must be a non-empty string.")
    return selected_url, selected_contains
