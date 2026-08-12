from __future__ import annotations

import base64
import json
from typing import Any

from .types import ChatMessage, ContentBlock
from .redaction import redact_jsonable_payload
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


def build_updated_tool_result_block(
    tool_call_id: str,
    updated_tool_output: object,
    *,
    additional_contexts: tuple[str, ...] = (),
    additional_results: object | None = None,
) -> ContentBlock:
    redacted = redact_jsonable_payload(updated_tool_output)
    content = (
        redacted
        if isinstance(redacted, str)
        else json.dumps(redacted, ensure_ascii=False, allow_nan=False)
    )
    if not additional_contexts and additional_results is None:
        return {"type": "tool_result", "tool_call_id": tool_call_id, "content": content}
    blocks: list[ContentBlock] = [{"type": "text", "text": content}]
    if additional_contexts:
        redacted_contexts = tuple(
            str(redact_jsonable_payload(value)) for value in additional_contexts
        )
        blocks.append(
            {
                "type": "text",
                "text": "PostToolUse hook context:\n" + "\n\n".join(redacted_contexts),
            }
        )
    if additional_results is not None:
        blocks.append(
            {
                "type": "text",
                "text": "Additional tool results:\n"
                + json.dumps(
                    redact_jsonable_payload(additional_results),
                    ensure_ascii=False,
                ),
            }
        )
    return {"type": "tool_result", "tool_call_id": tool_call_id, "content": blocks}


def strip_consumed_tool_images(messages: list[ChatMessage]) -> None:
    for index, message in enumerate(messages):
        if not isinstance(message.content, list):
            continue
        compacted: list[ContentBlock] = []
        changed = False
        for block in message.content:
            if block.get("type") == "image":
                compacted.append(
                    {
                        "type": "text",
                        "text": "[prompt image payload consumed by model and removed from history]",
                    }
                )
                changed = True
                continue
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


def pending_image_tool_exchange(messages: list[ChatMessage]) -> tuple[ChatMessage, ...]:
    if len(messages) < 2:
        return ()
    assistant_message = messages[-2]
    result_message = messages[-1]
    if assistant_message.role != "assistant" or result_message.role != "user":
        return ()
    if not isinstance(assistant_message.content, list) or not isinstance(result_message.content, list):
        return ()

    image_result_ids = {
        str(block.get("tool_call_id") or block.get("tool_use_id") or "")
        for block in result_message.content
        if _tool_result_contains_image(block)
    }
    tool_call_ids = {
        str(block.get("id") or "")
        for block in assistant_message.content
        if block.get("type") == "tool_call"
    }
    if image_result_ids and image_result_ids.issubset(tool_call_ids):
        return assistant_message, result_message
    return ()


def pending_image_tool_result_count(messages: list[ChatMessage]) -> int:
    exchange = pending_image_tool_exchange(messages)
    if not exchange:
        return 0
    result_message = exchange[-1]
    if not isinstance(result_message.content, list):
        return 0
    return sum(1 for block in result_message.content if _tool_result_contains_image(block))


def _tool_result_contains_image(block: ContentBlock) -> bool:
    if block.get("type") != "tool_result" or not isinstance(block.get("content"), list):
        return False
    return any(isinstance(item, dict) and item.get("type") == "image" for item in block["content"])
