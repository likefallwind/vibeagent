from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .config import get_first_api_key, normalize_api_key as normalize_config_api_key, resolve_provider_config
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


def extract_content(data: Any) -> list[ContentBlock] | None:
    if not isinstance(data, dict):
        return None
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
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

    tool_calls = message.get("tool_calls")
    if isinstance(tool_calls, list):
        for tool_call in tool_calls:
            block = parse_tool_call(tool_call)
            if block:
                blocks.append(block)
    return blocks or None


def extract_usage(data: Any) -> ModelUsage | None:
    if not isinstance(data, dict):
        return None
    usage = data.get("usage")
    if not isinstance(usage, dict):
        return None
    input_tokens = parse_nonnegative_int(usage.get("prompt_tokens"))
    output_tokens = parse_nonnegative_int(usage.get("completion_tokens"))
    total_tokens = parse_nonnegative_int(usage.get("total_tokens"))
    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens
    if all(value is None for value in (input_tokens, output_tokens, total_tokens)):
        return None
    return ModelUsage(input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=total_tokens)


def parse_nonnegative_int(value: Any) -> int | None:
    return value if isinstance(value, int) and value >= 0 else None


def parse_tool_call(value: Any) -> ContentBlock | None:
    if not isinstance(value, dict) or not isinstance(value.get("id"), str):
        return None
    function = value.get("function")
    if not isinstance(function, dict) or not isinstance(function.get("name"), str):
        return None
    raw_arguments = function.get("arguments", "{}")
    tool_input: Any
    if isinstance(raw_arguments, str):
        try:
            tool_input = json.loads(raw_arguments or "{}")
        except json.JSONDecodeError:
            tool_input = raw_arguments
    else:
        tool_input = raw_arguments
    return {"type": "tool_call", "id": value["id"], "name": function["name"], "input": tool_input}


def normalize_api_key(value: str | None) -> str | None:
    return normalize_config_api_key(value)


def summarize(value: str, max_length: int = 500) -> str:
    compact = " ".join(value.split())
    if len(compact) <= max_length:
        return compact
    return f"{compact[:max_length]}..."
