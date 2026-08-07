from __future__ import annotations

from pathlib import Path

from .git_read_commands import _indent_block


def git_index_usage_report(root: Path, usage: str, error: str) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "paths": {"shown": 0, "items": []},
        "statusText": "",
        "message": f"Usage: {usage}\nError: {error}",
    }


def git_index_unexpected_report(root: Path, paths: list[str], message: str) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "paths": {"shown": len(paths), "items": list(paths)},
        "statusText": "",
        "message": message,
    }


def git_index_observation_report(root: Path, observation: object) -> dict[str, object]:
    paths = list(getattr(observation, "paths"))
    return {
        "projectRoot": str(root),
        "ok": bool(getattr(observation, "ok")),
        "paths": {"shown": len(paths), "items": paths},
        "statusText": str(getattr(observation, "status")),
        "message": str(getattr(observation, "message")),
    }


def format_git_index_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    paths = report.get("paths") if isinstance(report.get("paths"), dict) else {}
    items = paths.get("items") if isinstance(paths.get("items"), list) else []
    status = str(report.get("statusText") or "")
    lines = [
        f"{title}:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  paths: {paths.get('shown', len(items))}",
    ]
    if items:
        lines.append("  pathList:")
        lines.extend(f"    - {path}" for path in items)
    else:
        lines.append("  pathList: none")
    if status.strip():
        lines.append("  status:")
        lines.append(_indent_block(status.strip(), spaces=4))
    else:
        lines.append("  status: none")
    lines.append(f"  message: {message}")
    return "\n".join(lines)


def format_git_index_text(title: str, root: Path, ok: bool, paths: list[str], status: str, message: str) -> str:
    report = {
        "projectRoot": str(root),
        "ok": ok,
        "paths": {"shown": len(paths), "items": paths},
        "statusText": status,
        "message": message,
    }
    return format_git_index_report_text(title, report)
