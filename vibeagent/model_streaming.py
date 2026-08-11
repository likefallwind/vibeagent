from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from .types import AssistantResponse, ChatClient, ChatMessage, ToolSpec


ProviderStreamHandler = Callable[[dict[str, Any]], None]
AgentModelStreamHandler = Callable[[Path, int, int, dict[str, Any]], None]
ChatModelStreamHandler = Callable[[int, dict[str, Any]], None]


class ModelStreamingUnsupportedError(RuntimeError):
    pass


def complete_streaming(
    client: ChatClient,
    messages: list[ChatMessage],
    *,
    tools: list[ToolSpec] | None,
    max_tokens: int,
    temperature: float,
    timeout_ms: int,
    on_event: ProviderStreamHandler,
) -> AssistantResponse:
    complete_stream = getattr(client, "complete_stream", None)
    if not callable(complete_stream):
        raise ModelStreamingUnsupportedError(
            "The active model client does not support incremental streaming."
        )
    response = complete_stream(
        messages,
        tools=tools,
        max_tokens=max_tokens,
        temperature=temperature,
        timeout_ms=timeout_ms,
        on_event=on_event,
    )
    if not isinstance(response, AssistantResponse):
        raise ModelStreamingUnsupportedError("The streaming model client returned an invalid response.")
    return response


__all__ = [
    "AgentModelStreamHandler",
    "ChatModelStreamHandler",
    "ModelStreamingUnsupportedError",
    "ProviderStreamHandler",
    "complete_streaming",
]
