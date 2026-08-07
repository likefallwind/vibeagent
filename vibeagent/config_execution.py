from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .config_validation import validate_nonnegative_int, validate_positive_int, validate_timeout_ms

DEFAULT_MAX_ITERATIONS = 20
DEFAULT_COMMAND_TIMEOUT_MS = 30_000
DEFAULT_MAX_OUTPUT_TOKENS = 4096
DEFAULT_MODEL_RETRIES = 1
DEFAULT_MODEL_RETRY_DELAY_MS = 250
DEFAULT_MODEL_TIMEOUT_MS = 120_000


@dataclass(frozen=True)
class ExecutionConfig:
    max_iterations: int = DEFAULT_MAX_ITERATIONS
    command_timeout_ms: int = DEFAULT_COMMAND_TIMEOUT_MS
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS
    model_retries: int = DEFAULT_MODEL_RETRIES
    model_retry_delay_ms: int = DEFAULT_MODEL_RETRY_DELAY_MS
    model_timeout_ms: int = DEFAULT_MODEL_TIMEOUT_MS


def resolve_execution_config(
    project_root: str | Path | None = None,
    *,
    max_iterations: int | None = None,
    command_timeout_ms: int | None = None,
    max_output_tokens: int | None = None,
    model_retries: int | None = None,
    model_retry_delay_ms: int | None = None,
    model_timeout_ms: int | None = None,
    read_project_config_func: Callable[[str | Path], dict[str, Any]],
) -> ExecutionConfig:
    data = read_project_config_func(project_root or ".") if project_root is not None else {}
    configured_iterations = read_optional_positive_int(data, "max_iterations")
    configured_timeout = read_optional_timeout_ms(data, "command_timeout_ms")
    configured_max_output_tokens = read_optional_positive_int(data, "max_output_tokens")
    configured_model_retries = read_optional_nonnegative_int(data, "model_retries")
    configured_model_retry_delay_ms = read_optional_nonnegative_int(data, "model_retry_delay_ms")
    configured_model_timeout_ms = read_optional_timeout_ms(data, "model_timeout_ms")
    return ExecutionConfig(
        max_iterations=max_iterations if max_iterations is not None else configured_iterations or DEFAULT_MAX_ITERATIONS,
        command_timeout_ms=(
            command_timeout_ms if command_timeout_ms is not None else configured_timeout or DEFAULT_COMMAND_TIMEOUT_MS
        ),
        max_output_tokens=(
            max_output_tokens
            if max_output_tokens is not None
            else configured_max_output_tokens or DEFAULT_MAX_OUTPUT_TOKENS
        ),
        model_retries=(
            model_retries
            if model_retries is not None
            else configured_model_retries
            if configured_model_retries is not None
            else DEFAULT_MODEL_RETRIES
        ),
        model_retry_delay_ms=(
            model_retry_delay_ms
            if model_retry_delay_ms is not None
            else configured_model_retry_delay_ms
            if configured_model_retry_delay_ms is not None
            else DEFAULT_MODEL_RETRY_DELAY_MS
        ),
        model_timeout_ms=(
            model_timeout_ms
            if model_timeout_ms is not None
            else configured_model_timeout_ms
            if configured_model_timeout_ms is not None
            else DEFAULT_MODEL_TIMEOUT_MS
        ),
    )


def read_optional_positive_int(data: dict[str, Any], key: str) -> int | None:
    if key not in data:
        return None
    return validate_positive_int(data[key], key)


def read_optional_nonnegative_int(data: dict[str, Any], key: str) -> int | None:
    if key not in data:
        return None
    return validate_nonnegative_int(data[key], key)


def read_optional_timeout_ms(data: dict[str, Any], key: str) -> int | None:
    if key not in data:
        return None
    return validate_timeout_ms(data[key], key)
