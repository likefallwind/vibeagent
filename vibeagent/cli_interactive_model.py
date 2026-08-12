from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from .cli_config import (
    apply_provider_env_overrides,
    build_provider_env,
    provider_env_with_model_override,
)
from .config import resolve_provider_config


MAX_INTERACTIVE_MODEL_CHARS = 200


@dataclass(frozen=True)
class InteractiveModelSelection:
    override: str | None
    provider_env: dict[str, str | None]
    changed: bool
    text: str


def resolve_interactive_model_selection(
    project_root: str | Path,
    argument: str | None,
    current_override: str | None,
    *,
    setting_sources: tuple[str, ...] = ("user", "project", "local"),
    settings_override_json: str | None = None,
    provider_env_overrides: tuple[tuple[str, str], ...] = (),
) -> InteractiveModelSelection:
    if argument is None:
        override = current_override
    else:
        override = normalize_interactive_model(argument)

    provider_env = interactive_provider_env(
        project_root,
        override,
        setting_sources=setting_sources,
        settings_override_json=settings_override_json,
        provider_env_overrides=provider_env_overrides,
    )
    provider = resolve_provider_config(provider_env)
    changed = argument is not None and override != current_override
    source = "session override" if override is not None else "configured default"
    action = "Switched interactive model." if changed else "Interactive model configuration."
    return InteractiveModelSelection(
        override=override,
        provider_env=provider_env,
        changed=changed,
        text="\n".join(
            [
                action,
                f"  provider: {provider.provider}",
                f"  model: {provider.model}",
                f"  source: {source}",
            ]
        ),
    )


def interactive_provider_env(
    project_root: str | Path,
    model_override: str | None,
    *,
    setting_sources: tuple[str, ...] = ("user", "project", "local"),
    settings_override_json: str | None = None,
    provider_env_overrides: tuple[tuple[str, str], ...] = (),
) -> dict[str, str | None]:
    env = build_provider_env(
        argparse.Namespace(
            setting_sources=",".join(setting_sources),
            settings=settings_override_json,
            provider=None,
            model=None,
            model_name=None,
            base_url=None,
            api_key=None,
        ),
        Path(project_root),
    )
    env = apply_provider_env_overrides(env, provider_env_overrides)
    if model_override is None:
        return env
    return provider_env_with_model_override(env, model_override)


def normalize_interactive_model(value: str) -> str | None:
    normalized = value.strip()
    if normalized.lower() == "default":
        return None
    if not normalized:
        raise ValueError("Usage: /model [model-name|default]")
    if len(normalized) > MAX_INTERACTIVE_MODEL_CHARS:
        raise ValueError(
            f"Interactive model name must be at most {MAX_INTERACTIVE_MODEL_CHARS} characters."
        )
    if any(ord(character) < 32 or ord(character) == 127 for character in normalized):
        raise ValueError("Interactive model name cannot contain control characters.")
    if any(character.isspace() for character in normalized):
        raise ValueError("Interactive model name cannot contain whitespace.")
    return normalized


__all__ = [
    "InteractiveModelSelection",
    "interactive_provider_env",
    "normalize_interactive_model",
    "resolve_interactive_model_selection",
]
