from __future__ import annotations

from pathlib import Path

from .check_suggested_commands import (
    format_check_suggested_checks_report_text,
    format_run_suggested_checks_report_text,
    get_check_suggested_checks_report,
    get_check_suggested_checks_text,
    get_run_suggested_checks_report,
    get_run_suggested_checks_text,
)
from .workspace_core import create_local_workspace
from .workspace import suggest_project_checks
from .workflow_commands import format_review_check


def get_checks_report(project_root: str | Path = ".", max_checks: int = 20) -> dict[str, object]:
    if max_checks < 1:
        raise ValueError("max_checks must be at least 1.")
    if max_checks > 100:
        raise ValueError("max_checks must be at most 100.")
    root = Path(project_root).resolve()
    workspace = create_local_workspace(root, "local-checks")
    suggestions = suggest_project_checks(workspace, max_commands=max_checks)
    checks = [item for item in suggestions["checks"] if isinstance(item, dict)]
    changed_files = [item for item in suggestions["changed_files"] if isinstance(item, str)]
    return {
        "projectRoot": str(root),
        "suggestedChecks": {
            "shown": len(checks),
            "total": suggestions["total"],
            "truncated": bool(suggestions["truncated"]),
            "commands": checks,
        },
        "changedFiles": changed_files,
        "message": suggestions["message"],
    }


def get_checks_text(project_root: str | Path = ".", max_checks: int = 20) -> str:
    return format_checks_report_text(get_checks_report(project_root, max_checks=max_checks))


def format_checks_report_text(report: dict[str, object]) -> str:
    suggested = report.get("suggestedChecks") if isinstance(report.get("suggestedChecks"), dict) else {}
    checks = suggested.get("commands") if isinstance(suggested.get("commands"), list) else []
    changed_files = report.get("changedFiles") if isinstance(report.get("changedFiles"), list) else []
    lines = [
        "Checks:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  suggestedChecks: {int(suggested.get('shown', 0) or 0)}/{int(suggested.get('total', 0) or 0)}",
        f"  changedFiles: {len(changed_files)}",
        f"  truncated: {'yes' if bool(suggested.get('truncated')) else 'no'}",
    ]
    if checks:
        lines.append("  commands:")
        lines.extend(format_review_check(item) for item in checks)
    else:
        lines.append("  commands: none")
    lines.append(f"  message: {report.get('message') or ''}")
    return "\n".join(lines)
