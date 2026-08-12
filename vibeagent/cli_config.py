from __future__ import annotations

import argparse
from collections.abc import Mapping
from pathlib import Path

from .anthropic_betas import anthropic_beta_header
from .config import load_project_config_env, project_config_path, read_project_config, save_project_config
from .providers import get_provider_name
from .workspace_environment import workspace_process_environment_from_root
from .invocation_settings import parse_invocation_settings, parse_setting_sources


def resolve_project_root(value: str | None) -> Path | None:
    if value is None:
        return None
    root = Path(value).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Project directory not found: {value}")
    return root


def build_provider_env(
    args: argparse.Namespace | None,
    project_root: Path | None = None,
    *,
    trust_project_settings: bool = False,
) -> dict[str, str | None]:
    config_root = project_root or Path.cwd()
    setting_sources = (
        ()
        if getattr(args, "bare", False)
        else parse_setting_sources(getattr(args, "setting_sources", None))
    )
    settings_override_json = parse_invocation_settings(
        getattr(args, "settings", None),
        invocation_root=Path.cwd(),
    )
    env: dict[str, str | None] = workspace_process_environment_from_root(
        config_root,
        trust_project_settings=trust_project_settings,
        setting_sources=setting_sources,
        settings_override_json=settings_override_json,
    )
    for key, value in load_project_config_env(config_root).items():
        if not env.get(key):
            env[key] = value
    arg_provider = getattr(args, "provider", None)
    arg_model_name = model_override_from_args(args)
    arg_base_url = getattr(args, "base_url", None)
    arg_api_key = getattr(args, "api_key", None)
    provider = arg_provider or get_provider_name(env)
    beta_header = anthropic_beta_header(getattr(args, "betas", None))
    if beta_header is not None and provider != "anthropic":
        raise ValueError("--betas is available only with --provider anthropic.")
    if arg_provider:
        env["VIBEAGENT_PROVIDER"] = arg_provider
    if arg_model_name:
        env = provider_env_with_model_override(env, arg_model_name, provider=provider)
    if arg_base_url:
        if provider == "minimax":
            env["MINIMAX_BASE_URL"] = arg_base_url
        elif provider == "anthropic":
            env["ANTHROPIC_BASE_URL"] = arg_base_url
        else:
            env["OPENAI_COMPAT_BASE_URL"] = arg_base_url
            env["DEEPSEEK_BASE_URL"] = arg_base_url
    if arg_api_key:
        if provider == "minimax":
            env["MINIMAX_API_KEY"] = arg_api_key
        elif provider == "anthropic":
            env["ANTHROPIC_API_KEY"] = arg_api_key
        else:
            env["OPENAI_COMPAT_API_KEY"] = arg_api_key
            env["DEEPSEEK_API_KEY"] = arg_api_key
    if beta_header is not None:
        env["ANTHROPIC_BETA"] = beta_header
    return env


def provider_env_overrides_from_args(
    args: argparse.Namespace,
    project_root: Path,
) -> tuple[tuple[str, str], ...]:
    requested = any(
        (
            getattr(args, "provider", None),
            model_override_from_args(args),
            getattr(args, "base_url", None),
            getattr(args, "api_key", None),
            getattr(args, "betas", None),
        )
    )
    if not requested:
        return ()
    resolved = build_provider_env(args, project_root)
    provider = get_provider_name(resolved)
    keys = ["VIBEAGENT_PROVIDER"] if getattr(args, "provider", None) else []
    if model_override_from_args(args) is not None:
        keys.append(_provider_key(provider, "MODEL"))
    if getattr(args, "base_url", None) is not None:
        keys.append(_provider_key(provider, "BASE_URL"))
    if getattr(args, "api_key", None) is not None:
        keys.append(_provider_key(provider, "API_KEY"))
    if getattr(args, "betas", None):
        keys.append("ANTHROPIC_BETA")
    return tuple(
        (key, value)
        for key in keys
        if isinstance((value := resolved.get(key)), str)
    )


def apply_provider_env_overrides(
    env: dict[str, str | None],
    overrides: Mapping[str, str] | tuple[tuple[str, str], ...],
) -> dict[str, str | None]:
    updated = dict(env)
    updated.update(dict(overrides))
    return updated


def _provider_key(provider: str, suffix: str) -> str:
    if provider == "minimax":
        return f"MINIMAX_{suffix}"
    if provider == "anthropic":
        return f"ANTHROPIC_{suffix}"
    if provider == "deepseek":
        return f"DEEPSEEK_{suffix}"
    return f"OPENAI_COMPAT_{suffix}"


def provider_env_with_model_override(
    env: dict[str, str | None],
    model: str,
    *,
    provider: str | None = None,
) -> dict[str, str | None]:
    updated = dict(env)
    active_provider = provider or get_provider_name(updated)
    if active_provider == "minimax":
        updated["MINIMAX_MODEL"] = model
    elif active_provider == "anthropic":
        updated["ANTHROPIC_MODEL"] = model
    else:
        updated["OPENAI_COMPAT_MODEL"] = model
        updated["DEEPSEEK_MODEL"] = model
    return updated


def save_project_config_from_args(args: argparse.Namespace, project_root: str | Path) -> str:
    if args.api_key:
        raise ValueError("--save-config does not write API keys. Use environment variables or --api-key for one command.")
    return save_project_config(
        project_root,
        provider=args.provider,
        model=model_override_from_args(args),
        base_url=args.base_url,
        max_iterations=args.max_iterations,
        command_timeout_ms=args.command_timeout_ms,
        max_output_tokens=args.max_output_tokens,
        model_retries=args.model_retries,
        model_retry_delay_ms=args.model_retry_delay_ms,
        model_timeout_ms=args.model_timeout_ms,
    )


def save_project_config_report_from_args(args: argparse.Namespace, project_root: str | Path) -> dict[str, object]:
    root = Path(project_root).resolve()
    path = project_config_path(root)
    existed_before = path.exists()
    message = save_project_config_from_args(args, root)
    config = read_project_config(root)
    written_keys = [
        key
        for key, value in {
            "provider": args.provider,
            "model": model_override_from_args(args),
            "base_url": args.base_url,
            "max_iterations": args.max_iterations,
            "command_timeout_ms": args.command_timeout_ms,
            "max_output_tokens": args.max_output_tokens,
            "model_retries": args.model_retries,
            "model_retry_delay_ms": args.model_retry_delay_ms,
            "model_timeout_ms": args.model_timeout_ms,
        }.items()
        if value is not None and (not isinstance(value, str) or value.strip())
    ]
    return {
        "projectRoot": str(root),
        "path": str(path),
        "ok": True,
        "created": not existed_before and path.exists(),
        "existedBefore": existed_before,
        "exists": path.exists(),
        "writtenKeys": written_keys,
        "config": config,
        "message": message,
    }


def model_override_from_args(args: argparse.Namespace | None) -> str | None:
    if args is None:
        return None
    model = getattr(args, "model", None)
    if isinstance(model, str):
        return model
    model_name = getattr(args, "model_name", None)
    return model_name if isinstance(model_name, str) else None


def format_save_config_report_text(report: dict[str, object]) -> str:
    return str(report.get("message") or "")
