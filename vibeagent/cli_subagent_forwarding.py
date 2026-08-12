from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from threading import Lock
from typing import Any

from .cli_stream_output import JsonEventStream


class SubagentStreamForwarder:
    def __init__(
        self,
        stream: JsonEventStream,
        *,
        enabled: bool = False,
        fallback: Callable[[Path, dict[str, Any]], None] | None = None,
    ) -> None:
        self.stream = stream
        self.enabled = enabled
        self.fallback = fallback or stream.session_event
        self._parent_tool_ids: dict[str, str] = {}
        self._lock = Lock()

    def __call__(self, session_dir: Path, event: dict[str, Any]) -> None:
        with self._lock:
            self.fallback(session_dir, event)
            if not self.enabled:
                return
            event_type = event.get("type")
            subagent_id = _nonempty_text(event.get("subagent_id"))
            if subagent_id is None:
                return
            explicit_parent = _nonempty_text(event.get("parent_tool_use_id"))
            if explicit_parent is not None:
                self._parent_tool_ids[subagent_id] = explicit_parent
            parent_tool_use_id = self._parent_tool_ids.get(subagent_id, subagent_id)
            if event_type == "subagent_model":
                blocks = _assistant_blocks(event.get("content"))
                if blocks:
                    self.stream.subagent_message(
                        session_dir,
                        role="assistant",
                        content=blocks,
                        subagent_id=subagent_id,
                        parent_tool_use_id=parent_tool_use_id,
                    )
            elif event_type == "subagent_tool_result":
                tool_use_id = _nonempty_text(event.get("id"))
                if tool_use_id is None:
                    return
                block: dict[str, object] = {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": json.dumps(event.get("result"), ensure_ascii=False, sort_keys=True),
                }
                if event.get("failed") is True:
                    block["is_error"] = True
                self.stream.subagent_message(
                    session_dir,
                    role="user",
                    content=[block],
                    subagent_id=subagent_id,
                    parent_tool_use_id=parent_tool_use_id,
                )


def _assistant_blocks(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    forwarded: list[dict[str, object]] = []
    for block in value:
        if not isinstance(block, dict):
            continue
        block_type = block.get("type")
        field = "text" if block_type == "text" else "thinking" if block_type == "thinking" else None
        content = _nonempty_text(block.get(field)) if field is not None else None
        if content is not None:
            forwarded.append({"type": block_type, field: content})
    return forwarded


def _nonempty_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


__all__ = ["SubagentStreamForwarder"]
