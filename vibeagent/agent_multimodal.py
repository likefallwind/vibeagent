from __future__ import annotations

import base64
import json
from typing import Any

from .types import ChatMessage, ContentBlock
from .workspace import read_project_image_payload
from .workspace_core import RunWorkspace


def build_tool_result_block(
    workspace: RunWorkspace,
    tool_call_id: str,
    observation: object,
    result_payload: dict[str, Any],
) -> ContentBlock:
    text = json.dumps(result_payload, ensure_ascii=False)
    if getattr(observation, "kind", None) != "view_image" or not getattr(observation, "ok", False):
        return {"type": "tool_result", "tool_call_id": tool_call_id, "content": text}
    try:
        payload = read_project_image_payload(
            workspace,
            str(getattr(observation, "path")),
            int(getattr(observation, "max_bytes")),
        )
        encoded = base64.b64encode(payload["data"]).decode("ascii")
        content: list[ContentBlock] = [
            {"type": "text", "text": text},
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": str(payload["mime_type"]),
                    "data": encoded,
                },
            },
        ]
    except (OSError, ValueError) as error:
        content = [{"type": "text", "text": f"{text}\nImage payload became unavailable: {error}"}]
    return {"type": "tool_result", "tool_call_id": tool_call_id, "content": content}


def strip_consumed_tool_images(messages: list[ChatMessage]) -> None:
    for index, message in enumerate(messages):
        if not isinstance(message.content, list):
            continue
        compacted: list[ContentBlock] = []
        changed = False
        for block in message.content:
            if block.get("type") != "tool_result" or not isinstance(block.get("content"), list):
                compacted.append(block)
                continue
            nested = block["content"]
            text_parts = [
                str(item.get("text"))
                for item in nested
                if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str)
            ]
            if any(isinstance(item, dict) and item.get("type") == "image" for item in nested):
                text_parts.append("[image payload consumed by model and removed from history]")
                compacted.append({**block, "content": "\n".join(text_parts)})
                changed = True
            else:
                compacted.append(block)
        if changed:
            messages[index] = ChatMessage(role=message.role, content=compacted)
