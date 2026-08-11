from __future__ import annotations

import base64
import json
from collections.abc import Iterable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from . import __version__
from .mcp_config import McpServerConfig, expanded_mcp_headers
from .mcp_protocol import (
    MCP_HTTP_PROTOCOL_VERSION,
    MCP_MAX_MESSAGE_BYTES,
    MCP_STDIO_PROTOCOL_VERSION,
    McpProtocolError,
    McpToolsClient,
)
from .mcp_elicitation_context import current_mcp_elicitation_handler


MCP_MODERN_PROTOCOL_VERSION = MCP_HTTP_PROTOCOL_VERSION
MCP_LEGACY_PROTOCOL_VERSION = MCP_STDIO_PROTOCOL_VERSION
JS_SAFE_INTEGER = 9_007_199_254_740_991


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


class McpHttpClient(McpToolsClient):
    def __init__(self, config: McpServerConfig, timeout_ms: int) -> None:
        self.config = config
        self.timeout_ms = timeout_ms
        self.next_id = 1
        self.session_id: str | None = None
        self.tool_headers: dict[str, list[tuple[tuple[str, ...], str, str]]] = {}
        self.opener = build_opener(_NoRedirectHandler())
        self.elicitation_handler = current_mcp_elicitation_handler()

    def __enter__(self) -> "McpHttpClient":
        try:
            if self.config.protocol_version == MCP_LEGACY_PROTOCOL_VERSION:
                result, headers = self._request_with_headers(
                    "initialize",
                    {
                        "protocolVersion": MCP_LEGACY_PROTOCOL_VERSION,
                        "capabilities": self._client_capabilities(),
                        "clientInfo": {"name": "vibeagent", "version": __version__},
                    },
                    legacy_initialize=True,
                )
                version = result.get("protocolVersion")
                if version != MCP_LEGACY_PROTOCOL_VERSION:
                    raise McpProtocolError(f"MCP server selected unsupported protocolVersion: {version!r}.")
                self.session_id = headers.get("Mcp-Session-Id")
                self._notify("notifications/initialized", {})
            return self
        except Exception:
            self.close()
            raise

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    def close(self) -> None:
        if not self.session_id:
            return
        request = Request(self.config.url, method="DELETE", headers=self._base_headers(include_session=True))
        try:
            self.opener.open(request, timeout=self.timeout_ms / 1000).close()
        except (HTTPError, URLError, TimeoutError):
            pass
        finally:
            self.session_id = None

    def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        result, _ = self._request_with_headers(method, params)
        return result

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        extra_headers: dict[str, str] = {}
        if self.config.protocol_version == MCP_MODERN_PROTOCOL_VERSION:
            for path, header_name, value_type in self.tool_headers.get(name, []):
                found, value = _value_at_path(arguments, path)
                if found and value is not None:
                    extra_headers[f"Mcp-Param-{header_name}"] = _encode_header_value(
                        _primitive_text(value, value_type)
                    )
        result, _ = self._request_with_headers(
            "tools/call", {"name": name, "arguments": arguments}, extra_headers=extra_headers
        )
        return result

    def _prepare_tools(self, tools: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        accepted: list[dict[str, Any]] = []
        for tool in tools:
            name = tool.get("name")
            if not isinstance(name, str) or not name:
                accepted.append(tool)
                continue
            if self.config.protocol_version != MCP_MODERN_PROTOCOL_VERSION:
                accepted.append(tool)
                continue
            try:
                annotations = _tool_header_annotations(tool.get("inputSchema"))
            except McpProtocolError:
                continue
            self.tool_headers[name] = annotations
            accepted.append(tool)
        return accepted

    def _request_with_headers(
        self,
        method: str,
        params: dict[str, Any],
        *,
        legacy_initialize: bool = False,
        extra_headers: dict[str, str] | None = None,
    ) -> tuple[dict[str, Any], Any]:
        request_id = self.next_id
        self.next_id += 1
        body_params = dict(params)
        modern = self.config.protocol_version == MCP_MODERN_PROTOCOL_VERSION
        if modern:
            metadata = body_params.get("_meta")
            metadata = dict(metadata) if isinstance(metadata, dict) else {}
            metadata.update(
                {
                    "io.modelcontextprotocol/protocolVersion": self.config.protocol_version,
                    "io.modelcontextprotocol/clientInfo": {"name": "vibeagent", "version": __version__},
                    "io.modelcontextprotocol/clientCapabilities": self._client_capabilities(),
                }
            )
            body_params["_meta"] = metadata
        message = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": body_params}
        headers = self._base_headers(include_protocol=not legacy_initialize, include_session=not legacy_initialize)
        if modern:
            headers["Mcp-Method"] = method
            source_name = body_params.get("name", body_params.get("uri"))
            if method in {"tools/call", "resources/read", "prompts/get"} and isinstance(source_name, str):
                headers["Mcp-Name"] = _encode_header_value(source_name)
        headers.update(extra_headers or {})
        payload, response_headers = self._post(message, headers)
        response = _response_for_request(payload, request_id)
        if "error" in response:
            rpc_error = response["error"]
            code = rpc_error.get("code") if isinstance(rpc_error, dict) else None
            raise McpProtocolError(
                f"MCP {method} failed: {json.dumps(rpc_error, ensure_ascii=False)}",
                code=(code if isinstance(code, int) and not isinstance(code, bool) else None),
            )
        result = response.get("result")
        if not isinstance(result, dict):
            raise McpProtocolError(f"MCP {method} response result must be an object.")
        return result, response_headers

    def _notify(self, method: str, params: dict[str, Any]) -> None:
        message = {"jsonrpc": "2.0", "method": method, "params": params}
        headers = self._base_headers(include_protocol=True, include_session=True)
        self._post(message, headers, notification=True)

    def _post(
        self, message: dict[str, Any], headers: dict[str, str], *, notification: bool = False
    ) -> tuple[list[dict[str, Any]], Any]:
        raw = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        request = Request(self.config.url, data=raw, method="POST", headers=headers)
        try:
            with self.opener.open(request, timeout=self.timeout_ms / 1000) as response:
                response_headers = response.headers
                status = response.status
                content_type = response_headers.get_content_type()
                if notification:
                    payload = response.read(MCP_MAX_MESSAGE_BYTES + 1)
                    messages: list[dict[str, Any]] = []
                elif content_type == "application/json":
                    payload = response.read(MCP_MAX_MESSAGE_BYTES + 1)
                    messages = [_parse_json_message(payload)]
                elif content_type == "text/event-stream":
                    payload = b""
                    messages = _read_sse_messages(
                        response,
                        message.get("id"),
                        self._handle_server_request,
                    )
                else:
                    raise McpProtocolError(f"MCP HTTP response has unsupported Content-Type: {content_type}.")
        except HTTPError as error:
            payload = error.read(MCP_MAX_MESSAGE_BYTES + 1)
            if len(payload) > MCP_MAX_MESSAGE_BYTES:
                raise McpProtocolError(f"MCP message exceeds {MCP_MAX_MESSAGE_BYTES} bytes.") from error
            detail = _http_error_detail(payload)
            raise McpProtocolError(f"MCP HTTP request failed with status {error.code}{detail}.") from error
        except URLError as error:
            raise McpProtocolError(f"MCP HTTP request failed: {error.reason}") from error
        if len(payload) > MCP_MAX_MESSAGE_BYTES:
            raise McpProtocolError(f"MCP message exceeds {MCP_MAX_MESSAGE_BYTES} bytes.")
        if notification:
            if status != 202:
                raise McpProtocolError(f"MCP notification expected HTTP 202, got {status}.")
            return [], response_headers
        return messages, response_headers

    def _client_capabilities(self) -> dict[str, object]:
        if self.elicitation_handler is None:
            return {}
        return {"elicitation": {"form": {}, "url": {}}}

    def _handle_server_request(self, message: dict[str, Any]) -> None:
        if "id" not in message:
            return
        if message.get("method") == "elicitation/create" and self.elicitation_handler is not None:
            params = message.get("params")
            if isinstance(params, dict):
                try:
                    result = self.elicitation_handler(self.config.name, params)
                except Exception:
                    response = _rpc_error(message["id"], -32603, "Elicitation handler failed")
                else:
                    response = {"jsonrpc": "2.0", "id": message["id"], "result": result}
            else:
                response = _rpc_error(message["id"], -32602, "Invalid elicitation params")
        else:
            response = _rpc_error(message["id"], -32601, "Client method not supported")
        headers = self._base_headers(include_protocol=True, include_session=True)
        self._post(response, headers, notification=True)

    def _base_headers(self, *, include_protocol: bool = True, include_session: bool = True) -> dict[str, str]:
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        for key, value in expanded_mcp_headers(self.config).items():
            if len(value) > 8_192 or "\r" in value or "\n" in value:
                raise McpProtocolError(f"Expanded MCP HTTP header {key!r} has an invalid value.")
            headers[key] = value
        if include_protocol:
            headers["MCP-Protocol-Version"] = self.config.protocol_version
        if include_session and self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        return headers


def _response_for_request(messages: list[dict[str, Any]], request_id: int) -> dict[str, Any]:
    for message in messages:
        if message.get("id") == request_id and "method" not in message:
            return message
    raise McpProtocolError("MCP HTTP response did not include the matching JSON-RPC response.")


def _parse_json_message(payload: bytes) -> dict[str, Any]:
    try:
        message = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise McpProtocolError(f"MCP server emitted invalid JSON-RPC: {error}") from error
    if not isinstance(message, dict):
        raise McpProtocolError("MCP server message must be a JSON object.")
    return message


def _read_sse_messages(
    stream: Any,
    request_id: object,
    server_request_handler: Any = None,
) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    data_lines: list[str] = []
    total = 0
    while True:
        raw_line = stream.readline(MCP_MAX_MESSAGE_BYTES - total + 1)
        if not raw_line:
            line = ""
            at_eof = True
        else:
            total += len(raw_line)
            if total > MCP_MAX_MESSAGE_BYTES:
                raise McpProtocolError(f"MCP message exceeds {MCP_MAX_MESSAGE_BYTES} bytes.")
            try:
                line = raw_line.decode("utf-8").rstrip("\r\n")
            except UnicodeDecodeError as error:
                raise McpProtocolError(f"MCP server emitted invalid SSE: {error}") from error
            at_eof = False
        if not line:
            if data_lines:
                message = _parse_json_message("\n".join(data_lines).encode("utf-8"))
                messages.append(message)
                data_lines = []
                if "method" in message and server_request_handler is not None:
                    server_request_handler(message)
                if message.get("id") == request_id and "method" not in message:
                    return messages
            if at_eof:
                break
        elif line.startswith("data:"):
            data_lines.append(line[5:].lstrip(" "))
    if not messages:
        raise McpProtocolError("MCP SSE response did not contain JSON-RPC data.")
    return messages


def _rpc_error(request_id: object, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def _http_error_detail(payload: bytes) -> str:
    if not payload:
        return ""
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return ""
    return f": {json.dumps(value, ensure_ascii=False)[:2_000]}"


def _tool_header_annotations(schema: object) -> list[tuple[tuple[str, ...], str, str]]:
    if not isinstance(schema, dict):
        return []
    found: list[tuple[tuple[str, ...], str, str]] = []
    names: set[str] = set()

    def walk(node: object, path: tuple[str, ...], reachable: bool, is_property: bool) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item, path, False, False)
            return
        if not isinstance(node, dict):
            return
        if "x-mcp-header" in node:
            header_name = node["x-mcp-header"]
            value_type = node.get("type")
            if (
                not reachable
                or not is_property
                or not isinstance(header_name, str)
                or not header_name
                or not _is_http_token(header_name)
                or value_type not in {"string", "integer", "boolean"}
                or header_name.lower() in names
            ):
                raise McpProtocolError("Invalid x-mcp-header annotation in MCP tool definition.")
            names.add(header_name.lower())
            found.append((path, header_name, str(value_type)))
        for key, value in node.items():
            if key == "properties" and isinstance(value, dict):
                for property_name, property_schema in value.items():
                    if isinstance(property_name, str):
                        walk(property_schema, (*path, property_name), reachable, True)
            elif key != "x-mcp-header":
                walk(value, path, False, False)

    walk(schema, (), True, False)
    return found


def _is_http_token(value: str) -> bool:
    allowed = "!#$%&'*+-.^_`|~"
    return all(character.isascii() and (character.isalnum() or character in allowed) for character in value)


def _value_at_path(arguments: dict[str, Any], path: tuple[str, ...]) -> tuple[bool, Any]:
    value: Any = arguments
    for part in path:
        if not isinstance(value, dict) or part not in value:
            return False, None
        value = value[part]
    return True, value


def _primitive_text(value: Any, value_type: str) -> str:
    if value_type == "string" and isinstance(value, str):
        return value
    if value_type == "boolean" and isinstance(value, bool):
        return "true" if value else "false"
    if value_type == "integer" and isinstance(value, int) and not isinstance(value, bool) and abs(value) <= JS_SAFE_INTEGER:
        return str(value)
    raise McpProtocolError("MCP x-mcp-header argument does not match its declared primitive type.")


def _encode_header_value(value: str) -> str:
    plain = all(character == "\t" or 0x20 <= ord(character) <= 0x7E for character in value)
    sentinel = value.startswith("=?base64?") and value.endswith("?=")
    if plain and value == value.strip() and not sentinel:
        return value
    encoded = base64.b64encode(value.encode("utf-8")).decode("ascii")
    return f"=?base64?{encoded}?="
