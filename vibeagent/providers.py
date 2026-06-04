from __future__ import annotations

from typing import Mapping

from .config import OPENAI_COMPATIBLE_PROVIDERS, get_provider_name as get_config_provider_name, resolve_provider_config
from .minimax import MiniMaxClient, MissingMiniMaxApiKeyError
from .openai_compat import MissingOpenAICompatibleApiKeyError, OpenAICompatibleClient
from .types import ChatClient


def get_provider_name(env: Mapping[str, str | None] | None = None) -> str:
    return get_config_provider_name(env)


def create_chat_client(env: Mapping[str, str | None] | None = None) -> ChatClient:
    config = resolve_provider_config(env)
    if config.provider == "minimax":
        if not config.api_key:
            raise MissingMiniMaxApiKeyError()
        return MiniMaxClient(
            api_key=config.api_key,
            base_url=config.base_url,
            model=config.model,
        )
    if config.provider in OPENAI_COMPATIBLE_PROVIDERS:
        if not config.api_key:
            raise MissingOpenAICompatibleApiKeyError()
        return OpenAICompatibleClient(
            api_key=config.api_key,
            base_url=config.base_url,
            model=config.model,
        )
    raise ValueError(f"Unsupported VIBEAGENT_PROVIDER: {config.provider}")


def get_model_text(env: Mapping[str, str | None] | None = None) -> str:
    try:
        config = resolve_provider_config(env)
    except ValueError as error:
        return str(error)

    if config.provider == "minimax":
        return "\n".join(
            [
                "Model provider: minimax",
                f"  model: {config.model}",
                f"  baseUrl: {config.base_url}",
                f"  apiKey: {'configured via ' + config.api_key_source if config.api_key_source else 'missing'}",
            ]
        )
    if config.provider in OPENAI_COMPATIBLE_PROVIDERS:
        return "\n".join(
            [
                f"Model provider: {config.provider}",
                f"  model: {config.model}",
                f"  baseUrl: {config.base_url}",
                f"  apiKey: {'configured via ' + config.api_key_source if config.api_key_source else 'missing'}",
            ]
        )
    return f"Unsupported VIBEAGENT_PROVIDER: {config.provider}"
