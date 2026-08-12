from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import socket
import tempfile
from threading import Thread
import unittest

from vibeagent.sandbox_network_policy import (
    normalize_sandbox_domains,
    sandbox_domain_allowed,
    sandbox_domain_matches,
)
from vibeagent.sandbox_network_proxy import SandboxNetworkProxy


class SandboxNetworkPolicyTests(unittest.TestCase):
    def test_normalizes_idna_and_matches_only_wildcard_subdomains(self) -> None:
        domains = normalize_sandbox_domains(
            ["Example.COM", "*.example.com", "example.com"],
            field="allowedDomains",
        )

        self.assertEqual(domains, ("example.com", "*.example.com"))
        self.assertTrue(sandbox_domain_matches("example.com", "example.com"))
        self.assertTrue(sandbox_domain_matches("api.example.com", "*.example.com"))
        self.assertFalse(sandbox_domain_matches("example.com", "*.example.com"))
        self.assertFalse(sandbox_domain_matches("notexample.com", "*.example.com"))

    def test_denied_domains_override_allowed_domains(self) -> None:
        self.assertFalse(
            sandbox_domain_allowed(
                "private.example.com",
                ("*.example.com",),
                ("private.example.com",),
            )
        )
        self.assertTrue(
            sandbox_domain_allowed(
                "public.example.com",
                ("*.example.com",),
                ("private.example.com",),
            )
        )

    def test_rejects_urls_ports_and_unsafe_wildcards(self) -> None:
        for value in ("https://example.com", "example.com:443", "*", "foo.*.com"):
            with self.subTest(value=value), self.assertRaisesRegex(
                ValueError, "invalid domain"
            ):
                normalize_sandbox_domains([value], field="allowedDomains")


class SandboxNetworkProxyTests(unittest.TestCase):
    def test_plain_http_proxy_allows_exact_host_and_denied_host_wins(self) -> None:
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                body = b"proxy-ok"
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, _format: str, *_args: object) -> None:
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server_thread = Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        try:
            port = server.server_address[1]
            with tempfile.TemporaryDirectory(prefix="vibeagent-proxy-") as base:
                socket_path = Path(base) / "proxy.sock"
                with SandboxNetworkProxy(
                    socket_path.as_posix(),
                    allowed_domains=("127.0.0.1",),
                    denied_domains=(),
                ):
                    allowed = _proxy_request(socket_path, port)
                with SandboxNetworkProxy(
                    socket_path.as_posix(),
                    allowed_domains=("127.0.0.1",),
                    denied_domains=("127.0.0.1",),
                ):
                    denied = _proxy_request(socket_path, port)
        finally:
            server.shutdown()
            server.server_close()
            server_thread.join(timeout=2)

        self.assertIn(b"200 OK", allowed)
        self.assertTrue(allowed.endswith(b"proxy-ok"))
        self.assertIn(b"403 Sandbox Proxy Error", denied)

    def test_connect_proxy_opens_only_an_allowed_tunnel(self) -> None:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]

        def echo_once() -> None:
            connection, _address = listener.accept()
            with connection:
                connection.sendall(connection.recv(32))

        echo_thread = Thread(target=echo_once, daemon=True)
        echo_thread.start()
        try:
            with tempfile.TemporaryDirectory(prefix="vibeagent-proxy-") as base:
                socket_path = Path(base) / "proxy.sock"
                with SandboxNetworkProxy(
                    socket_path.as_posix(),
                    allowed_domains=("127.0.0.1",),
                    denied_domains=(),
                ):
                    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                        client.connect(socket_path.as_posix())
                        client.sendall(
                            f"CONNECT 127.0.0.1:{port} HTTP/1.1\r\n\r\n".encode("ascii")
                        )
                        response = _read_until(client, b"\r\n\r\n")
                        client.sendall(b"tunnel-ok")
                        echoed = client.recv(32)
        finally:
            listener.close()
            echo_thread.join(timeout=2)

        self.assertIn(b"200 Connection Established", response)
        self.assertEqual(echoed, b"tunnel-ok")

    def test_connect_proxy_rejects_zero_ports_and_authority_queries(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-proxy-") as base:
            socket_path = Path(base) / "proxy.sock"
            with SandboxNetworkProxy(
                socket_path.as_posix(),
                allowed_domains=("127.0.0.1",),
                denied_domains=(),
            ):
                zero_port = _raw_proxy_request(
                    socket_path,
                    b"CONNECT 127.0.0.1:0 HTTP/1.1\r\n\r\n",
                )
                query = _raw_proxy_request(
                    socket_path,
                    b"CONNECT 127.0.0.1:443?target=elsewhere HTTP/1.1\r\n\r\n",
                )

        self.assertIn(b"502 Sandbox Proxy Error", zero_port)
        self.assertIn(b"502 Sandbox Proxy Error", query)


def _proxy_request(socket_path: Path, port: int) -> bytes:
    return _raw_proxy_request(
        socket_path,
        (
            f"GET http://127.0.0.1:{port}/ HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{port}\r\nConnection: close\r\n\r\n"
        ).encode("ascii"),
    )


def _raw_proxy_request(socket_path: Path, request: bytes) -> bytes:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.connect(socket_path.as_posix())
        client.sendall(request)
        chunks: list[bytes] = []
        while True:
            chunk = client.recv(65_536)
            if not chunk:
                return b"".join(chunks)
            chunks.append(chunk)


def _read_until(client: socket.socket, marker: bytes) -> bytes:
    data = bytearray()
    while marker not in data:
        chunk = client.recv(4_096)
        if not chunk:
            break
        data.extend(chunk)
    return bytes(data)


if __name__ == "__main__":
    unittest.main()
