from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class MemoryFileInfo:
    path: str
    bytes: int


@dataclass(frozen=True)
class MemoryListObservation:
    kind: Literal["memory_list"]
    ok: bool
    files: list[MemoryFileInfo] = field(default_factory=list)
    message: str = ""


@dataclass(frozen=True)
class MemoryReadObservation:
    kind: Literal["memory_read"]
    ok: bool
    path: str
    content: str
    truncated: bool
    message: str


@dataclass(frozen=True)
class MemoryWriteObservation:
    kind: Literal["memory_write"]
    ok: bool
    path: str
    bytes: int
    redacted: bool
    message: str


@dataclass(frozen=True)
class CheckMemoryWriteObservation:
    kind: Literal["check_memory_write"]
    ok: bool
    path: str
    mode: str
    content_sha256: str
    current_bytes: int
    proposed_bytes: int
    redacted: bool
    diff: str
    message: str
