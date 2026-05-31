from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .types import ChatMessage, ChatClient


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
        normalized_key = normalize_minimax_api_key(api_key) or get_minimax_api_key_from_env()
        if not normalized_key:
            raise MissingMiniMaxApiKeyError()

        defaults = get_minimax_defaults()
        self.api_key = normalized_key
        self.base_url = (base_url or defaults["base_url"]).rstrip("/")
        self.model = model or defaults["model"]

    def complete(self, messages: list[ChatMessage]) -> str:
        body = json.dumps(
            {
                "model": self.model,
                "messages": [message.__dict__ for message in messages],
                "temperature": 0.2,
            }
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
            raise MiniMaxResponseError(
                f"MiniMax response did not include choices[0].message.content: {summarize(text)}"
            )

        return content


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
    source = env if env is not None else os.environ
    return {
        "base_url": (source.get("MINIMAX_BASE_URL") or "https://api.minimax.io/v1").rstrip("/"),
        "model": source.get("MINIMAX_MODEL") or "MiniMax-M2.7",
    }


def extract_content(data: Any) -> str | None:
    if not isinstance(data, dict):
        return None
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first = choices[0]
    if not isinstance(first, dict):
        return None
    message = first.get("message")
    if isinstance(message, dict) and isinstance(message.get("content"), str):
        return message["content"]
    text = first.get("text")
    return text if isinstance(text, str) else None


def normalize_minimax_api_key(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    if trimmed.lower().startswith("bearer "):
        return trimmed[7:].strip()
    return trimmed


def summarize(value: str, max_length: int = 500) -> str:
    compact = " ".join(value.split())
    if len(compact) <= max_length:
        return compact
    return f"{compact[:max_length]}..."
