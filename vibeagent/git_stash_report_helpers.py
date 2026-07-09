from __future__ import annotations

from pathlib import Path

from .git_read_commands import _indent_block, clip_with_flag


def format_git_stash_text(
    title: str,
    root: Path,
    ok: bool,
    message_text: str,
    include_untracked: bool,
    stash_ref: str,
    status: str,
    diff: str,
    message: str,
    max_diff_chars: int,
) -> str:
    _validate_git_stash_max_chars(max_diff_chars)
    diff_text, diff_truncated = clip_with_flag(diff, max_diff_chars)
    report = {
        "projectRoot": str(root),
        "ok": ok,
        "messageText": message_text,
        "includeUntracked": include_untracked,
        "stashRef": stash_ref,
        "statusText": status,
        "diff": {"text": diff_text, "chars": len(diff), "truncated": diff_truncated, "maxChars": max_diff_chars},
        "message": message,
    }
    return format_git_stash_report_text(title, report)


def _validate_git_stash_max_chars(max_chars: int) -> None:
    if max_chars < 100:
        raise ValueError("max_chars must be at least 100.")
    if max_chars > 200_000:
        raise ValueError("max_chars must be at most 200000.")


def _empty_clip_report(max_chars: int) -> dict[str, object]:
    return {"text": "", "chars": 0, "truncated": False, "maxChars": max_chars}


def _clip_report(value: str, max_chars: int) -> dict[str, object]:
    text, truncated = clip_with_flag(value, max_chars)
    return {"text": text, "chars": len(value), "truncated": truncated, "maxChars": max_chars}


def format_git_stash_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    diff = report.get("diff") if isinstance(report.get("diff"), dict) else {}
    diff_text = str(diff.get("text") or "")
    status = str(report.get("statusText") or "")
    lines = [
        f"{title}:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  messageText: {report.get('messageText') or '.'}",
        f"  includeUntracked: {'yes' if bool(report.get('includeUntracked')) else 'no'}",
    ]
    if report.get("stashRef"):
        lines.append(f"  stashRef: {report.get('stashRef')}")
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


def format_git_stash_apply_text(
    title: str,
    root: Path,
    ok: bool,
    stash_ref: str,
    worktree_clean: bool | None,
    patch: str,
    status: str,
    message: str,
    max_patch_chars: int,
) -> str:
    _validate_git_stash_max_chars(max_patch_chars)
    patch_text, patch_truncated = clip_with_flag(patch, max_patch_chars)
    report: dict[str, object] = {
        "projectRoot": str(root),
        "ok": ok,
        "stashRef": stash_ref,
        "patch": {"text": patch_text, "chars": len(patch), "truncated": patch_truncated, "maxChars": max_patch_chars},
        "statusText": status,
        "message": message,
    }
    if worktree_clean is not None:
        report["worktreeClean"] = worktree_clean
    return format_git_stash_apply_report_text(title, report)


def format_git_stash_apply_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    patch = report.get("patch") if isinstance(report.get("patch"), dict) else {}
    patch_text = str(patch.get("text") or "")
    status = str(report.get("statusText") or "")
    lines = [
        f"{title}:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  stashRef: {report.get('stashRef') or '.'}",
    ]
    if "worktreeClean" in report:
        lines.append(f"  worktreeClean: {'yes' if bool(report.get('worktreeClean')) else 'no'}")
    if status.strip():
        lines.append("  status:")
        lines.append(_indent_block(status.strip(), spaces=4))
    else:
        lines.append("  status: none")
    lines.append(f"  patchChars: {patch.get('chars', 0)}")
    lines.append(f"  patchTruncated: {'yes' if bool(patch.get('truncated')) else 'no'}")
    lines.append(f"  message: {message}")
    if patch_text:
        lines.append("")
        lines.append(patch_text)
    return "\n".join(lines)


def format_git_stash_drop_text(
    title: str,
    root: Path,
    ok: bool,
    stash_ref: str,
    summary: str,
    patch: str,
    remaining_total: int | None,
    message: str,
    max_patch_chars: int,
) -> str:
    _validate_git_stash_max_chars(max_patch_chars)
    patch_text, patch_truncated = clip_with_flag(patch, max_patch_chars)
    report: dict[str, object] = {
        "projectRoot": str(root),
        "ok": ok,
        "stashRef": stash_ref,
        "summary": summary,
        "patch": {"text": patch_text, "chars": len(patch), "truncated": patch_truncated, "maxChars": max_patch_chars},
        "message": message,
    }
    if remaining_total is not None:
        report["remainingTotal"] = remaining_total
    return format_git_stash_drop_report_text(title, report)


def format_git_stash_drop_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    patch = report.get("patch") if isinstance(report.get("patch"), dict) else {}
    patch_text = str(patch.get("text") or "")
    lines = [
        f"{title}:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  stashRef: {report.get('stashRef') or '.'}",
        f"  summary: {report.get('summary') or '.'}",
    ]
    if "remainingTotal" in report:
        lines.append(f"  remainingTotal: {report.get('remainingTotal')}")
    lines.append(f"  patchChars: {patch.get('chars', 0)}")
    lines.append(f"  patchTruncated: {'yes' if bool(patch.get('truncated')) else 'no'}")
    lines.append(f"  message: {message}")
    if patch_text:
        lines.append("")
        lines.append(patch_text)
    return "\n".join(lines)
