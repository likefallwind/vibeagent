from __future__ import annotations

import os
from typing import Mapping

from .minimax import MiniMaxClient, get_minimax_api_key_from_env, get_minimax_api_key_info_from_env, get_minimax_defaults
from .openai_compat import (
    OpenAICompatibleClient,
    get_openai_compatible_api_key_from_env,
    get_openai_compatible_api_key_info_from_env,
    get_openai_compatible_defaults,
)
from .types import ChatClient


def get_provider_name(env: Mapping[str, str | None] | None = None) -> str:
    source = env if env is not None else os.environ
    return (source.get("VIBEAGENT_PROVIDER") or "minimax").strip().lower()


def create_chat_client(env: Mapping[str, str | None] | None = None) -> ChatClient:
    provider = get_provider_name(env)
    if provider == "minimax":
        defaults = get_minimax_defaults(env)
        return MiniMaxClient(
            api_key=get_minimax_api_key_from_env(env),
            base_url=defaults["base_url"],
            model=defaults["model"],
        )
    if provider in {"deepseek", "openai-compatible", "openai_compatible"}:
        defaults = get_openai_compatible_defaults(env)
        return OpenAICompatibleClient(
            api_key=get_openai_compatible_api_key_from_env(env),
            base_url=defaults["base_url"],
            model=defaults["model"],
        )
    raise ValueError(f"Unsupported VIBEAGENT_PROVIDER: {provider}")


def get_model_text(env: Mapping[str, str | None] | None = None) -> str:
    provider = get_provider_name(env)
    if provider == "minimax":
        defaults = get_minimax_defaults(env)
        api_key = get_minimax_api_key_info_from_env(env)
        return "\n".join(
            [
                "Model provider: minimax",
                f"  model: {defaults['model']}",
                f"  baseUrl: {defaults['base_url']}",
                f"  apiKey: {'configured via ' + api_key.name if api_key else 'missing'}",
            ]
        )
    if provider in {"deepseek", "openai-compatible", "openai_compatible"}:
        defaults = get_openai_compatible_defaults(env)
        api_key = get_openai_compatible_api_key_info_from_env(env)
        return "\n".join(
            [
                f"Model provider: {provider}",
                f"  model: {defaults['model']}",
                f"  baseUrl: {defaults['base_url']}",
                f"  apiKey: {'configured via ' + api_key.name if api_key else 'missing'}",
            ]
        )
    return f"Unsupported VIBEAGENT_PROVIDER: {provider}"
