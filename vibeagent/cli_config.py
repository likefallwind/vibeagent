from __future__ import annotations

import argparse
import os
from pathlib import Path

from .config import load_project_config_env, project_config_path, read_project_config, save_project_config
from .providers import get_provider_name


def resolve_project_root(value: str | None) -> Path | None:
    if value is None:
        return None
    root = Path(value).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Project directory not found: {value}")
    return root


def build_provider_env(args: argparse.Namespace | None, project_root: Path | None = None) -> dict[str, str | None]:
    env: dict[str, str | None] = dict(os.environ)
    config_root = project_root or Path.cwd()
    for key, value in load_project_config_env(config_root).items():
        if not env.get(key):
            env[key] = value
    arg_provider = getattr(args, "provider", None)
    arg_model_name = model_override_from_args(args)
    arg_base_url = getattr(args, "base_url", None)
    arg_api_key = getattr(args, "api_key", None)
    provider = arg_provider or get_provider_name(env)
    if arg_provider:
        env["VIBEAGENT_PROVIDER"] = arg_provider
    if arg_model_name:
        if provider == "minimax":
            env["MINIMAX_MODEL"] = arg_model_name
        elif provider == "anthropic":
            env["ANTHROPIC_MODEL"] = arg_model_name
        else:
            env["OPENAI_COMPAT_MODEL"] = arg_model_name
            env["DEEPSEEK_MODEL"] = arg_model_name
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
    return env


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
