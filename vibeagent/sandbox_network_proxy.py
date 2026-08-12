from __future__ import annotations

import os
import re
import socket
import threading
from urllib.parse import urlsplit

from .sandbox_network_policy import sandbox_domain_allowed


MAX_PROXY_HEADER_BYTES = 64 * 1024
PROXY_IO_TIMEOUT_SECONDS = 30
_HTTP_TOKEN = re.compile(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+")


class SandboxNetworkProxy:
    def __init__(
        self,
        socket_path: str,
        *,
        allowed_domains: tuple[str, ...],
        denied_domains: tuple[str, ...],
    ) -> None:
        self.socket_path = socket_path
        self.allowed_domains = allowed_domains
        self.denied_domains = denied_domains
        self._listener: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._closed = threading.Event()

    def start(self) -> None:
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(self.socket_path)
        listener.listen(64)
        listener.settimeout(0.2)
        self._listener = listener
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def close(self) -> None:
        self._closed.set()
        listener = self._listener
        if listener is not None:
            listener.close()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=1)
        try:
            os.unlink(self.socket_path)
        except FileNotFoundError:
            pass

    def __enter__(self) -> SandboxNetworkProxy:
        self.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _serve(self) -> None:
        assert self._listener is not None
        while not self._closed.is_set():
            try:
                client, _address = self._listener.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            threading.Thread(target=self._handle_client, args=(client,), daemon=True).start()

    def _handle_client(self, client: socket.socket) -> None:
        with client:
            client.settimeout(PROXY_IO_TIMEOUT_SECONDS)
            try:
                request = _read_proxy_header(client)
                method, target, version, headers, remainder = _parse_proxy_request(request)
                hostname, port, upstream_request = _proxy_destination(
                    method, target, version, headers, remainder
                )
                if not sandbox_domain_allowed(
                    hostname, self.allowed_domains, self.denied_domains
                ):
                    _send_proxy_error(client, 403, "Domain blocked by sandbox policy")
                    return
                with socket.create_connection(
                    (hostname, port), timeout=PROXY_IO_TIMEOUT_SECONDS
                ) as upstream:
                    upstream.settimeout(None)
                    if method == "CONNECT":
                        client.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                    else:
                        upstream.sendall(upstream_request)
                    _relay_bidirectional(client, upstream)
            except (OSError, TimeoutError, ValueError):
                try:
                    _send_proxy_error(client, 502, "Sandbox proxy request failed")
                except OSError:
                    pass


def _read_proxy_header(client: socket.socket) -> bytes:
    data = bytearray()
    while b"\r\n\r\n" not in data:
        chunk = client.recv(min(16_384, MAX_PROXY_HEADER_BYTES + 1 - len(data)))
        if not chunk:
            raise ValueError("Proxy request ended before headers were complete.")
        data.extend(chunk)
        if len(data) > MAX_PROXY_HEADER_BYTES:
            raise ValueError("Proxy request headers are too large.")
    return bytes(data)


def _parse_proxy_request(
    request: bytes,
) -> tuple[str, str, str, list[tuple[str, str]], bytes]:
    header, remainder = request.split(b"\r\n\r\n", 1)
    try:
        lines = header.decode("iso-8859-1").split("\r\n")
        method, target, version = lines[0].split(" ", 2)
    except (UnicodeDecodeError, ValueError) as error:
        raise ValueError("Invalid HTTP proxy request line.") from error
    if (
        not method.isascii()
        or not method.isalpha()
        or any(ord(char) < 32 or ord(char) == 127 for char in target)
        or version not in {"HTTP/1.0", "HTTP/1.1"}
    ):
        raise ValueError("Invalid HTTP proxy request line.")
    headers: list[tuple[str, str]] = []
    for line in lines[1:]:
        if ":" not in line:
            raise ValueError("Invalid HTTP proxy header.")
        name, value = line.split(":", 1)
        if _HTTP_TOKEN.fullmatch(name) is None or any(
            ord(char) < 32 and char != "\t" for char in value
        ):
            raise ValueError("Invalid HTTP proxy header.")
        headers.append((name, value.lstrip()))
    return method.upper(), target, version, headers, remainder


def _proxy_destination(
    method: str,
    target: str,
    version: str,
    headers: list[tuple[str, str]],
    remainder: bytes,
) -> tuple[str, int, bytes]:
    if method == "CONNECT":
        hostname, port = _parse_authority(target, default_port=443)
        return hostname, port, b""
    parsed = urlsplit(target)
    if parsed.scheme != "http" or parsed.hostname is None or parsed.username is not None:
        raise ValueError("Plain proxy requests require an absolute HTTP URL.")
    if parsed.fragment:
        raise ValueError("Proxy request URLs must not contain fragments.")
    try:
        parsed_port = parsed.port
    except ValueError as error:
        raise ValueError("Invalid proxy destination port.") from error
    port = 80 if parsed_port is None else parsed_port
    if not 1 <= port <= 65_535:
        raise ValueError("Invalid proxy destination port.")
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    filtered_headers = [
        (name, value)
        for name, value in headers
        if name.lower() not in {"host", "proxy-authorization", "proxy-connection"}
    ]
    host_header = parsed.hostname
    if port != 80:
        host_header = f"{host_header}:{port}"
    filtered_headers.insert(0, ("Host", host_header))
    rendered_headers = "\r\n".join(f"{name}: {value}" for name, value in filtered_headers)
    upstream_request = (
        f"{method} {path} {version}\r\n{rendered_headers}\r\n\r\n".encode("iso-8859-1")
        + remainder
    )
    return parsed.hostname, port, upstream_request


def _parse_authority(value: str, *, default_port: int) -> tuple[str, int]:
    parsed = urlsplit(f"//{value}")
    if (
        parsed.hostname is None
        or parsed.username is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Invalid proxy destination.")
    try:
        parsed_port = parsed.port
    except ValueError as error:
        raise ValueError("Invalid proxy destination port.") from error
    port = default_port if parsed_port is None else parsed_port
    if not 1 <= port <= 65_535:
        raise ValueError("Invalid proxy destination port.")
    return parsed.hostname, port


def _send_proxy_error(client: socket.socket, status: int, message: str) -> None:
    body = f"{message}\n".encode("utf-8")
    client.sendall(
        f"HTTP/1.1 {status} Sandbox Proxy Error\r\n"
        f"Content-Type: text/plain; charset=utf-8\r\n"
        f"Content-Length: {len(body)}\r\n"
        "Connection: close\r\n\r\n".encode("ascii")
        + body
    )


def _relay_bidirectional(left: socket.socket, right: socket.socket) -> None:
    left.settimeout(None)
    right.settimeout(None)
    threads = (
        threading.Thread(target=_copy_socket, args=(left, right), daemon=True),
        threading.Thread(target=_copy_socket, args=(right, left), daemon=True),
    )
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()


def _copy_socket(source: socket.socket, destination: socket.socket) -> None:
    try:
        while True:
            chunk = source.recv(65_536)
            if not chunk:
                break
            destination.sendall(chunk)
    except OSError:
        pass
    finally:
        try:
            destination.shutdown(socket.SHUT_WR)
        except OSError:
            pass


__all__ = ["SandboxNetworkProxy"]
