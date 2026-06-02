from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .types import AssistantResponse, ChatMessage, ChatClient, ContentBlock


class MissingMiniMaxApiKeyError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("Missing MiniMax API key. Set MINIMAX_API_KEY, MINIMAX_API, or minimax_api.")


class MiniMaxHttpError(RuntimeError):
    def __init__(self, status: int, response_text: str) -> None:
        self.status = status
        self.response_text = response_text
        super().__init__(f"MiniMax API returned HTTP {status}: {summarize(response_text)}")


class MiniMaxResponseError(RuntimeError):
    pass


@dataclass(frozen=True)
class MiniMaxApiKeyInfo:
    name: str
    value: str


class MiniMaxClient(ChatClient):
    def __init__(self, api_key: str | None = None, base_url: str | None = None, model: str | None = None) -> None:
        # Normalize the explicit key first, then fallback to environment variables.
        normalized_key = normalize_minimax_api_key(api_key) or get_minimax_api_key_from_env()
        if not normalized_key:
            raise MissingMiniMaxApiKeyError()

        defaults = get_minimax_defaults()
        # Keep only the URL host/path portion once, so callers can pass or omit trailing slash.
        self.api_key = normalized_key
        self.base_url = (base_url or defaults["base_url"]).rstrip("/")
        self.model = model or defaults["model"]

    def complete(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> AssistantResponse:
        # Use Anthropic-compatible request shape: system prompt + chat messages.
        body = json.dumps(
            build_request_body(
                self.model,
                messages,
                tools=tools,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        ).encode("utf-8")
        request = Request(
            f"{self.base_url}/v1/messages",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            # OpenAI-style responses can be rejected by model/http errors; convert both cases
            # into typed exceptions with raw payload preserved.
            with urlopen(request) as response:
                text = response.read().decode("utf-8")
        except HTTPError as error:
            text = error.read().decode("utf-8", errors="replace")
            raise MiniMaxHttpError(error.code, text) from error

        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            raise MiniMaxResponseError(f"MiniMax response was not JSON: {error}") from error

        content = extract_content(data)
        if not content:
            raise MiniMaxResponseError(f"MiniMax response did not include structured content: {summarize(text)}")

        return AssistantResponse(content=content, raw=data)


def get_minimax_api_key_from_env(env: Mapping[str, str | None] | None = None) -> str | None:
    info = get_minimax_api_key_info_from_env(env)
    return info.value if info else None


def get_minimax_api_key_info_from_env(env: Mapping[str, str | None] | None = None) -> MiniMaxApiKeyInfo | None:
    source = env if env is not None else os.environ
    for name in ("MINIMAX_API_KEY", "MINIMAX_API", "minimax_api"):
        value = normalize_minimax_api_key(source.get(name))
        if value:
            return MiniMaxApiKeyInfo(name=name, value=value)
    return None


def get_minimax_defaults(env: Mapping[str, str | None] | None = None) -> dict[str, str]:
    # Keep default endpoint aligned with MiniMax Anthropic-compatible API and a stable default model.
    source = env if env is not None else os.environ
    return {
        "base_url": (source.get("MINIMAX_BASE_URL") or "https://api.minimaxi.com/anthropic").rstrip("/"),
        "model": source.get("MINIMAX_MODEL") or "MiniMax-M2.7",
    }


def build_request_body(
    model: str,
    messages: list[ChatMessage],
    tools: list[dict[str, Any]] | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.2,
) -> dict[str, Any]:
    # Anthropic format: system prompt lives at top-level `system`; only non-system messages stay in `messages`.
    body: dict[str, Any] = {
        "model": model,
        "messages": [message_to_minimax(message) for message in messages if message.role != "system"],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    system_parts = [message.content for message in messages if message.role == "system"]
    if system_parts:
        body["system"] = "\n\n".join(part if isinstance(part, str) else json.dumps(part) for part in system_parts)
    if tools:
        body["tools"] = tools
        body["tool_choice"] = {"type": "auto"}
    return body


def message_to_minimax(message: ChatMessage) -> dict[str, Any]:
    content = message.content
    if isinstance(content, list):
        content = [content_block_to_minimax(block) for block in content]
    return {"role": message.role, "content": content}


def content_block_to_minimax(block: ContentBlock) -> ContentBlock:
    block_type = block.get("type")
    if block_type == "tool_call":
        return {
            "type": "tool_use",
            "id": block.get("id"),
            "name": block.get("name"),
            "input": block.get("input", {}),
        }
    if block_type == "tool_result":
        return {
            "type": "tool_result",
            "tool_use_id": block.get("tool_call_id") or block.get("tool_use_id"),
            "content": block.get("content", ""),
        }
    return dict(block)


def extract_content(data: Any) -> list[ContentBlock] | None:
    # Accept both Anthropic-style `content` and legacy chat response payload shapes.
    if not isinstance(data, dict):
        return None
    content = data.get("content")
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    if isinstance(content, list):
        blocks: list[ContentBlock] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            block_type = block.get("type")
            if block_type == "text" and isinstance(block.get("text"), str):
                blocks.append(dict(block))
            elif block_type == "tool_use" and isinstance(block.get("name"), str) and isinstance(block.get("id"), str):
                normalized = {
                    "type": "tool_call",
                    "id": block["id"],
                    "name": block["name"],
                    "input": block["input"] if "input" in block else {},
                }
                blocks.append(normalized)
        if blocks:
            return blocks
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first = choices[0]
    if not isinstance(first, dict):
        return None
    message = first.get("message")
    if isinstance(message, dict) and isinstance(message.get("content"), str):
        return [{"type": "text", "text": message["content"]}]
    text = first.get("text")
    return [{"type": "text", "text": text}] if isinstance(text, str) else None


def content_blocks_to_text(content: list[ContentBlock]) -> str:
    return "".join(block["text"] for block in content if block.get("type") == "text" and isinstance(block.get("text"), str))


def normalize_minimax_api_key(value: str | None) -> str | None:
    # Normalize key input from env or config; return a clean token suitable for Authorization header.
    if value is None:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    # Strip common copied form: "Bearer sk-...".
    if trimmed.lower().startswith("bearer "):
        return trimmed[7:].strip()
    return trimmed


def summarize(value: str, max_length: int = 500) -> str:
    compact = " ".join(value.split())
    if len(compact) <= max_length:
        return compact
    return f"{compact[:max_length]}..."
