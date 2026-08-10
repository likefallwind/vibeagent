from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class MemoryListAction:
    type: Literal["memory_list"]


@dataclass(frozen=True)
class MemoryReadAction:
    type: Literal["memory_read"]
    path: str = "MEMORY.md"


@dataclass(frozen=True)
class MemoryWriteAction:
    type: Literal["memory_write"]
    path: str
    content: str
    mode: Literal["replace", "append"] = "replace"


@dataclass(frozen=True)
class CheckMemoryWriteAction:
    type: Literal["check_memory_write"]
    path: str
    content: str
    mode: Literal["replace", "append"] = "replace"
