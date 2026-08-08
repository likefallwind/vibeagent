import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from vibeagent.actions import execute_action, parse_tool_action
from vibeagent.mcp_config import read_mcp_server_configs
from vibeagent.workspace import create_run_workspace


class _McpHttpHandler(BaseHTTPRequestHandler):
    server_version = "McpTest/1.0"

    def log_message(self, format, *args):
        return

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        message = json.loads(self.rfile.read(length))
        self.server.requests.append((self.path, dict(self.headers), message))
        method = message.get("method")
        if self.server.legacy and method == "initialize":
            self._json_response(
                {
                    "jsonrpc": "2.0",
                    "id": message["id"],
                    "result": {
                        "protocolVersion": "2025-11-25",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "legacy-test", "version": "1"},
                    },
                },
                {"Mcp-Session-Id": "test-session"},
            )
            return
        if method == "notifications/initialized":
            self.send_response(202)
            self.end_headers()
            return
        if method == "tools/list":
            result = {
                "tools": [
                    {
                        "name": "echo",
                        "description": "Echo arguments and mirrored headers",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "region": {"type": "string", "x-mcp-header": "Region"},
                                "scope": {
                                    "type": "object",
                                    "properties": {
                                        "tenant": {"type": "integer", "x-mcp-header": "Tenant"}
                                    },
                                },
                            },
                        },
                    },
                    {
                        "name": "invalid",
                        "inputSchema": {
                            "oneOf": [
                                {
                                    "type": "object",
                                    "properties": {
                                        "hidden": {"type": "string", "x-mcp-header": "Invalid"}
                                    },
                                }
                            ]
                        },
                    },
                ]
            }
            response = {"jsonrpc": "2.0", "id": message["id"], "result": result}
            if self.server.sse:
                progress = json.dumps({"jsonrpc": "2.0", "method": "notifications/progress", "params": {}})
                final = json.dumps(response)
                payload = f": keepalive\r\ndata: {progress}\r\n\r\nevent: message\r\ndata: {final}\r\n\r\n".encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            else:
                self._json_response(response)
            return
        if method == "tools/call":
            selected = {
                key: self.headers.get(key)
                for key in ("MCP-Protocol-Version", "Mcp-Method", "Mcp-Name", "Mcp-Param-Region", "Mcp-Param-Tenant", "Authorization", "Mcp-Session-Id")
            }
            self._json_response(
                {
                    "jsonrpc": "2.0",
                    "id": message["id"],
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(selected, sort_keys=True)}],
                        "isError": False,
                    },
                }
            )
            return
        self._json_response({"jsonrpc": "2.0", "id": message.get("id"), "error": {"code": -32601}})

    def do_DELETE(self):
        self.server.deletes.append(dict(self.headers))
        self.send_response(204)
        self.end_headers()

    def _json_response(self, value, headers=None):
        payload = json.dumps(value).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        for key, item in (headers or {}).items():
            self.send_header(key, item)
        self.end_headers()
        self.wfile.write(payload)


class _McpHttpServer:
    def __init__(self, *, legacy=False, sse=False):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _McpHttpHandler)
        self.server.legacy = legacy
        self.server.sse = sse
        self.server.requests = []
        self.server.deletes = []
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server.server_port}/mcp?project=test"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def _write_http_config(root: Path, url: str, **extra) -> None:
    server = {"type": "http", "url": url, **extra}
    (root / ".mcp.json").write_text(json.dumps({"mcpServers": {"remote": server}}), encoding="utf-8")


class McpHttpRuntimeTests(unittest.TestCase):
    def test_modern_json_lists_and_calls_with_metadata_and_mirrored_headers(self) -> None:
        with _McpHttpServer() as server, tempfile.TemporaryDirectory(prefix="vibeagent-mcp-http-") as base:
            root = Path(base)
            _write_http_config(
                root,
                server.url,
                headers={"Authorization": "Bearer ${MCP_HTTP_TOKEN}"},
            )
            workspace = create_run_workspace(root, "run-1")
            with patch.dict(os.environ, {"MCP_HTTP_TOKEN": "secret-token"}):
                listed = execute_action(workspace, parse_tool_action("mcp_tools", {"server": "remote"}))
                called = execute_action(
                    workspace,
                    parse_tool_action(
                        "mcp_call",
                        {
                            "server": "remote",
                            "name": "echo",
                            "arguments": {"region": "Hello, 世界", "scope": {"tenant": 42}},
                        },
                    ),
                )
            servers = execute_action(workspace, parse_tool_action("mcp_servers", {}))

        self.assertTrue(listed.ok)
        self.assertEqual([tool.name for tool in listed.tools], ["echo"])
        self.assertTrue(called.ok)
        output = json.loads(called.output)
        self.assertEqual(output["MCP-Protocol-Version"], "2026-07-28")
        self.assertEqual(output["Mcp-Method"], "tools/call")
        self.assertEqual(output["Mcp-Name"], "echo")
        self.assertEqual(output["Mcp-Param-Region"], "=?base64?SGVsbG8sIOS4lueVjA==?=")
        self.assertEqual(output["Mcp-Param-Tenant"], "42")
        self.assertEqual(output["Authorization"], "Bearer [REDACTED]")
        call_headers = next(headers for _, headers, message in server.server.requests if message.get("method") == "tools/call")
        self.assertEqual(call_headers["Authorization"], "Bearer secret-token")
        list_request = next(message for _, _, message in server.server.requests if message.get("method") == "tools/list")
        self.assertEqual(list_request["params"]["_meta"]["io.modelcontextprotocol/protocolVersion"], "2026-07-28")
        self.assertEqual(servers.servers[0].transport, "http")
        self.assertEqual(servers.servers[0].endpoint, server.url.split("?")[0])
        self.assertEqual(servers.servers[0].header_keys, ["Authorization"])
        self.assertNotIn("secret-token", repr(servers))

    def test_modern_sse_ignores_notifications_and_uses_final_response(self) -> None:
        with _McpHttpServer(sse=True) as server, tempfile.TemporaryDirectory(prefix="vibeagent-mcp-http-") as base:
            root = Path(base)
            _write_http_config(root, server.url)
            workspace = create_run_workspace(root, "run-1")
            observation = execute_action(workspace, parse_tool_action("mcp_tools", {"server": "remote"}))

        self.assertTrue(observation.ok)
        self.assertEqual([tool.name for tool in observation.tools], ["echo"])

    def test_explicit_legacy_protocol_initializes_uses_session_and_deletes_it(self) -> None:
        with _McpHttpServer(legacy=True) as server, tempfile.TemporaryDirectory(prefix="vibeagent-mcp-http-") as base:
            root = Path(base)
            _write_http_config(root, server.url, protocolVersion="2025-11-25")
            workspace = create_run_workspace(root, "run-1")
            observation = execute_action(workspace, parse_tool_action("mcp_tools", {"server": "remote"}))

        self.assertTrue(observation.ok)
        methods = [message.get("method") for _, _, message in server.server.requests]
        self.assertEqual(methods, ["initialize", "notifications/initialized", "tools/list"])
        initialize_headers = server.server.requests[0][1]
        self.assertNotIn("MCP-Protocol-Version", initialize_headers)
        self.assertEqual(server.server.requests[-1][1].get("Mcp-Session-Id"), "test-session")
        self.assertEqual(server.server.deletes[0].get("Mcp-Session-Id"), "test-session")

    def test_redirect_is_not_followed(self) -> None:
        class RedirectHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                return

            def do_POST(self):
                self.send_response(307)
                self.send_header("Location", self.server.target)
                self.end_headers()

        with _McpHttpServer() as target, tempfile.TemporaryDirectory(prefix="vibeagent-mcp-http-") as base:
            redirect = ThreadingHTTPServer(("127.0.0.1", 0), RedirectHandler)
            redirect.target = target.url
            thread = threading.Thread(target=redirect.serve_forever, daemon=True)
            thread.start()
            try:
                root = Path(base)
                _write_http_config(root, f"http://127.0.0.1:{redirect.server_port}/mcp")
                workspace = create_run_workspace(root, "run-1")
                observation = execute_action(workspace, parse_tool_action("mcp_tools", {"server": "remote"}))
            finally:
                redirect.shutdown()
                redirect.server_close()
                thread.join(timeout=2)

        self.assertFalse(observation.ok)
        self.assertIn("status 307", observation.error)
        self.assertEqual(target.server.requests, [])

    def test_http_config_rejects_unsafe_endpoint_headers_and_version(self) -> None:
        invalid_servers = [
            {"type": "http", "url": "ftp://example.com/mcp"},
            {"type": "http", "url": "https://user:pass@example.com/mcp"},
            {"type": "http", "url": "https://example.com/mcp#fragment"},
            {"type": "http", "url": "https://example.com/mcp", "headers": {"Mcp-Name": "override"}},
            {"type": "http", "url": "https://example.com/mcp", "headers": {"X-Test": "bad\nvalue"}},
            {"type": "http", "url": "https://example.com/mcp", "protocolVersion": "unknown"},
        ]
        for server in invalid_servers:
            with self.subTest(server=server), tempfile.TemporaryDirectory(prefix="vibeagent-mcp-http-") as base:
                root = Path(base)
                (root / ".mcp.json").write_text(json.dumps({"mcpServers": {"remote": server}}), encoding="utf-8")
                workspace = create_run_workspace(root, "run-1")
                with self.assertRaises(ValueError):
                    read_mcp_server_configs(workspace)


if __name__ == "__main__":
    unittest.main()
