from __future__ import annotations

from pathlib import Path

from .project_trust import is_project_permissions_trusted
from .workspace_core import RunWorkspace
from .workspace_sandbox import read_workspace_sandbox


def get_sandbox_report(root: str | Path = ".") -> dict[str, object]:
    project_root = Path(root).resolve()
    workspace = RunWorkspace(
        root=project_root,
        run_id="",
        session_dir=project_root / ".vibeagent/sessions",
        project_config_trusted=is_project_permissions_trusted(project_root),
    )
    config = read_workspace_sandbox(workspace)
    return {
        "ok": config.error is None and (not config.enabled or config.active or not config.fail_if_unavailable),
        "enabled": config.enabled,
        "active": config.active,
        "available": config.available,
        "networkDisabled": config.network_disabled,
        "networkIsolationAvailable": config.network_available,
        "failIfUnavailable": config.fail_if_unavailable,
        "autoAllowBashIfSandboxed": config.auto_allow_bash_if_sandboxed,
        "autoApprovalReady": (
            config.active
            and config.auto_allow_bash_if_sandboxed
            and config.network_disabled
            and config.network_available
        ),
        "bwrapPath": config.bwrap_path,
        "sources": list(config.sources),
        "filesystem": {
            "allowWrite": [path.as_posix() for path in config.allow_write],
            "denyWrite": [path.as_posix() for path in config.deny_write],
            "denyRead": [path.as_posix() for path in config.deny_read],
        },
        "excludedCommands": list(config.excluded_commands),
        "error": config.error,
        "message": _sandbox_message(config.enabled, config.active, config.available, config.error),
    }


def get_sandbox_text(root: str | Path = ".") -> str:
    return format_sandbox_report_text(get_sandbox_report(root))


def format_sandbox_report_text(report: dict[str, object]) -> str:
    lines = [
        "Command sandbox:",
        f"  enabled: {'yes' if report.get('enabled') else 'no'}",
        f"  active: {'yes' if report.get('active') else 'no'}",
        f"  bubblewrap: {report.get('bwrapPath') or '(unavailable)'}",
        f"  failIfUnavailable: {'yes' if report.get('failIfUnavailable') else 'no'}",
        f"  autoAllowBashIfSandboxed: {'yes' if report.get('autoAllowBashIfSandboxed') else 'no'}",
        f"  autoApprovalReady: {'yes' if report.get('autoApprovalReady') else 'no'}",
        f"  networkDisabled: {'yes' if report.get('networkDisabled') else 'no'}",
        f"  networkIsolationAvailable: {'yes' if report.get('networkIsolationAvailable') else 'no'}",
        f"  sources: {', '.join(str(item) for item in report.get('sources', [])) or '(none)'}",
    ]
    filesystem = report.get("filesystem")
    if isinstance(filesystem, dict):
        for field in ("allowWrite", "denyWrite", "denyRead"):
            values = filesystem.get(field)
            if isinstance(values, list) and values:
                lines.append(f"  {field}:")
                lines.extend(f"    - {value}" for value in values)
    excluded = report.get("excludedCommands")
    if isinstance(excluded, list) and excluded:
        lines.append("  excludedCommands:")
        lines.extend(f"    - {value}" for value in excluded)
    error = report.get("error")
    if isinstance(error, str) and error:
        lines.append(f"  error: {error}")
    lines.append(f"  message: {report.get('message')}")
    return "\n".join(lines)


def _sandbox_message(enabled: bool, active: bool, available: bool, error: str | None) -> str:
    if error:
        return f"Sandbox configuration is invalid: {error}"
    if not enabled:
        return "Command sandbox is disabled."
    if active:
        return "Command sandbox is active."
    if not available:
        return "Command sandbox is enabled but Bubblewrap is unavailable."
    return "Command sandbox is enabled but inactive."
