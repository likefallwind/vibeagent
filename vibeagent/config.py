from __future__ import annotations

import json
import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping


MINIMAX_PROVIDER = "minimax"
OPENAI_COMPATIBLE_PROVIDERS = {"deepseek", "openai-compatible", "openai_compatible"}
PROJECT_CONFIG_RELATIVE_PATH = Path(".vibeagent") / "config.json"
DEFAULT_MAX_ITERATIONS = 20
DEFAULT_COMMAND_TIMEOUT_MS = 30_000
SECRET_PROJECT_CONFIG_KEYS = {
    "apiKey",
    "api_key",
    "apikey",
    "DEEPSEEK_API_KEY",
    "MINIMAX_API",
    "MINIMAX_API_KEY",
    "OPENAI_COMPAT_API_KEY",
    "minimax_api",
}


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


@dataclass(frozen=True)
class CostRates:
    input_usd_per_million: Decimal | None = None
    output_usd_per_million: Decimal | None = None
    cache_creation_usd_per_million: Decimal | None = None
    cache_read_usd_per_million: Decimal | None = None


@dataclass(frozen=True)
class ExecutionConfig:
    max_iterations: int = DEFAULT_MAX_ITERATIONS
    command_timeout_ms: int = DEFAULT_COMMAND_TIMEOUT_MS


def resolve_provider_config(env: Mapping[str, str | None] | None = None) -> ProviderConfig:
    source = env if env is not None else os.environ
    provider = get_provider_name(source)
    generic_model = source.get("VIBEAGENT_MODEL")
    generic_base_url = source.get("VIBEAGENT_BASE_URL")
    if provider == MINIMAX_PROVIDER:
        key = get_first_api_key(source, ("MINIMAX_API_KEY", "MINIMAX_API", "minimax_api"))
        return ProviderConfig(
            provider=provider,
            model=source.get("MINIMAX_MODEL") or generic_model or "MiniMax-M2.7",
            base_url=(source.get("MINIMAX_BASE_URL") or generic_base_url or "https://api.minimaxi.com/anthropic").rstrip("/"),
            api_key=key.value if key else None,
            api_key_source=key.name if key else None,
        )
    if provider in OPENAI_COMPATIBLE_PROVIDERS:
        key = get_first_api_key(source, ("OPENAI_COMPAT_API_KEY", "DEEPSEEK_API_KEY"))
        return ProviderConfig(
            provider=provider,
            model=source.get("OPENAI_COMPAT_MODEL") or source.get("DEEPSEEK_MODEL") or generic_model or "deepseek-chat",
            base_url=(
                source.get("OPENAI_COMPAT_BASE_URL")
                or source.get("DEEPSEEK_BASE_URL")
                or generic_base_url
                or "https://api.deepseek.com"
            ).rstrip("/"),
            api_key=key.value if key else None,
            api_key_source=key.name if key else None,
        )
    raise ValueError(f"Unsupported VIBEAGENT_PROVIDER: {provider}")


def load_project_config_env(project_root: str | Path) -> dict[str, str]:
    data = read_project_config(project_root)
    env: dict[str, str] = {}
    set_string_config(data, env, "provider", "VIBEAGENT_PROVIDER")
    set_string_config(data, env, "model", "VIBEAGENT_MODEL")
    set_string_config(data, env, "base_url", "VIBEAGENT_BASE_URL")
    set_string_config(data, env, "input_usd_per_million", "VIBEAGENT_INPUT_USD_PER_MILLION")
    set_string_config(data, env, "output_usd_per_million", "VIBEAGENT_OUTPUT_USD_PER_MILLION")
    set_string_config(data, env, "cache_creation_usd_per_million", "VIBEAGENT_CACHE_CREATION_USD_PER_MILLION")
    set_string_config(data, env, "cache_read_usd_per_million", "VIBEAGENT_CACHE_READ_USD_PER_MILLION")
    return env


def read_project_config(project_root: str | Path) -> dict[str, Any]:
    path = project_config_path(project_root)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid .vibeagent/config.json: {error.msg}") from error
    if not isinstance(data, dict):
        raise ValueError(".vibeagent/config.json must contain a JSON object.")
    return dict(data)


def save_project_config(
    project_root: str | Path,
    *,
    provider: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    max_iterations: int | None = None,
    command_timeout_ms: int | None = None,
) -> str:
    updates: dict[str, str | int] = {
        key: value.strip()
        for key, value in {
            "provider": provider,
            "model": model,
            "base_url": base_url,
        }.items()
        if isinstance(value, str) and value.strip()
    }
    if max_iterations is not None:
        updates["max_iterations"] = validate_positive_int(max_iterations, "max_iterations")
    if command_timeout_ms is not None:
        updates["command_timeout_ms"] = validate_timeout_ms(command_timeout_ms, "command_timeout_ms")
    if not updates:
        raise ValueError(
            "Usage: --save-config requires at least one of --provider, --model-name, --base-url, "
            "--max-iterations, or --command-timeout-ms."
        )
    path = project_config_path(project_root)
    data = read_project_config(project_root)
    old_provider = data.get("provider")
    provider_changed = "provider" in updates and updates["provider"] != old_provider
    for key in SECRET_PROJECT_CONFIG_KEYS:
        data.pop(key, None)
    if provider_changed:
        if "model" not in updates:
            data.pop("model", None)
        if "base_url" not in updates:
            data.pop("base_url", None)
    data.update(updates)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return "Saved .vibeagent/config.json."


def project_config_path(project_root: str | Path) -> Path:
    return Path(project_root).expanduser().resolve() / PROJECT_CONFIG_RELATIVE_PATH


def resolve_execution_config(
    project_root: str | Path | None = None,
    *,
    max_iterations: int | None = None,
    command_timeout_ms: int | None = None,
) -> ExecutionConfig:
    data = read_project_config(project_root or ".") if project_root is not None else {}
    configured_iterations = read_optional_positive_int(data, "max_iterations")
    configured_timeout = read_optional_timeout_ms(data, "command_timeout_ms")
    return ExecutionConfig(
        max_iterations=max_iterations if max_iterations is not None else configured_iterations or DEFAULT_MAX_ITERATIONS,
        command_timeout_ms=(
            command_timeout_ms if command_timeout_ms is not None else configured_timeout or DEFAULT_COMMAND_TIMEOUT_MS
        ),
    )


def set_string_config(data: dict[str, Any], env: dict[str, str], key: str, env_name: str) -> None:
    value = data.get(key)
    if isinstance(value, str) and value.strip():
        env[env_name] = value.strip()


def read_optional_positive_int(data: dict[str, Any], key: str) -> int | None:
    if key not in data:
        return None
    return validate_positive_int(data[key], key)


def read_optional_timeout_ms(data: dict[str, Any], key: str) -> int | None:
    if key not in data:
        return None
    return validate_timeout_ms(data[key], key)


def validate_positive_int(value: Any, key: str) -> int:
    parsed = parse_int_config(value, key)
    if parsed <= 0:
        raise ValueError(f".vibeagent/config.json {key} must be a positive integer.")
    return parsed


def validate_timeout_ms(value: Any, key: str) -> int:
    parsed = validate_positive_int(value, key)
    if parsed < 100:
        raise ValueError(f".vibeagent/config.json {key} must be at least 100.")
    return parsed


def parse_int_config(value: Any, key: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f".vibeagent/config.json {key} must be an integer.")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return int(value.strip())
        except ValueError as error:
            raise ValueError(f".vibeagent/config.json {key} must be an integer.") from error
    raise ValueError(f".vibeagent/config.json {key} must be an integer.")


def resolve_cost_rates(env: Mapping[str, str | None] | None = None) -> tuple[CostRates, list[str]]:
    source = env if env is not None else os.environ
    input_rate, input_error = parse_cost_rate(source.get("VIBEAGENT_INPUT_USD_PER_MILLION"), "VIBEAGENT_INPUT_USD_PER_MILLION")
    output_rate, output_error = parse_cost_rate(source.get("VIBEAGENT_OUTPUT_USD_PER_MILLION"), "VIBEAGENT_OUTPUT_USD_PER_MILLION")
    cache_creation_rate, cache_creation_error = parse_cost_rate(
        source.get("VIBEAGENT_CACHE_CREATION_USD_PER_MILLION"),
        "VIBEAGENT_CACHE_CREATION_USD_PER_MILLION",
    )
    cache_read_rate, cache_read_error = parse_cost_rate(
        source.get("VIBEAGENT_CACHE_READ_USD_PER_MILLION"),
        "VIBEAGENT_CACHE_READ_USD_PER_MILLION",
    )
    errors = [
        error
        for error in (input_error, output_error, cache_creation_error, cache_read_error)
        if error is not None
    ]
    return (
        CostRates(
            input_usd_per_million=input_rate,
            output_usd_per_million=output_rate,
            cache_creation_usd_per_million=cache_creation_rate,
            cache_read_usd_per_million=cache_read_rate,
        ),
        errors,
    )


def parse_cost_rate(value: str | None, name: str) -> tuple[Decimal | None, str | None]:
    if value is None or not value.strip():
        return None, None
    try:
        parsed = Decimal(value.strip())
    except InvalidOperation:
        return None, f"{name} must be a non-negative decimal."
    if parsed < 0:
        return None, f"{name} must be a non-negative decimal."
    return parsed, None


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
