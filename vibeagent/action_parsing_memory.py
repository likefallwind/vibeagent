from __future__ import annotations

from typing import Any

from .action_memory_types import CheckMemoryWriteAction, MemoryListAction, MemoryReadAction, MemoryWriteAction
from .action_parsing_helpers import ActionParseError


MEMORY_ACTION_TYPES = {"check_memory_write", "memory_list", "memory_read", "memory_write"}


def parse_memory_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in MEMORY_ACTION_TYPES:
        return None
    if action_type == "memory_list":
        return MemoryListAction(type="memory_list")
    path = value.get("path", "MEMORY.md")
    if not isinstance(path, str) or not path or len(path) > 131:
        raise ActionParseError("Memory path must be a non-empty string of at most 131 characters.", raw)
    if action_type == "memory_read":
        return MemoryReadAction(type="memory_read", path=path)
    content = value.get("content")
    if not isinstance(content, str):
        raise ActionParseError("memory_write content must be a string.", raw)
    mode = value.get("mode", "replace")
    if mode not in {"replace", "append"}:
        raise ActionParseError("memory_write mode must be replace or append.", raw)
    if action_type == "check_memory_write":
        return CheckMemoryWriteAction(type="check_memory_write", path=path, content=content, mode=mode)
    return MemoryWriteAction(type="memory_write", path=path, content=content, mode=mode)
