from __future__ import annotations

import json
import os
import selectors
import subprocess
import tempfile
import time
from typing import Any

from . import __version__
from .mcp_config import McpServerConfig, expanded_mcp_environment
from .workspace_core import RunWorkspace


MCP_PROTOCOL_VERSION = "2025-11-25"
MCP_MAX_MESSAGE_BYTES = 1_000_000
MCP_MAX_TOOLS = 500
MCP_MAX_PAGES = 20


class McpProtocolError(RuntimeError):
    pass


class McpStdioClient:
    def __init__(self, workspace: RunWorkspace, config: McpServerConfig, timeout_ms: int) -> None:
        self.workspace = workspace
        self.config = config
        self.timeout_ms = timeout_ms
        self.process: subprocess.Popen[bytes] | None = None
        self.stderr_file = tempfile.TemporaryFile()
        self.buffer = bytearray()
        self.next_id = 1

    def __enter__(self) -> "McpStdioClient":
        try:
            self.process = subprocess.Popen(
                self.config.argv,
                cwd=self.workspace.root / self.config.cwd,
                env=expanded_mcp_environment(self.config),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=self.stderr_file,
            )
            initialized = self.request(
                "initialize",
                {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "vibeagent", "version": __version__},
                },
            )
            version = initialized.get("protocolVersion") if isinstance(initialized, dict) else None
            if not isinstance(version, str):
                raise McpProtocolError("MCP initialize result did not include protocolVersion.")
            self.notify("notifications/initialized", {})
            return self
        except Exception:
            self.close()
            raise

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    def close(self) -> None:
        process = self.process
        if process is None:
            if not self.stderr_file.closed:
                self.stderr_file.close()
            return
        if process.stdin:
            try:
                process.stdin.close()
            except BrokenPipeError:
                pass
        try:
            process.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=0.5)
        if process.stdout:
            process.stdout.close()
        if not self.stderr_file.closed:
            self.stderr_file.close()
        self.process = None

    def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        request_id = self.next_id
        self.next_id += 1
        self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        deadline = time.monotonic() + self.timeout_ms / 1000
        while True:
            message = self._read_message(deadline)
            if "method" in message:
                if "id" in message:
                    self._send(
                        {
                            "jsonrpc": "2.0",
                            "id": message["id"],
                            "error": {"code": -32601, "message": "Client method not supported"},
                        }
                    )
                continue
            if message.get("id") != request_id:
                continue
            if "error" in message:
                raise McpProtocolError(f"MCP {method} failed: {json.dumps(message['error'], ensure_ascii=False)}")
            result = message.get("result")
            if not isinstance(result, dict):
                raise McpProtocolError(f"MCP {method} response result must be an object.")
            return result

    def notify(self, method: str, params: dict[str, Any]) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": params})

    def list_tools(self, max_tools: int = 100) -> tuple[list[dict[str, Any]], int, bool]:
        tools: list[dict[str, Any]] = []
        cursor: str | None = None
        for _ in range(MCP_MAX_PAGES):
            params = {"cursor": cursor} if cursor else {}
            result = self.request("tools/list", params)
            page = result.get("tools")
            if not isinstance(page, list):
                raise McpProtocolError("MCP tools/list result did not include a tools list.")
            tools.extend(item for item in page if isinstance(item, dict))
            cursor = result.get("nextCursor") if isinstance(result.get("nextCursor"), str) else None
            if len(tools) > MCP_MAX_TOOLS or not cursor:
                break
        bounded = tools[: min(max_tools, MCP_MAX_TOOLS)]
        return bounded, len(tools), len(tools) > len(bounded) or bool(cursor)

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.request("tools/call", {"name": name, "arguments": arguments})

    def stderr_tail(self, max_chars: int = 4_000) -> str:
        self.stderr_file.flush()
        size = self.stderr_file.tell()
        self.stderr_file.seek(max(0, size - max_chars * 4))
        return self.stderr_file.read().decode("utf-8", errors="replace")[-max_chars:]

    def _send(self, message: dict[str, Any]) -> None:
        process = self._require_process()
        if process.stdin is None:
            raise McpProtocolError("MCP server stdin is unavailable.")
        payload = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
        process.stdin.write(payload)
        process.stdin.flush()

    def _read_message(self, deadline: float) -> dict[str, Any]:
        process = self._require_process()
        if process.stdout is None:
            raise McpProtocolError("MCP server stdout is unavailable.")
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        try:
            while True:
                newline = self.buffer.find(b"\n")
                if newline >= 0:
                    raw = bytes(self.buffer[:newline])
                    del self.buffer[: newline + 1]
                    if not raw:
                        continue
                    try:
                        message = json.loads(raw.decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError) as error:
                        raise McpProtocolError(f"MCP server emitted invalid JSON-RPC: {error}") from error
                    if not isinstance(message, dict):
                        raise McpProtocolError("MCP server message must be a JSON object.")
                    return message
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(f"MCP request timed out after {self.timeout_ms} ms.")
                if not selector.select(remaining):
                    raise TimeoutError(f"MCP request timed out after {self.timeout_ms} ms.")
                chunk = os.read(process.stdout.fileno(), 65_536)
                if not chunk:
                    stderr = self.stderr_tail()
                    detail = f" stderr: {stderr}" if stderr else ""
                    raise McpProtocolError(f"MCP server exited before responding.{detail}")
                self.buffer.extend(chunk)
                if len(self.buffer) > MCP_MAX_MESSAGE_BYTES:
                    raise McpProtocolError(f"MCP message exceeds {MCP_MAX_MESSAGE_BYTES} bytes.")
        finally:
            selector.close()

    def _require_process(self) -> subprocess.Popen[bytes]:
        if self.process is None:
            raise McpProtocolError("MCP server process has not started.")
        return self.process
