from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import Mapping

from .background_agent_memory import (
    BACKGROUND_AGENT_MEMORY_LIMIT_ENV,
    resolve_background_agent_memory_limit,
)
from .tool_memory_limit import (
    TOOL_MEMORY_LIMIT_ENV,
    ToolMemoryLimitError,
    format_memory_bytes,
    parse_tool_memory_limit,
)


SYSTEMD_CHECK_TIMEOUT_SECONDS = 2.0


def get_memory_limits_doctor_report(
    environment: Mapping[str, str | None] | None = None,
) -> dict[str, object]:
    values = os.environ if environment is None else environment
    support = _get_systemd_support_report(values)
    tool_commands = _get_limit_report(values, TOOL_MEMORY_LIMIT_ENV, background=False)
    background_agents = _get_limit_report(
        values,
        BACKGROUND_AGENT_MEMORY_LIMIT_ENV,
        background=True,
    )
    limits = (tool_commands, background_agents)
    configured = any(bool(limit["configured"]) for limit in limits)
    enabled = any(bool(limit["enabled"]) for limit in limits)
    valid = all(bool(limit["valid"]) for limit in limits)

    if not valid:
        status = "invalid"
    elif enabled and not bool(support["ready"]):
        status = "unavailable"
    elif enabled:
        status = "ready"
    elif configured:
        status = "disabled"
    else:
        status = "not configured"

    return {
        "ok": status not in {"invalid", "unavailable"},
        "status": status,
        "support": support,
        "toolCommands": tool_commands,
        "backgroundAgents": background_agents,
    }


def _get_limit_report(
    environment: Mapping[str, str | None],
    variable: str,
    *,
    background: bool,
) -> dict[str, object]:
    configured = variable in environment and environment.get(variable) is not None
    report: dict[str, object] = {
        "environment": variable,
        "configured": configured,
        "enabled": False,
        "valid": True,
        "limitBytes": None,
        "limit": None,
    }
    if not configured:
        return report

    string_environment = _string_environment(environment)
    try:
        if background:
            limit = resolve_background_agent_memory_limit(None, string_environment)
        else:
            limit = parse_tool_memory_limit(string_environment)
    except ToolMemoryLimitError as error:
        report["valid"] = False
        report["error"] = str(error)
        return report

    if limit is not None:
        report["enabled"] = True
        report["limitBytes"] = limit
        report["limit"] = format_memory_bytes(limit)
    return report


def _get_systemd_support_report(
    environment: Mapping[str, str | None],
) -> dict[str, object]:
    linux = sys.platform.startswith("linux")
    path = environment.get("PATH")
    search_path = path if isinstance(path, str) else None
    systemd_run = shutil.which("systemd-run", path=search_path)
    systemctl = shutil.which("systemctl", path=search_path)
    report: dict[str, object] = {
        "ready": False,
        "platform": sys.platform,
        "linux": linux,
        "systemdRun": systemd_run is not None,
        "systemctl": systemctl is not None,
        "userManager": False,
    }
    if not linux:
        report["error"] = "Memory limits require Linux or WSL."
        return report
    if systemd_run is None or systemctl is None:
        report["error"] = "systemd-run and systemctl must be available on PATH."
        return report

    try:
        completed = subprocess.run(
            [systemctl, "--user", "show-environment"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=SYSTEMD_CHECK_TIMEOUT_SECONDS,
            env=_runtime_environment(environment),
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        report["error"] = _bounded_error(error)
        return report
    if completed.returncode != 0:
        report["error"] = _bounded_error(completed.stderr or "User systemd manager is unavailable.")
        return report

    report["ready"] = True
    report["userManager"] = True
    return report


def _string_environment(environment: Mapping[str, str | None]) -> dict[str, str]:
    return {key: value for key, value in environment.items() if isinstance(value, str)}


def _runtime_environment(environment: Mapping[str, str | None]) -> dict[str, str]:
    runtime = dict(os.environ)
    for key, value in environment.items():
        if isinstance(value, str):
            runtime[key] = value
        elif value is None:
            runtime.pop(key, None)
    return runtime


def _bounded_error(error: object) -> str:
    text = " ".join(str(error).split())
    return (text or "User systemd manager is unavailable.")[:240]


__all__ = ["SYSTEMD_CHECK_TIMEOUT_SECONDS", "get_memory_limits_doctor_report"]
