from __future__ import annotations

from pathlib import Path
import shutil
import sys

from . import __version__
from .command_hard_blocks import get_command_hard_block_report
from .config import resolve_cost_rates, resolve_provider_config
from .doctor_memory_limits import get_memory_limits_doctor_report


def get_doctor_report(project_root: str | Path = ".", env: dict[str, str | None] | None = None) -> dict[str, object]:
    root = Path(project_root).resolve()
    report: dict[str, object] = {
        "version": __version__,
        "projectRoot": str(root),
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "sessionsDir": (root / ".vibeagent" / "sessions").exists(),
        "projectConfig": (root / ".vibeagent" / "config.json").exists(),
        "gitRepo": (root / ".git").exists(),
        "agentsMd": (root / "AGENTS.md").exists(),
        "claudeMd": (root / "CLAUDE.md").exists(),
    }
    try:
        config = resolve_provider_config(env)
        report["provider"] = {
            "ok": True,
            "name": config.provider,
            "model": config.model,
            "baseUrl": config.base_url,
            "apiKeySource": config.api_key_source,
        }
    except ValueError as error:
        report["provider"] = {"ok": False, "error": str(error)}

    rates, cost_errors = resolve_cost_rates(env)
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
        "errors": cost_errors,
    }
    report["executables"] = {
        name: shutil.which(name) is not None
        for name in ("python3", "git", "npm")
    }
    report["memoryLimits"] = get_memory_limits_doctor_report(env)
    report["commandHardBlocks"] = get_command_hard_block_report()
    return report


def get_doctor_text(project_root: str | Path = ".", env: dict[str, str | None] | None = None) -> str:
    return format_doctor_report_text(get_doctor_report(project_root, env))


def format_doctor_report_text(report: dict[str, object]) -> str:
    lines = [
        "Doctor:",
        f"  version: {report.get('version') or ''}",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  python: {report.get('python') or ''}",
        f"  sessionsDir: {'yes' if bool(report.get('sessionsDir')) else 'no'}",
        f"  projectConfig: {'yes' if bool(report.get('projectConfig')) else 'no'}",
        f"  gitRepo: {'yes' if bool(report.get('gitRepo')) else 'no'}",
        f"  agentsMd: {'yes' if bool(report.get('agentsMd')) else 'no'}",
        f"  claudeMd: {'yes' if bool(report.get('claudeMd')) else 'no'}",
    ]
    provider = report.get("provider")
    if isinstance(provider, dict) and provider.get("ok"):
        key_source = provider.get("apiKeySource")
        key_text = f"configured via {key_source}" if key_source else "missing"
        lines.extend(
            [
                f"  provider: {provider.get('name')}",
                f"  model: {provider.get('model')}",
                f"  baseUrl: {provider.get('baseUrl')}",
                f"  apiKey: {key_text}",
            ]
        )
    elif isinstance(provider, dict):
        lines.append(f"  provider: {provider.get('error')}")

    cost_rates = report.get("costRates")
    if isinstance(cost_rates, dict) and not bool(cost_rates.get("ok")):
        lines.append("  costRates: invalid")
        lines.extend(f"    - {error}" for error in cost_rates.get("errors", []))
    elif isinstance(cost_rates, dict):
        lines.append(f"  costRates: {cost_rates.get('configured')}/{cost_rates.get('total')} configured")

    memory_limits = report.get("memoryLimits")
    if isinstance(memory_limits, dict):
        lines.append(f"  memoryLimits: {memory_limits.get('status') or 'unknown'}")
        support = memory_limits.get("support")
        if isinstance(support, dict):
            support_status = "ready" if bool(support.get("ready")) else "unavailable"
            lines.append(f"    support: {support_status}")
            lines.append(f"      - platform: {support.get('platform') or 'unknown'}")
            lines.append(
                f"      - systemd-run: {'available' if bool(support.get('systemdRun')) else 'missing'}"
            )
            lines.append(
                f"      - systemctl: {'available' if bool(support.get('systemctl')) else 'missing'}"
            )
            lines.append(
                f"      - userManager: {'reachable' if bool(support.get('userManager')) else 'unavailable'}"
            )
            if support.get("error"):
                lines.append(f"      - error: {support.get('error')}")
        for key, label in (("toolCommands", "toolCommands"), ("backgroundAgents", "backgroundAgents")):
            limit = memory_limits.get(key)
            if not isinstance(limit, dict):
                continue
            if not bool(limit.get("configured")):
                value = "not configured"
            elif not bool(limit.get("valid")):
                value = f"invalid: {limit.get('error') or 'invalid value'}"
            elif not bool(limit.get("enabled")):
                value = "disabled"
            else:
                value = str(limit.get("limit") or limit.get("limitBytes") or "configured")
            lines.append(f"    {label}: {value} ({limit.get('environment')})")

    lines.append("  executables:")
    executables = report.get("executables")
    if isinstance(executables, dict):
        for name in ("python3", "git", "npm"):
            lines.append(f"    - {name}: {'available' if bool(executables.get(name)) else 'missing'}")
    hard_blocks = report.get("commandHardBlocks")
    if isinstance(hard_blocks, dict):
        lines.append(f"  commandHardBlocks: {hard_blocks.get('active')}/{hard_blocks.get('total')} active")
        for check in hard_blocks.get("checks", []):
            if not isinstance(check, dict):
                continue
            status = "active" if bool(check.get("active")) else "missing"
            reason = str(check.get("reason") or "")
            detail = f": {reason}" if reason else ""
            lines.append(f"    - {check.get('command')}: {status}{detail}")
    return "\n".join(lines)
