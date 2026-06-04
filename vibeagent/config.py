from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping


MINIMAX_PROVIDER = "minimax"
OPENAI_COMPATIBLE_PROVIDERS = {"deepseek", "openai-compatible", "openai_compatible"}


@dataclass(frozen=True)
class ApiKeyInfo:
    name: str
    value: str


@dataclass(frozen=True)
class ProviderConfig:
    provider: str
    model: str
    base_url: str
    api_key: str | None
    api_key_source: str | None


def resolve_provider_config(env: Mapping[str, str | None] | None = None) -> ProviderConfig:
    source = env if env is not None else os.environ
    provider = get_provider_name(source)
    if provider == MINIMAX_PROVIDER:
        key = get_first_api_key(source, ("MINIMAX_API_KEY", "MINIMAX_API", "minimax_api"))
        return ProviderConfig(
            provider=provider,
            model=source.get("MINIMAX_MODEL") or "MiniMax-M2.7",
            base_url=(source.get("MINIMAX_BASE_URL") or "https://api.minimaxi.com/anthropic").rstrip("/"),
            api_key=key.value if key else None,
            api_key_source=key.name if key else None,
        )
    if provider in OPENAI_COMPATIBLE_PROVIDERS:
        key = get_first_api_key(source, ("OPENAI_COMPAT_API_KEY", "DEEPSEEK_API_KEY"))
        return ProviderConfig(
            provider=provider,
            model=source.get("OPENAI_COMPAT_MODEL") or source.get("DEEPSEEK_MODEL") or "deepseek-chat",
            base_url=(
                source.get("OPENAI_COMPAT_BASE_URL")
                or source.get("DEEPSEEK_BASE_URL")
                or "https://api.deepseek.com"
            ).rstrip("/"),
            api_key=key.value if key else None,
            api_key_source=key.name if key else None,
        )
    raise ValueError(f"Unsupported VIBEAGENT_PROVIDER: {provider}")


def get_provider_name(env: Mapping[str, str | None] | None = None) -> str:
    source = env if env is not None else os.environ
    return (source.get("VIBEAGENT_PROVIDER") or MINIMAX_PROVIDER).strip().lower()


def get_first_api_key(source: Mapping[str, str | None], names: tuple[str, ...]) -> ApiKeyInfo | None:
    for name in names:
        value = normalize_api_key(source.get(name))
        if value:
            return ApiKeyInfo(name=name, value=value)
    return None


def normalize_api_key(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    if trimmed.lower().startswith("bearer "):
        return trimmed[7:].strip()
    return trimmed
