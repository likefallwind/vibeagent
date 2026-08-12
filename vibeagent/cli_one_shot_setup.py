from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .cli_config import build_provider_env
from .cli_mcp_args import resolve_mcp_config_paths
from .cli_one_shot_input import resolve_one_shot_code_task
from .config import ExecutionConfig, resolve_execution_config


@dataclass(frozen=True)
class OneShotProjectSetup:
    task: str
    task_metadata: dict[str, object] | None
    mcp_config_paths: tuple[Path, ...]


@dataclass(frozen=True)
class OneShotRuntimeSetup:
    execution_config: ExecutionConfig
    provider_env: dict[str, str | None]


def resolve_one_shot_project_setup(
    task: str,
    *,
    request_mode: str,
    project_root: Path,
    mcp_config_paths: list[str] | tuple[str, ...] | None,
    safe_mode: bool = False,
    bare_mode: bool = False,
    invocation_plugin_dirs: tuple[Path, ...] = (),
    resolve_code_task_func: Callable[..., tuple[str, dict[str, object] | None]] = resolve_one_shot_code_task,
    resolve_mcp_config_paths_func: Callable[[Path, list[str] | tuple[str, ...] | None], tuple[Path, ...]] = (
        resolve_mcp_config_paths
    ),
) -> OneShotProjectSetup:
    task_kwargs: dict[str, object] = {
        "request_mode": request_mode,
        "project_root": project_root,
    }
    if safe_mode:
        task_kwargs["safe_mode"] = True
    if bare_mode:
        task_kwargs["bare_mode"] = True
    if invocation_plugin_dirs:
        task_kwargs["invocation_plugin_dirs"] = invocation_plugin_dirs
    resolved_task, task_metadata = resolve_code_task_func(task, **task_kwargs)
    resolved_mcp_config_paths = (
        ()
        if safe_mode
        else resolve_mcp_config_paths_func(project_root, mcp_config_paths)
    )
    return OneShotProjectSetup(
        task=resolved_task,
        task_metadata=task_metadata,
        mcp_config_paths=resolved_mcp_config_paths,
    )


def resolve_one_shot_runtime_setup(
    *,
    config_root: Path,
    provider_args: object | None,
    max_iterations: int | None = None,
    command_timeout_ms: int | None = None,
    max_output_tokens: int | None = None,
    model_retries: int | None = None,
    model_retry_delay_ms: int | None = None,
    model_timeout_ms: int | None = None,
    trust_project_settings: bool = False,
    resolve_execution_config_func: Callable[..., ExecutionConfig] = resolve_execution_config,
    build_provider_env_func: Callable[..., dict[str, str | None]] = build_provider_env,
) -> OneShotRuntimeSetup:
    execution_config = resolve_execution_config_func(
        config_root,
        max_iterations=max_iterations,
        command_timeout_ms=command_timeout_ms,
        max_output_tokens=max_output_tokens,
        model_retries=model_retries,
        model_retry_delay_ms=model_retry_delay_ms,
        model_timeout_ms=model_timeout_ms,
    )
    if trust_project_settings:
        provider_env = build_provider_env_func(
            provider_args,
            config_root,
            trust_project_settings=trust_project_settings,
        )
    else:
        provider_env = build_provider_env_func(provider_args, config_root)
    return OneShotRuntimeSetup(execution_config=execution_config, provider_env=provider_env)
