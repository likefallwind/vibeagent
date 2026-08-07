from __future__ import annotations

import json
from typing import Any

from .types import ChatMessage, ContentBlock, ToolSpec


def flatten_messages(messages: list[ChatMessage]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for message in messages:
        content = message.content
        if not isinstance(content, list):
            flattened.append({"role": message.role, "content": content})
            continue

        tool_results = [block for block in content if block.get("type") == "tool_result"]
        if tool_results:
            flattened.extend(flatten_tool_results(tool_results))
            continue

        tool_calls = [block for block in content if block.get("type") == "tool_call"]
        text = "".join(block["text"] for block in content if block.get("type") == "text" and isinstance(block.get("text"), str))
        if tool_calls:
            flattened.append(
                {
                    "role": "assistant",
                    "content": text or None,
                    "tool_calls": [tool_call_to_openai(block) for block in tool_calls],
                }
            )
        else:
            images = openai_image_blocks(content)
            if images:
                flattened.append(
                    {
                        "role": message.role,
                        "content": [{"type": "text", "text": text}, *images] if text else images,
                    }
                )
            else:
                flattened.append({"role": message.role, "content": text})
    return flattened


def flatten_tool_results(tool_results: list[ContentBlock]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    images: list[dict[str, Any]] = []
    for block in tool_results:
        result_content = block.get("content", "")
        if isinstance(result_content, list):
            text = "\n".join(
                str(item.get("text"))
                for item in result_content
                if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str)
            )
            images.extend(openai_image_blocks(result_content))
            result_content = text
        flattened.append(
            {
                "role": "tool",
                "tool_call_id": block.get("tool_call_id") or block.get("tool_use_id"),
                "content": result_content,
            }
        )
    if images:
        flattened.append(
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Image content returned by the preceding tool result."},
                    *images,
                ],
            }
        )
    return flattened


def openai_image_blocks(content: list[ContentBlock]) -> list[dict[str, Any]]:
    return [
        converted
        for block in content
        if block.get("type") == "image"
        if (converted := image_block_to_openai(block)) is not None
    ]


def image_block_to_openai(block: ContentBlock) -> dict[str, Any] | None:
    source = block.get("source")
    if not isinstance(source, dict) or source.get("type") != "base64":
        return None
    media_type = source.get("media_type")
    data = source.get("data")
    if not isinstance(media_type, str) or not isinstance(data, str):
        return None
    return {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{data}"}}


def tool_to_openai(tool: ToolSpec) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool.get("description", ""),
            "parameters": tool.get("input_schema", {"type": "object"}),
        },
    }


def tool_call_to_openai(block: ContentBlock) -> dict[str, Any]:
    return {
        "id": block.get("id"),
        "type": "function",
        "function": {
            "name": block.get("name"),
            "arguments": json.dumps(block.get("input", {}), ensure_ascii=False),
        },
    }
