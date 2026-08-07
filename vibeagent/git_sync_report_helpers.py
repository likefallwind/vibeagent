from __future__ import annotations

from pathlib import Path

from .git_fetch_report_helpers import (
    format_git_fetch_preview_text,
    format_git_fetch_report_text,
    format_git_fetch_text,
    git_fetch_unexpected_report,
    git_fetch_usage_report,
)


def indent_block(value: str, spaces: int = 2) -> str:
    indent = " " * spaces
    return "\n".join(f"{indent}{line}" if line else "" for line in value.splitlines())


def git_sync_unexpected_report(root: Path, message: str) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "remote": "",
        "branch": "",
        "current": "",
        "upstream": "",
        "ahead": 0,
        "behind": 0,
        "worktreeClean": False,
        "statusText": "",
        "message": message,
    }


def git_sync_preview_observation_report(root: Path, observation: object) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": bool(getattr(observation, "ok")),
        "remote": str(getattr(observation, "remote")),
        "branch": str(getattr(observation, "branch")),
        "current": str(getattr(observation, "current")),
        "upstream": str(getattr(observation, "upstream")),
        "ahead": int(getattr(observation, "ahead")),
        "behind": int(getattr(observation, "behind")),
        "worktreeClean": bool(getattr(observation, "worktree_clean")),
        "statusText": str(getattr(observation, "status")),
        "message": str(getattr(observation, "message")),
    }


def format_git_pull_push_preview_text(
    title: str,
    root: Path,
    ok: bool,
    remote: str,
    branch: str,
    current: str,
    upstream: str,
    ahead: int,
    behind: int,
    worktree_clean: bool,
    status: str,
    message: str,
) -> str:
    lines = [
        f"{title}:",
        f"  projectRoot: {root}",
        f"  ok: {'yes' if ok else 'no'}",
        f"  remote: {remote or '.'}",
        f"  branch: {branch or '.'}",
        f"  current: {current or '.'}",
        f"  upstream: {upstream or '.'}",
        f"  ahead: {ahead}",
        f"  behind: {behind}",
        f"  worktreeClean: {'yes' if worktree_clean else 'no'}",
    ]
    if status.strip():
        lines.append("  status:")
        lines.append(indent_block(status.strip(), spaces=4))
    else:
        lines.append("  status: none")
    lines.append(f"  message: {message}")
    return "\n".join(lines)


def format_git_sync_preview_report_text(title: str, report: dict[str, object]) -> str:
    status = str(report.get("statusText") or "")
    lines = [
        f"{title}:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  remote: {report.get('remote') or '.'}",
        f"  branch: {report.get('branch') or '.'}",
        f"  current: {report.get('current') or '.'}",
        f"  upstream: {report.get('upstream') or '.'}",
        f"  ahead: {report.get('ahead', 0)}",
        f"  behind: {report.get('behind', 0)}",
        f"  worktreeClean: {'yes' if bool(report.get('worktreeClean')) else 'no'}",
    ]
    if status.strip():
        lines.append("  status:")
        lines.append(indent_block(status.strip(), spaces=4))
    else:
        lines.append("  status: none")
    lines.append(f"  message: {report.get('message') or ''}")
    return "\n".join(lines)


def format_git_pull_text(
    title: str,
    root: Path,
    ok: bool,
    remote: str,
    branch: str,
    current_before: str,
    current_after: str,
    upstream: str,
    ahead_before: int,
    behind_before: int,
    ahead_after: int,
    behind_after: int,
    status: str,
    message: str,
) -> str:
    lines = [
        f"{title}:",
        f"  projectRoot: {root}",
        f"  ok: {'yes' if ok else 'no'}",
        f"  remote: {remote or '.'}",
        f"  branch: {branch or '.'}",
        f"  currentBefore: {current_before or '.'}",
        f"  currentAfter: {current_after or '.'}",
        f"  upstream: {upstream or '.'}",
        f"  aheadBefore: {ahead_before}",
        f"  behindBefore: {behind_before}",
        f"  aheadAfter: {ahead_after}",
        f"  behindAfter: {behind_after}",
    ]
    if status.strip():
        lines.append("  status:")
        lines.append(indent_block(status.strip(), spaces=4))
    else:
        lines.append("  status: none")
    lines.append(f"  message: {message}")
    return "\n".join(lines)


def format_git_pull_report_text(title: str, report: dict[str, object]) -> str:
    status = str(report.get("statusText") or "")
    lines = [
        f"{title}:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  remote: {report.get('remote') or '.'}",
        f"  branch: {report.get('branch') or '.'}",
        f"  currentBefore: {report.get('currentBefore') or '.'}",
        f"  currentAfter: {report.get('currentAfter') or '.'}",
        f"  upstream: {report.get('upstream') or '.'}",
        f"  aheadBefore: {report.get('aheadBefore', 0)}",
        f"  behindBefore: {report.get('behindBefore', 0)}",
        f"  aheadAfter: {report.get('aheadAfter', 0)}",
        f"  behindAfter: {report.get('behindAfter', 0)}",
    ]
    if status.strip():
        lines.append("  status:")
        lines.append(indent_block(status.strip(), spaces=4))
    else:
        lines.append("  status: none")
    lines.append(f"  message: {report.get('message') or ''}")
    return "\n".join(lines)


def format_git_push_text(
    title: str,
    root: Path,
    ok: bool,
    remote: str,
    branch: str,
    current: str,
    upstream: str,
    ahead_before: int,
    behind_before: int,
    status: str,
    message: str,
) -> str:
    lines = [
        f"{title}:",
        f"  projectRoot: {root}",
        f"  ok: {'yes' if ok else 'no'}",
        f"  remote: {remote or '.'}",
        f"  branch: {branch or '.'}",
        f"  current: {current or '.'}",
        f"  upstream: {upstream or '.'}",
        f"  aheadBefore: {ahead_before}",
        f"  behindBefore: {behind_before}",
    ]
    if status.strip():
        lines.append("  status:")
        lines.append(indent_block(status.strip(), spaces=4))
    else:
        lines.append("  status: none")
    lines.append(f"  message: {message}")
    return "\n".join(lines)


def format_git_push_report_text(title: str, report: dict[str, object]) -> str:
    status = str(report.get("statusText") or "")
    lines = [
        f"{title}:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  remote: {report.get('remote') or '.'}",
        f"  branch: {report.get('branch') or '.'}",
        f"  current: {report.get('current') or '.'}",
        f"  upstream: {report.get('upstream') or '.'}",
        f"  aheadBefore: {report.get('aheadBefore', 0)}",
        f"  behindBefore: {report.get('behindBefore', 0)}",
    ]
    if status.strip():
        lines.append("  status:")
        lines.append(indent_block(status.strip(), spaces=4))
    else:
        lines.append("  status: none")
    lines.append(f"  message: {report.get('message') or ''}")
    return "\n".join(lines)
