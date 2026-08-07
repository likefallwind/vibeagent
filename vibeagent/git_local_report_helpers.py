from __future__ import annotations

from pathlib import Path

from .git_index_report_helpers import (
    format_git_index_report_text,
    format_git_index_text,
    git_index_observation_report,
    git_index_unexpected_report,
    git_index_usage_report,
)
from .git_read_commands import _indent_block, clip_with_flag


def validate_git_restore_max_diff_chars(max_diff_chars: int) -> None:
    if max_diff_chars < 100:
        raise ValueError("max_diff_chars must be at least 100.")
    if max_diff_chars > 200_000:
        raise ValueError("max_diff_chars must be at most 200000.")


def git_restore_usage_report(root: Path, usage: str, error: str, max_diff_chars: int) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "paths": {"shown": 0, "items": []},
        "statusText": "",
        "diff": {"text": "", "chars": 0, "truncated": False, "maxChars": max_diff_chars},
        "message": f"Usage: {usage}\nError: {error}",
    }


def git_restore_unexpected_report(root: Path, paths: list[str], message: str, max_diff_chars: int) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "paths": {"shown": len(paths), "items": list(paths)},
        "statusText": "",
        "diff": {"text": "", "chars": 0, "truncated": False, "maxChars": max_diff_chars},
        "message": message,
    }


def git_restore_observation_report(root: Path, observation: object, max_diff_chars: int) -> dict[str, object]:
    paths = list(getattr(observation, "paths"))
    diff = str(getattr(observation, "diff"))
    diff_text, diff_truncated = clip_with_flag(diff, max_diff_chars)
    return {
        "projectRoot": str(root),
        "ok": bool(getattr(observation, "ok")),
        "paths": {"shown": len(paths), "items": paths},
        "statusText": str(getattr(observation, "status")),
        "diff": {"text": diff_text, "chars": len(diff), "truncated": diff_truncated, "maxChars": max_diff_chars},
        "message": str(getattr(observation, "message")),
    }


def format_git_restore_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    paths = report.get("paths") if isinstance(report.get("paths"), dict) else {}
    items = paths.get("items") if isinstance(paths.get("items"), list) else []
    status = str(report.get("statusText") or "")
    diff = report.get("diff") if isinstance(report.get("diff"), dict) else {}
    diff_text = str(diff.get("text") or "")
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
    lines.append(f"  diffChars: {diff.get('chars', 0)}")
    lines.append(f"  diffTruncated: {'yes' if bool(diff.get('truncated')) else 'no'}")
    lines.append(f"  message: {message}")
    if diff_text:
        lines.append("")
        lines.append(diff_text)
    return "\n".join(lines)


def format_check_switch_text(
    root: Path,
    ok: bool,
    branch: str,
    create: bool,
    current_before: str,
    branch_exists: bool,
    worktree_clean: bool,
    status: str,
    message: str,
) -> str:
    lines = [
        "Check switch:",
        f"  projectRoot: {root}",
        f"  ok: {'yes' if ok else 'no'}",
        f"  branch: {branch}",
        f"  create: {'yes' if create else 'no'}",
        f"  currentBefore: {current_before or '.'}",
        f"  branchExists: {'yes' if branch_exists else 'no'}",
        f"  worktreeClean: {'yes' if worktree_clean else 'no'}",
    ]
    if status.strip():
        lines.append("  status:")
        lines.append(_indent_block(status.strip(), spaces=4))
    else:
        lines.append("  status: none")
    lines.append(f"  message: {message}")
    return "\n".join(lines)


def git_switch_usage_report(root: Path, usage: str, error: str) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "branch": "",
        "create": False,
        "currentBefore": "",
        "statusText": "",
        "message": f"Usage: {usage}\nError: {error}",
    }


def git_switch_unexpected_report(root: Path, branch: str, create: bool, message: str) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "branch": branch,
        "create": create,
        "currentBefore": "",
        "statusText": "",
        "message": message,
    }


def format_git_switch_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    status = str(report.get("statusText") or "")
    lines = [
        f"{title}:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  branch: {report.get('branch') or '.'}",
        f"  create: {'yes' if bool(report.get('create')) else 'no'}",
        f"  currentBefore: {report.get('currentBefore') or '.'}",
    ]
    if "branchExists" in report:
        lines.append(f"  branchExists: {'yes' if bool(report.get('branchExists')) else 'no'}")
    if "worktreeClean" in report:
        lines.append(f"  worktreeClean: {'yes' if bool(report.get('worktreeClean')) else 'no'}")
    if "currentAfter" in report:
        lines.append(f"  currentAfter: {report.get('currentAfter') or '.'}")
    if status.strip():
        lines.append("  status:")
        lines.append(_indent_block(status.strip(), spaces=4))
    else:
        lines.append("  status: none")
    lines.append(f"  message: {message}")
    return "\n".join(lines)


def format_switch_text(
    root: Path,
    ok: bool,
    branch: str,
    create: bool,
    current_before: str,
    current_after: str,
    status: str,
    message: str,
) -> str:
    lines = [
        "Switch:",
        f"  projectRoot: {root}",
        f"  ok: {'yes' if ok else 'no'}",
        f"  branch: {branch}",
        f"  create: {'yes' if create else 'no'}",
        f"  currentBefore: {current_before or '.'}",
        f"  currentAfter: {current_after or '.'}",
    ]
    if status.strip():
        lines.append("  status:")
        lines.append(_indent_block(status.strip(), spaces=4))
    else:
        lines.append("  status: none")
    lines.append(f"  message: {message}")
    return "\n".join(lines)


def format_git_restore_text(title: str, root: Path, ok: bool, paths: list[str], diff: str, status: str, message: str, max_diff_chars: int) -> str:
    validate_git_restore_max_diff_chars(max_diff_chars)
    diff_text, diff_truncated = clip_with_flag(diff, max_diff_chars)
    report = {
        "projectRoot": str(root),
        "ok": ok,
        "paths": {"shown": len(paths), "items": paths},
        "statusText": status,
        "diff": {"text": diff_text, "chars": len(diff), "truncated": diff_truncated, "maxChars": max_diff_chars},
        "message": message,
    }
    return format_git_restore_report_text(title, report)


def git_commit_usage_report(root: Path, usage: str, error: str) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "headBefore": "",
        "headAfter": "",
        "statusText": "",
        "message": f"Usage: {usage}\nError: {error}",
    }


def git_commit_unexpected_report(root: Path, message: str) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "headBefore": "",
        "headAfter": "",
        "statusText": "",
        "message": message,
    }


def git_commit_observation_report(root: Path, observation: object) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": bool(getattr(observation, "ok")),
        "headBefore": str(getattr(observation, "head_before")),
        "headAfter": str(getattr(observation, "head_after")),
        "statusText": str(getattr(observation, "status")),
        "message": str(getattr(observation, "message")),
    }


def format_git_commit_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    status = str(report.get("statusText") or "")
    lines = [
        f"{title}:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  headBefore: {report.get('headBefore') or '.'}",
        f"  headAfter: {report.get('headAfter') or '.'}",
    ]
    if status.strip():
        lines.append("  status:")
        lines.append(_indent_block(status.strip(), spaces=4))
    else:
        lines.append("  status: none")
    lines.append(f"  message: {message}")
    return "\n".join(lines)


def format_git_commit_text(title: str, root: Path, ok: bool, head_before: str, head_after: str, status: str, message: str) -> str:
    report = {
        "projectRoot": str(root),
        "ok": ok,
        "headBefore": head_before,
        "headAfter": head_after,
        "statusText": status,
        "message": message,
    }
    return format_git_commit_report_text(title, report)
