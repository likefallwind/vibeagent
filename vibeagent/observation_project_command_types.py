from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ProjectCommand:
    file: str
    cwd: str
    source: str
    command: str
    detail: str
    available: bool
    missing_tool: str | None = None


@dataclass(frozen=True)
class ProjectCommandsObservation:
    kind: Literal["project_commands"]
    ok: bool
    commands: list[ProjectCommand]
    total: int
    truncated: bool
    total_files: int
    scanned_files: int
    message: str


@dataclass(frozen=True)
class ToolSearchObservation:
    kind: Literal["tool_search"]
    ok: bool
    query: str
    matches: list[dict[str, object]]
    total: int
    shown: int
    truncated: bool
    category: str | None
    approval_required: bool | None
    suggestions: list[str]
    message: str
