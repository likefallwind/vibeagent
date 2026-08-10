from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .config import get_first_api_key, normalize_api_key as normalize_config_api_key, resolve_provider_config
from .openai_compat_messages import (
    flatten_messages,
    flatten_tool_results,
    image_block_to_openai,
    openai_image_blocks,
    tool_call_to_openai,
    tool_to_openai,
)
from .provider_tool_calls import parse_function_tool_call, parse_responses_function_call
from .types import AssistantResponse, ChatMessage, ChatClient, ContentBlock, ModelUsage, ToolSpec


class MissingOpenAICompatibleApiKeyError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("Missing OpenAI-compatible API key. Set OPENAI_COMPAT_API_KEY or DEEPSEEK_API_KEY.")


class OpenAICompatibleHttpError(RuntimeError):
    def __init__(self, status: int, response_text: str) -> None:
        self.status = status
        self.response_text = response_text
        super().__init__(f"OpenAI-compatible API returned HTTP {status}: {summarize(response_text)}")


class OpenAICompatibleResponseError(RuntimeError):
    pass


@dataclass(frozen=True)
class OpenAICompatibleApiKeyInfo:
    name: str
    value: str


class OpenAICompatibleClient(ChatClient):
    def __init__(self, api_key: str | None = None, base_url: str | None = None, model: str | None = None) -> None:
        normalized_key = normalize_api_key(api_key) or get_openai_compatible_api_key_from_env()
        if not normalized_key:
            raise MissingOpenAICompatibleApiKeyError()

        defaults = get_openai_compatible_defaults()
        self.api_key = normalized_key
        self.base_url = (base_url or defaults["base_url"]).rstrip("/")
        self.model = model or defaults["model"]

    def with_agent_profile(
        self,
        *,
        model: str | None,
        effort: str | None,
    ) -> "OpenAICompatibleClient":
        if effort is not None:
            raise ValueError(
                "OpenAI-compatible providers do not support Claude agent profile effort overrides."
            )
        return OpenAICompatibleClient(
            api_key=self.api_key,
            base_url=self.base_url,
            model=model or self.model,
        )

    def complete(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        timeout_ms: int = 120_000,
    ) -> AssistantResponse:
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
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=timeout_ms / 1000) as response:
                text = response.read().decode("utf-8")
        except HTTPError as error:
            text = error.read().decode("utf-8", errors="replace")
            raise OpenAICompatibleHttpError(error.code, text) from error

        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            raise OpenAICompatibleResponseError(f"OpenAI-compatible response was not JSON: {error}") from error

        content = extract_content(data)
        if not content:
            raise OpenAICompatibleResponseError(
                f"OpenAI-compatible response did not include structured content: {summarize(text)}"
            )
        return AssistantResponse(content=content, raw=data, usage=extract_usage(data))


def get_openai_compatible_api_key_from_env(env: Mapping[str, str | None] | None = None) -> str | None:
    info = get_openai_compatible_api_key_info_from_env(env)
    return info.value if info else None


def get_openai_compatible_api_key_info_from_env(
    env: Mapping[str, str | None] | None = None,
) -> OpenAICompatibleApiKeyInfo | None:
    source = env if env is not None else os.environ
    key = get_first_api_key(source, ("OPENAI_COMPAT_API_KEY", "DEEPSEEK_API_KEY"))
    return OpenAICompatibleApiKeyInfo(name=key.name, value=key.value) if key else None


def get_openai_compatible_defaults(env: Mapping[str, str | None] | None = None) -> dict[str, str]:
    source = dict(os.environ if env is None else env)
    source["VIBEAGENT_PROVIDER"] = "deepseek"
    config = resolve_provider_config(source)
    return {
        "base_url": config.base_url,
        "model": config.model,
    }


def build_request_body(
    model: str,
    messages: list[ChatMessage],
    tools: list[ToolSpec] | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.2,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": model,
        "messages": flatten_messages(messages),
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if tools:
        body["tools"] = [tool_to_openai(tool) for tool in tools]
        body["tool_choice"] = "auto"
    return body


def extract_content(data: Any) -> list[ContentBlock] | None:
    if not isinstance(data, dict):
        return None
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return extract_responses_output_content(data)
    first = choices[0]
    if not isinstance(first, dict):
        return None
    message = first.get("message")
    if not isinstance(message, dict):
        return None

    blocks: list[ContentBlock] = []
    content = message.get("content")
    if isinstance(content, str) and content:
        blocks.append({"type": "text", "text": content})
    elif isinstance(content, list):
        for text in text_chunks_from_openai_content(content):
            blocks.append({"type": "text", "text": text})

    tool_calls = message.get("tool_calls")
    if isinstance(tool_calls, list):
        for tool_call in tool_calls:
            block = parse_function_tool_call(tool_call)
            if block:
                blocks.append(block)
    return blocks or None


def extract_responses_output_content(data: dict[str, Any]) -> list[ContentBlock] | None:
    output = data.get("output")
    if not isinstance(output, list):
        return None
    blocks: list[ContentBlock] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        item_type = item.get("type")
        if item_type == "message":
            content = item.get("content")
            if isinstance(content, list):
                for text in text_chunks_from_openai_content(content):
                    blocks.append({"type": "text", "text": text})
            continue
        block = parse_responses_function_call(item)
        if block is not None:
            blocks.append(block)
    return blocks or None


def text_chunks_from_openai_content(content: list[Any]) -> tuple[str, ...]:
    chunks: list[str] = []
    for item in content:
        if isinstance(item, str):
            if item:
                chunks.append(item)
            continue
        if not isinstance(item, dict):
            continue
        item_type = item.get("type")
        if item_type not in {None, "text", "output_text", "input_text"}:
            continue
        text = item.get("text")
        if isinstance(text, str) and text:
            chunks.append(text)
    return tuple(chunks)


def extract_usage(data: Any) -> ModelUsage | None:
    if not isinstance(data, dict):
        return None
    usage = data.get("usage")
    if not isinstance(usage, dict):
        return None
    input_tokens = parse_nonnegative_int(usage.get("prompt_tokens"))
    if input_tokens is None:
        input_tokens = parse_nonnegative_int(usage.get("input_tokens"))
    output_tokens = parse_nonnegative_int(usage.get("completion_tokens"))
    if output_tokens is None:
        output_tokens = parse_nonnegative_int(usage.get("output_tokens"))
    total_tokens = parse_nonnegative_int(usage.get("total_tokens"))
    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens
    if all(value is None for value in (input_tokens, output_tokens, total_tokens)):
        return None
    return ModelUsage(input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=total_tokens)


def parse_nonnegative_int(value: Any) -> int | None:
    return value if isinstance(value, int) and value >= 0 else None


def normalize_api_key(value: str | None) -> str | None:
    return normalize_config_api_key(value)


def summarize(value: str, max_length: int = 500) -> str:
    compact = " ".join(value.split())
    if len(compact) <= max_length:
        return compact
    return f"{compact[:max_length]}..."
