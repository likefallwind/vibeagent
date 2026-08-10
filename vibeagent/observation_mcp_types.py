from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class McpServerInfo:
    name: str
    command: str
    arg_count: int
    cwd: str
    env_keys: list[str]
    transport: str = "stdio"
    endpoint: str = ""
    header_keys: list[str] = field(default_factory=list)
    protocol_version: str = "2025-11-25"


@dataclass(frozen=True)
class McpServersObservation:
    kind: Literal["mcp_servers"]
    ok: bool
    servers: list[McpServerInfo]
    total: int
    truncated: bool
    config_path: str
    message: str


@dataclass(frozen=True)
class McpToolInfo:
    name: str
    title: str
    description: str
    input_schema: dict[str, object]


@dataclass(frozen=True)
class McpToolsObservation:
    kind: Literal["mcp_tools"]
    ok: bool
    server: str
    tools: list[McpToolInfo]
    total: int
    truncated: bool
    timeout_ms: int
    error: str | None
    message: str


@dataclass(frozen=True)
class McpResourceInfo:
    uri: str
    name: str
    title: str
    description: str
    mime_type: str
    size: int | None = None


@dataclass(frozen=True)
class McpResourceTemplateInfo:
    uri_template: str
    name: str
    title: str
    description: str
    mime_type: str


@dataclass(frozen=True)
class McpResourcesObservation:
    kind: Literal["mcp_resources"]
    ok: bool
    server: str
    resources: list[McpResourceInfo]
    templates: list[McpResourceTemplateInfo]
    total: int
    resource_total: int
    template_total: int
    truncated: bool
    timeout_ms: int
    error: str | None
    message: str


@dataclass(frozen=True)
class McpReadResourceObservation:
    kind: Literal["mcp_read_resource"]
    ok: bool
    server: str
    uri: str
    template_uri: str | None
    output: str
    mime_types: list[str]
    truncated: bool
    max_output_chars: int
    timeout_ms: int
    error: str | None
    message: str


@dataclass(frozen=True)
class McpCallObservation:
    kind: Literal["mcp_call"]
    ok: bool
    server: str
    name: str
    output: str
    is_error: bool
    truncated: bool
    max_output_chars: int
    timeout_ms: int
    error: str | None
    message: str
    arguments: dict[str, object] = field(default_factory=dict)
    text_output: str = ""
