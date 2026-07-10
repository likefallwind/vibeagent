from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class CheckStartCommandObservation:
    kind: Literal["check_start_command"]
    ok: bool
    command: str
    cwd: str
    cwd_ok: bool
    blocked: bool
    block_reason: str | None
    executable_available: bool
    missing_tool: str | None
    message: str


@dataclass(frozen=True)
class PortCheckObservation:
    kind: Literal["port_check"]
    ok: bool
    host: str
    port: int
    timeout_ms: int
    reachable: bool
    error: str | None
    message: str


@dataclass(frozen=True)
class HttpCheckObservation:
    kind: Literal["http_check"]
    ok: bool
    url: str
    final_url: str | None
    status: int | None
    reason: str | None
    timeout_ms: int
    reachable: bool
    matched: bool
    matched_pattern: str | None
    body: str
    body_truncated: bool
    max_body_chars: int
    error: str | None
    message: str


@dataclass(frozen=True)
class HttpFetchObservation:
    kind: Literal["http_fetch"]
    ok: bool
    url: str
    final_url: str | None
    status: int | None
    reason: str | None
    content_type: str | None
    timeout_ms: int
    reachable: bool
    body: str
    body_truncated: bool
    max_body_chars: int
    error: str | None
    message: str


@dataclass(frozen=True)
class WebFetchObservation:
    kind: Literal["web_fetch"]
    ok: bool
    url: str
    final_url: str | None
    status: int | None
    content_type: str | None
    title: str | None
    text: str
    text_truncated: bool
    max_text_chars: int
    error: str | None
    message: str


@dataclass(frozen=True)
class RuntimeToolInfo:
    name: str
    available: bool
    path: str | None
    version: str | None
    message: str


@dataclass(frozen=True)
class EnvironmentInfoObservation:
    kind: Literal["environment_info"]
    ok: bool
    project_root: str
    python_version: str
    python_executable: str
    platform: str
    is_git_repo: bool
    tools: list[RuntimeToolInfo]
    message: str
