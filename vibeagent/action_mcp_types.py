from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class McpServersAction:
    type: Literal["mcp_servers"]
    max_servers: int = 50


@dataclass(frozen=True)
class McpToolsAction:
    type: Literal["mcp_tools"]
    server: str
    max_tools: int = 100
    timeout_ms: int = 10_000


@dataclass(frozen=True)
class McpCallAction:
    type: Literal["mcp_call"]
    server: str
    name: str
    arguments: dict[str, Any]
    timeout_ms: int = 30_000
    max_output_chars: int = 20_000
