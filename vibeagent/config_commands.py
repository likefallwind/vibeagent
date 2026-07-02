from __future__ import annotations

import os
from pathlib import Path

from .config import (
    load_project_config_env,
    project_config_path,
    resolve_cost_rates,
    resolve_execution_config,
    resolve_provider_config,
)


def get_model_text(env: dict[str, str | None] | None = None) -> str:
    return format_model_report_text(get_model_report(env))


def get_model_report(env: dict[str, str | None] | None = None) -> dict[str, object]:
    try:
        provider = resolve_provider_config(env)
    except ValueError as error:
        return {
            "ok": False,
            "provider": "",
            "model": "",
            "baseUrl": "",
            "apiKeyConfigured": False,
            "apiKeySource": "",
            "error": str(error),
            "message": str(error),
        }
    return {
        "ok": True,
        "provider": provider.provider,
        "model": provider.model,
        "baseUrl": provider.base_url,
        "apiKeyConfigured": bool(provider.api_key),
        "apiKeySource": provider.api_key_source or "",
        "error": "",
        "message": "Resolved model provider configuration.",
    }


def format_model_report_text(report: dict[str, object]) -> str:
    if not bool(report.get("ok")) and report.get("error"):
        return str(report.get("error"))
    api_key_text = f"configured via {report.get('apiKeySource')}" if report.get("apiKeySource") else "missing"
    return "\n".join(
        [
            f"Model provider: {report.get('provider') or '.'}",
            f"  model: {report.get('model') or '.'}",
            f"  baseUrl: {report.get('baseUrl') or '.'}",
            f"  apiKey: {api_key_text}",
        ]
    )


def get_config_text(
    project_root: str | Path = ".",
    env: dict[str, str | None] | None = None,
    *,
    max_iterations: int | None = None,
    command_timeout_ms: int | None = None,
    max_output_tokens: int | None = None,
    model_retries: int | None = None,
    model_retry_delay_ms: int | None = None,
    model_timeout_ms: int | None = None,
) -> str:
    return format_config_report_text(
        get_config_report(
            project_root,
            env,
            max_iterations=max_iterations,
            command_timeout_ms=command_timeout_ms,
            max_output_tokens=max_output_tokens,
            model_retries=model_retries,
            model_retry_delay_ms=model_retry_delay_ms,
            model_timeout_ms=model_timeout_ms,
        )
    )


def get_config_report(
    project_root: str | Path = ".",
    env: dict[str, str | None] | None = None,
    *,
    max_iterations: int | None = None,
    command_timeout_ms: int | None = None,
    max_output_tokens: int | None = None,
    model_retries: int | None = None,
    model_retry_delay_ms: int | None = None,
    model_timeout_ms: int | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    source_env, project_config_error = build_config_report_env(root, env)
    report: dict[str, object] = {
        "projectRoot": str(root),
        "projectConfig": project_config_path(root).is_file(),
        "projectConfigError": project_config_error or "",
        "provider": {
            "ok": False,
            "name": "",
            "model": "",
            "baseUrl": "",
            "apiKeyConfigured": False,
            "apiKeySource": "",
            "error": "",
        },
        "execution": {
            "ok": False,
            "maxIterations": None,
            "commandTimeoutMs": None,
            "maxOutputTokens": None,
            "modelRetries": None,
            "modelRetryDelayMs": None,
            "modelTimeoutMs": None,
            "error": "",
        },
        "costRates": {"ok": True, "configured": 0, "total": 4, "errors": []},
    }
    try:
        provider = resolve_provider_config(source_env)
        report["provider"] = {
            "ok": True,
            "name": provider.provider,
            "model": provider.model,
            "baseUrl": provider.base_url,
            "apiKeyConfigured": bool(provider.api_key),
            "apiKeySource": provider.api_key_source or "",
            "error": "",
        }
    except ValueError as error:
        report["provider"] = {
            "ok": False,
            "name": "",
            "model": "",
            "baseUrl": "",
            "apiKeyConfigured": False,
            "apiKeySource": "",
            "error": str(error),
        }

    try:
        execution = resolve_execution_config(
            root,
            max_iterations=max_iterations,
            command_timeout_ms=command_timeout_ms,
            max_output_tokens=max_output_tokens,
            model_retries=model_retries,
            model_retry_delay_ms=model_retry_delay_ms,
            model_timeout_ms=model_timeout_ms,
        )
        report["execution"] = {
            "ok": True,
            "maxIterations": execution.max_iterations,
            "commandTimeoutMs": execution.command_timeout_ms,
            "maxOutputTokens": execution.max_output_tokens,
            "modelRetries": execution.model_retries,
            "modelRetryDelayMs": execution.model_retry_delay_ms,
            "modelTimeoutMs": execution.model_timeout_ms,
            "error": "",
        }
    except ValueError as error:
        report["execution"] = {
            "ok": False,
            "maxIterations": None,
            "commandTimeoutMs": None,
            "maxOutputTokens": None,
            "modelRetries": None,
            "modelRetryDelayMs": None,
            "modelTimeoutMs": None,
            "error": str(error),
        }

    rates, cost_errors = resolve_cost_rates(source_env)
    configured_rates = sum(
        rate is not None
        for rate in (
            rates.input_usd_per_million,
            rates.output_usd_per_million,
            rates.cache_creation_usd_per_million,
            rates.cache_read_usd_per_million,
        )
    )
    report["costRates"] = {
        "ok": not cost_errors,
        "configured": configured_rates,
        "total": 4,
        "errors": list(cost_errors),
    }
    return report


def build_config_report_env(root: Path, env: dict[str, str | None] | None) -> tuple[dict[str, str | None], str | None]:
    if env is not None:
        return dict(env), None
    source_env: dict[str, str | None] = dict(os.environ)
    try:
        project_env = load_project_config_env(root)
    except ValueError as error:
        return source_env, str(error)
    for key, value in project_env.items():
        if not source_env.get(key):
            source_env[key] = value
    return source_env, None


def format_config_report_text(report: dict[str, object]) -> str:
    provider = report.get("provider") if isinstance(report.get("provider"), dict) else {}
    execution = report.get("execution") if isinstance(report.get("execution"), dict) else {}
    cost_rates = report.get("costRates") if isinstance(report.get("costRates"), dict) else {}
    lines = [
        "Config:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  projectConfig: {'yes' if bool(report.get('projectConfig')) else 'no'}",
    ]
    if report.get("projectConfigError"):
        lines.append(f"  projectConfigError: {report.get('projectConfigError')}")
    if provider.get("ok"):
        key_text = f"configured via {provider.get('apiKeySource')}" if provider.get("apiKeySource") else "missing"
        lines.extend(
            [
                f"  provider: {provider.get('name')}",
                f"  model: {provider.get('model')}",
                f"  baseUrl: {provider.get('baseUrl')}",
                f"  apiKey: {key_text}",
            ]
        )
    else:
        lines.append(f"  provider: {provider.get('error') or 'unresolved'}")
    if execution.get("ok"):
        lines.extend(
            [
                f"  maxIterations: {execution.get('maxIterations')}",
                f"  commandTimeoutMs: {execution.get('commandTimeoutMs')}",
                f"  maxOutputTokens: {execution.get('maxOutputTokens')}",
                f"  modelRetries: {execution.get('modelRetries')}",
                f"  modelRetryDelayMs: {execution.get('modelRetryDelayMs')}",
                f"  modelTimeoutMs: {execution.get('modelTimeoutMs')}",
            ]
        )
    else:
        lines.append(f"  execution: {execution.get('error') or 'unresolved'}")
    errors = cost_rates.get("errors") if isinstance(cost_rates.get("errors"), list) else []
    if not bool(cost_rates.get("ok")):
        lines.append("  costRates: invalid")
        lines.extend(f"    - {error}" for error in errors)
    else:
        lines.append(f"  costRates: {cost_rates.get('configured', 0)}/{cost_rates.get('total', 4)} configured")
    return "\n".join(lines)
