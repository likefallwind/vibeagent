from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from typing import Any

from .model_streaming import ProviderStreamHandler
from .sse import iter_sse_json


def accumulate_anthropic_stream(
    lines: Iterable[bytes | str],
    *,
    on_event: ProviderStreamHandler,
    response_error: Callable[[str], Exception],
) -> dict[str, Any]:
    message: dict[str, Any] = {}
    blocks: dict[int, dict[str, Any]] = {}
    tool_inputs: dict[int, str] = {}
    usage: dict[str, Any] = {}
    stopped = False

    for event in iter_sse_json(lines):
        on_event(dict(event))
        event_type = event.get("type")
        if event_type == "error":
            error = event.get("error")
            detail = json.dumps(error, ensure_ascii=False, sort_keys=True) if isinstance(error, dict) else str(error)
            raise response_error(f"Streaming response returned an error: {detail[:2_000]}")
        if event_type == "message_start":
            started = event.get("message")
            if isinstance(started, dict):
                message.update(started)
                started_usage = started.get("usage")
                if isinstance(started_usage, dict):
                    usage.update(started_usage)
            continue
        if event_type == "content_block_start":
            index = _event_index(event)
            block = event.get("content_block")
            if index is not None and isinstance(block, dict):
                blocks[index] = dict(block)
                if block.get("type") == "tool_use":
                    tool_inputs[index] = ""
            continue
        if event_type == "content_block_delta":
            index = _event_index(event)
            delta = event.get("delta")
            if index is None or not isinstance(delta, dict):
                continue
            block = blocks.setdefault(index, {})
            delta_type = delta.get("type")
            if delta_type == "text_delta" and isinstance(delta.get("text"), str):
                block["type"] = block.get("type") or "text"
                block["text"] = str(block.get("text") or "") + delta["text"]
            elif delta_type == "thinking_delta" and isinstance(delta.get("thinking"), str):
                block["type"] = block.get("type") or "thinking"
                block["thinking"] = str(block.get("thinking") or "") + delta["thinking"]
            elif delta_type == "signature_delta" and isinstance(delta.get("signature"), str):
                block["signature"] = str(block.get("signature") or "") + delta["signature"]
            elif delta_type == "input_json_delta" and isinstance(delta.get("partial_json"), str):
                tool_inputs[index] = tool_inputs.get(index, "") + delta["partial_json"]
            continue
        if event_type == "content_block_stop":
            index = _event_index(event)
            if index is not None and index in tool_inputs:
                partial = tool_inputs[index]
                if partial:
                    try:
                        blocks.setdefault(index, {})["input"] = json.loads(partial)
                    except json.JSONDecodeError:
                        blocks.setdefault(index, {})["input"] = partial
            continue
        if event_type == "message_delta":
            delta = event.get("delta")
            if isinstance(delta, dict):
                message.update(delta)
            delta_usage = event.get("usage")
            if isinstance(delta_usage, dict):
                usage.update(delta_usage)
            continue
        if event_type == "message_stop":
            stopped = True

    if not stopped:
        raise response_error("Streaming response ended before message_stop.")
    message["content"] = [blocks[index] for index in sorted(blocks)]
    if usage:
        message["usage"] = usage
    return message


def _event_index(event: dict[str, Any]) -> int | None:
    value = event.get("index")
    return value if isinstance(value, int) and value >= 0 else None


__all__ = ["accumulate_anthropic_stream"]
