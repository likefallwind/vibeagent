from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

from .config_costs import parse_cost_rate, resolve_cost_rates as resolve_config_cost_rates
from .config_execution import (
    DEFAULT_COMMAND_TIMEOUT_MS,
    DEFAULT_MAX_ITERATIONS,
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_MODEL_RETRIES,
    DEFAULT_MODEL_RETRY_DELAY_MS,
    DEFAULT_MODEL_TIMEOUT_MS,
    ExecutionConfig,
    read_optional_nonnegative_int,
    read_optional_positive_int,
    read_optional_timeout_ms,
    resolve_execution_config as resolve_config_execution,
)
from .config_provider import (
    ANTHROPIC_PROVIDER,
    MINIMAX_PROVIDER,
    OPENAI_COMPATIBLE_PROVIDERS,
    ApiKeyInfo,
    ProviderConfig,
    get_first_api_key,
    get_provider_name,
    normalize_api_key,
    resolve_provider_config,
)
from .config_validation import parse_int_config, validate_nonnegative_int, validate_positive_int, validate_timeout_ms


PROJECT_CONFIG_RELATIVE_PATH = Path(".vibeagent") / "config.json"
SECRET_PROJECT_CONFIG_KEYS = {
    "apiKey",
    "api_key",
    "apikey",
    "DEEPSEEK_API_KEY",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "MINIMAX_API",
    "MINIMAX_API_KEY",
    "OPENAI_COMPAT_API_KEY",
    "minimax_api",
}


@dataclass(frozen=True)
class CostRates:
    input_usd_per_million: Decimal | None = None
    output_usd_per_million: Decimal | None = None
    cache_creation_usd_per_million: Decimal | None = None
    cache_read_usd_per_million: Decimal | None = None


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
    max_output_tokens: int | None = None,
    model_retries: int | None = None,
    model_retry_delay_ms: int | None = None,
    model_timeout_ms: int | None = None,
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
    if max_output_tokens is not None:
        updates["max_output_tokens"] = validate_positive_int(max_output_tokens, "max_output_tokens")
    if model_retries is not None:
        updates["model_retries"] = validate_nonnegative_int(model_retries, "model_retries")
    if model_retry_delay_ms is not None:
        updates["model_retry_delay_ms"] = validate_nonnegative_int(model_retry_delay_ms, "model_retry_delay_ms")
    if model_timeout_ms is not None:
        updates["model_timeout_ms"] = validate_timeout_ms(model_timeout_ms, "model_timeout_ms")
    if not updates:
        raise ValueError(
            "Usage: --save-config requires at least one of --provider, --model/--model-name, --base-url, "
            "--max-iterations, --command-timeout-ms, --max-output-tokens, --model-retries, "
            "--model-retry-delay-ms, or --model-timeout-ms."
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
    max_output_tokens: int | None = None,
    model_retries: int | None = None,
    model_retry_delay_ms: int | None = None,
    model_timeout_ms: int | None = None,
) -> ExecutionConfig:
    return resolve_config_execution(
        project_root,
        max_iterations=max_iterations,
        command_timeout_ms=command_timeout_ms,
        max_output_tokens=max_output_tokens,
        model_retries=model_retries,
        model_retry_delay_ms=model_retry_delay_ms,
        model_timeout_ms=model_timeout_ms,
        read_project_config_func=read_project_config,
    )


def set_string_config(data: dict[str, Any], env: dict[str, str], key: str, env_name: str) -> None:
    value = data.get(key)
    if isinstance(value, str) and value.strip():
        env[env_name] = value.strip()


def resolve_cost_rates(env: Mapping[str, str | None] | None = None) -> tuple[CostRates, list[str]]:
    return resolve_config_cost_rates(env, cost_rates_factory=CostRates)
