from __future__ import annotations

from collections.abc import Iterable
from typing import Any


MCP_STDIO_PROTOCOL_VERSION = "2025-11-25"
MCP_HTTP_PROTOCOL_VERSION = "2026-07-28"
MCP_MAX_MESSAGE_BYTES = 1_000_000
MCP_MAX_TOOLS = 500
MCP_MAX_RESOURCES = 500
MCP_MAX_RESOURCE_TEMPLATES = 500
MCP_MAX_PAGES = 20


class McpProtocolError(RuntimeError):
    def __init__(self, message: str, *, code: int | None = None) -> None:
        super().__init__(message)
        self.code = code


class McpToolsClient:
    def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def list_tools(self, max_tools: int = 100) -> tuple[list[dict[str, Any]], int, bool]:
        tools: list[dict[str, Any]] = []
        cursor: str | None = None
        for _ in range(MCP_MAX_PAGES):
            params = {"cursor": cursor} if cursor else {}
            result = self.request("tools/list", params)
            page = result.get("tools")
            if not isinstance(page, list):
                raise McpProtocolError("MCP tools/list result did not include a tools list.")
            tools.extend(self._prepare_tools(item for item in page if isinstance(item, dict)))
            cursor = result.get("nextCursor") if isinstance(result.get("nextCursor"), str) else None
            if len(tools) > MCP_MAX_TOOLS or not cursor:
                break
        bounded = tools[: min(max_tools, MCP_MAX_TOOLS)]
        return bounded, len(tools), len(tools) > len(bounded) or bool(cursor)

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.request("tools/call", {"name": name, "arguments": arguments})

    def list_resources(
        self,
        max_resources: int = 100,
    ) -> tuple[list[dict[str, Any]], int, bool]:
        resources: list[dict[str, Any]] = []
        cursor: str | None = None
        for _ in range(MCP_MAX_PAGES):
            params = {"cursor": cursor} if cursor else {}
            result = self.request("resources/list", params)
            page = result.get("resources")
            if not isinstance(page, list):
                raise McpProtocolError(
                    "MCP resources/list result did not include a resources list."
                )
            resources.extend(item for item in page if isinstance(item, dict))
            cursor = (
                result.get("nextCursor")
                if isinstance(result.get("nextCursor"), str)
                else None
            )
            if len(resources) > MCP_MAX_RESOURCES or not cursor:
                break
        bounded = resources[: min(max_resources, MCP_MAX_RESOURCES)]
        return bounded, len(resources), len(resources) > len(bounded) or bool(cursor)

    def list_resource_templates(
        self,
        max_templates: int = 100,
    ) -> tuple[list[dict[str, Any]], int, bool]:
        templates: list[dict[str, Any]] = []
        cursor: str | None = None
        for _ in range(MCP_MAX_PAGES):
            params = {"cursor": cursor} if cursor else {}
            try:
                result = self.request("resources/templates/list", params)
            except McpProtocolError as error:
                if not templates and cursor is None and error.code == -32601:
                    return [], 0, False
                raise
            page = result.get("resourceTemplates")
            if not isinstance(page, list):
                raise McpProtocolError(
                    "MCP resources/templates/list result did not include a resourceTemplates list."
                )
            templates.extend(item for item in page if isinstance(item, dict))
            cursor = (
                result.get("nextCursor")
                if isinstance(result.get("nextCursor"), str)
                else None
            )
            if len(templates) > MCP_MAX_RESOURCE_TEMPLATES or not cursor:
                break
        bounded = templates[: min(max_templates, MCP_MAX_RESOURCE_TEMPLATES)]
        return bounded, len(templates), len(templates) > len(bounded) or bool(cursor)

    def read_resource(self, uri: str) -> dict[str, Any]:
        return self.request("resources/read", {"uri": uri})

    def _prepare_tools(self, tools: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        return list(tools)
