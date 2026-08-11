from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from .model_streaming import ProviderStreamHandler
from .sse import iter_sse_json


def accumulate_openai_chat_stream(
    lines: Iterable[bytes | str],
    *,
    on_event: ProviderStreamHandler,
    response_error: Callable[[str], Exception],
) -> dict[str, Any]:
    text = ""
    text_index: int | None = None
    tool_blocks: dict[int, dict[str, Any]] = {}
    tool_event_indexes: dict[int, int] = {}
    next_event_index = 0
    usage: dict[str, Any] | None = None
    message_started = False
    finish_reason: str | None = None

    def emit(event: dict[str, Any]) -> None:
        on_event(event)

    for chunk in iter_sse_json(lines):
        error = chunk.get("error")
        if isinstance(error, dict):
            emit({"type": "error", "error": error})
            raise response_error(f"Streaming response returned an error: {str(error)[:2_000]}")
        if not message_started:
            emit(
                {
                    "type": "message_start",
                    "message": {
                        "id": chunk.get("id"),
                        "type": "message",
                        "role": "assistant",
                        "content": [],
                        "model": chunk.get("model"),
                        "stop_reason": None,
                        "usage": {},
                    },
                }
            )
            message_started = True
        chunk_usage = chunk.get("usage")
        if isinstance(chunk_usage, dict):
            usage = dict(chunk_usage)
        choices = chunk.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            continue
        choice = choices[0]
        if isinstance(choice.get("finish_reason"), str):
            finish_reason = choice["finish_reason"]
        delta = choice.get("delta")
        if not isinstance(delta, dict):
            continue
        content = delta.get("content")
        if isinstance(content, str) and content:
            if text_index is None:
                text_index = next_event_index
                next_event_index += 1
                emit(
                    {
                        "type": "content_block_start",
                        "index": text_index,
                        "content_block": {"type": "text", "text": ""},
                    }
                )
            text += content
            emit(
                {
                    "type": "content_block_delta",
                    "index": text_index,
                    "delta": {"type": "text_delta", "text": content},
                }
            )
        calls = delta.get("tool_calls")
        if not isinstance(calls, list):
            continue
        for position, call in enumerate(calls):
            if not isinstance(call, dict):
                continue
            call_index = call.get("index") if isinstance(call.get("index"), int) else position
            function = call.get("function") if isinstance(call.get("function"), dict) else {}
            block = tool_blocks.get(call_index)
            if block is None:
                event_index = next_event_index
                next_event_index += 1
                tool_event_indexes[call_index] = event_index
                block = {
                    "id": call.get("id") or "",
                    "type": "function",
                    "function": {"name": function.get("name") or "", "arguments": ""},
                }
                tool_blocks[call_index] = block
                emit(
                    {
                        "type": "content_block_start",
                        "index": event_index,
                        "content_block": {
                            "type": "tool_use",
                            "id": block["id"],
                            "name": block["function"]["name"],
                            "input": {},
                        },
                    }
                )
            if isinstance(call.get("id"), str) and call["id"]:
                block["id"] = call["id"]
            if isinstance(function.get("name"), str) and function["name"]:
                block["function"]["name"] += function["name"]
            arguments = function.get("arguments")
            if isinstance(arguments, str) and arguments:
                block["function"]["arguments"] += arguments
                emit(
                    {
                        "type": "content_block_delta",
                        "index": tool_event_indexes[call_index],
                        "delta": {"type": "input_json_delta", "partial_json": arguments},
                    }
                )

    if not message_started:
        raise response_error("Streaming response did not include any events.")
    if finish_reason is None:
        raise response_error("Streaming response ended before a finish reason.")
    if text_index is not None:
        emit({"type": "content_block_stop", "index": text_index})
    for call_index in sorted(tool_event_indexes):
        emit({"type": "content_block_stop", "index": tool_event_indexes[call_index]})
    emit(
        {
            "type": "message_delta",
            "delta": {"stop_reason": finish_reason},
            "usage": _anthropic_usage(usage),
        }
    )
    emit({"type": "message_stop"})

    message: dict[str, Any] = {"role": "assistant", "content": text or None}
    if tool_blocks:
        message["tool_calls"] = [tool_blocks[index] for index in sorted(tool_blocks)]
    return {
        "choices": [{"message": message, "finish_reason": finish_reason}],
        **({"usage": usage} if usage is not None else {}),
    }


def _anthropic_usage(usage: dict[str, Any] | None) -> dict[str, Any]:
    if usage is None:
        return {}
    return {
        "input_tokens": usage.get("prompt_tokens", usage.get("input_tokens")),
        "output_tokens": usage.get("completion_tokens", usage.get("output_tokens")),
    }


__all__ = ["accumulate_openai_chat_stream"]
