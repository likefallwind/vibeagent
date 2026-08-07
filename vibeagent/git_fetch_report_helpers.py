from __future__ import annotations

from pathlib import Path


def git_fetch_usage_report(root: Path, usage: str, error: str) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "remote": "",
        "remoteUrl": "",
        "branch": "",
        "upstream": "",
        "ahead": 0,
        "behind": 0,
        "message": f"Usage: {usage}\nError: {error}",
    }


def git_fetch_unexpected_report(root: Path, message: str) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "remote": "",
        "remoteUrl": "",
        "branch": "",
        "upstream": "",
        "message": message,
    }


def format_git_fetch_preview_text(
    title: str,
    root: Path,
    ok: bool,
    remote: str,
    remote_url: str,
    branch: str,
    upstream: str,
    ahead: int,
    behind: int,
    message: str,
) -> str:
    return "\n".join(
        [
            f"{title}:",
            f"  projectRoot: {root}",
            f"  ok: {'yes' if ok else 'no'}",
            f"  remote: {remote or '.'}",
            f"  remoteUrl: {remote_url or '.'}",
            f"  branch: {branch or '.'}",
            f"  upstream: {upstream or '.'}",
            f"  ahead: {ahead}",
            f"  behind: {behind}",
            f"  message: {message}",
        ]
    )


def format_git_fetch_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    lines = [
        f"{title}:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  remote: {report.get('remote') or '.'}",
        f"  remoteUrl: {report.get('remoteUrl') or '.'}",
        f"  branch: {report.get('branch') or '.'}",
        f"  upstream: {report.get('upstream') or '.'}",
    ]
    if "aheadBefore" in report or "behindBefore" in report:
        lines.extend(
            [
                f"  aheadBefore: {report.get('aheadBefore', 0)}",
                f"  behindBefore: {report.get('behindBefore', 0)}",
                f"  aheadAfter: {report.get('aheadAfter', 0)}",
                f"  behindAfter: {report.get('behindAfter', 0)}",
            ]
        )
    else:
        lines.extend(
            [
                f"  ahead: {report.get('ahead', 0)}",
                f"  behind: {report.get('behind', 0)}",
            ]
        )
    lines.append(f"  message: {message}")
    return "\n".join(lines)


def format_git_fetch_text(
    title: str,
    root: Path,
    ok: bool,
    remote: str,
    remote_url: str,
    branch: str,
    upstream: str,
    ahead_before: int,
    behind_before: int,
    ahead_after: int,
    behind_after: int,
    message: str,
) -> str:
    return "\n".join(
        [
            f"{title}:",
            f"  projectRoot: {root}",
            f"  ok: {'yes' if ok else 'no'}",
            f"  remote: {remote or '.'}",
            f"  remoteUrl: {remote_url or '.'}",
            f"  branch: {branch or '.'}",
            f"  upstream: {upstream or '.'}",
            f"  aheadBefore: {ahead_before}",
            f"  behindBefore: {behind_before}",
            f"  aheadAfter: {ahead_after}",
            f"  behindAfter: {behind_after}",
            f"  message: {message}",
        ]
    )
