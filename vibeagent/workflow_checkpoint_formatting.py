from __future__ import annotations

from .workflow_checkpoint_utils import short_head
from .workflow_review_formatting import clip_text, indent_block


def format_checkpoint_create_report_text(report: dict[str, object]) -> str:
    checkpoint = report.get("checkpoint")
    if not bool(report.get("ok")) or not isinstance(checkpoint, dict):
        return "\n".join(
            [
                "Checkpoint:",
                f"  projectRoot: {report.get('projectRoot') or '.'}",
                "  created: no",
                f"  message: {report.get('message')}",
            ]
        )
    lines = [
        "Checkpoint:",
        "  created: yes",
        f"  id: {checkpoint.get('id')}",
        f"  label: {checkpoint.get('label') or ''}",
        f"  projectRoot: {report.get('projectRoot') or checkpoint.get('projectRoot')}",
        f"  head: {checkpoint.get('shortHead') or short_head(str(checkpoint.get('head') or ''))}",
        f"  changedFiles: {checkpoint.get('changedFiles', 0)}",
        f"  stagedFiles: {checkpoint.get('stagedFiles', 0)}",
        f"  unstagedFiles: {checkpoint.get('unstagedFiles', 0)}",
        f"  untrackedFiles: {checkpoint.get('untrackedFiles', 0)}",
        f"  unstagedPatchChars: {checkpoint.get('unstagedPatchChars', 0)}",
        f"  stagedPatchChars: {checkpoint.get('stagedPatchChars', 0)}",
        f"  message: {report.get('message')}",
    ]
    return "\n".join(lines)


def format_checkpoints_report_text(report: dict[str, object]) -> str:
    checkpoints = report.get("checkpoints")
    items = checkpoints if isinstance(checkpoints, list) else []
    lines = [
        "Checkpoints:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  total: {report.get('total', 0)}",
    ]
    if items:
        lines.append("  items:")
        for metadata in items:
            if not isinstance(metadata, dict):
                continue
            label = str(metadata.get("label") or "")
            label_text = f" label={label}" if label else ""
            lines.append(
                "    - "
                f"{metadata.get('id')} created={metadata.get('createdAt')}"
                f"{label_text} changedFiles={metadata.get('changedFiles', 0)}"
                f" staged={metadata.get('stagedFiles', 0)}"
                f" unstaged={metadata.get('unstagedFiles', 0)}"
                f" untracked={metadata.get('untrackedFiles', 0)}"
            )
    else:
        lines.append("  items: none")
    return "\n".join(lines)


def format_checkpoint_show_report_text(report: dict[str, object]) -> str:
    checkpoint = report.get("checkpoint")
    if not bool(report.get("ok")) or not isinstance(checkpoint, dict):
        return str(report.get("message") or "Checkpoint not found.")
    patches = report.get("patches") if isinstance(report.get("patches"), dict) else {}
    paths = report.get("savedUntrackedPaths") if isinstance(report.get("savedUntrackedPaths"), dict) else {}
    shown_paths = paths.get("shown", []) if isinstance(paths, dict) else []
    lines = [
        "Checkpoint:",
        f"  id: {checkpoint.get('id')}",
        f"  label: {checkpoint.get('label') or ''}",
        f"  createdAt: {checkpoint.get('createdAt')}",
        f"  projectRoot: {checkpoint.get('projectRoot') or report.get('projectRoot')}",
        f"  head: {checkpoint.get('shortHead') or short_head(str(checkpoint.get('head') or ''))}",
        f"  changedFiles: {checkpoint.get('changedFiles', 0)}",
        f"  stagedFiles: {checkpoint.get('stagedFiles', 0)}",
        f"  unstagedFiles: {checkpoint.get('unstagedFiles', 0)}",
        f"  untrackedFiles: {checkpoint.get('untrackedFiles', 0)}",
        f"  untrackedSavedFiles: {checkpoint.get('untrackedSavedFiles', 0)}",
        f"  untrackedSkippedFiles: {checkpoint.get('untrackedSkippedFiles', 0)}",
        f"  unstagedPatch: {patches.get('unstagedPath')} ({patches.get('unstagedChars', 0)} chars)",
        f"  stagedPatch: {patches.get('stagedPath')} ({patches.get('stagedChars', 0)} chars)",
    ]
    if shown_paths:
        lines.append("  savedUntrackedPaths:")
        for path in shown_paths:
            lines.append(f"    - {path}")
        if bool(paths.get("truncated")):
            lines.append("    - ...")
    else:
        lines.append("  savedUntrackedPaths: none")
    status = str(report.get("gitStatus") or "")
    if status.strip():
        lines.append("  gitStatus:")
        lines.append(indent_block(clip_text(status, 4_000), spaces=4))
    else:
        lines.append("  gitStatus: clean")
    return "\n".join(lines)


def format_checkpoint_diff_report_text(report: dict[str, object]) -> str:
    checkpoint = report.get("checkpoint")
    diff = report.get("diff") if isinstance(report.get("diff"), dict) else {}
    if not bool(report.get("ok")) or not isinstance(checkpoint, dict):
        return str(report.get("message") or "Checkpoint not found.")
    staged_text = str(diff.get("stagedPatch") or "")
    unstaged_text = str(diff.get("unstagedPatch") or "")
    lines = [
        "Checkpoint diff:",
        f"  id: {checkpoint.get('id')}",
        f"  label: {checkpoint.get('label') or ''}",
        f"  createdAt: {checkpoint.get('createdAt')}",
        f"  stagedChars: {diff.get('stagedChars', 0)}",
        f"  stagedTruncated: {'yes' if bool(diff.get('stagedTruncated')) else 'no'}",
        f"  unstagedChars: {diff.get('unstagedChars', 0)}",
        f"  unstagedTruncated: {'yes' if bool(diff.get('unstagedTruncated')) else 'no'}",
        "",
        "Staged patch:",
        staged_text if staged_text else "no staged changes",
        "",
        "Unstaged patch:",
        unstaged_text if unstaged_text else "no unstaged changes",
    ]
    return "\n".join(lines)


def format_checkpoint_status_report_text(report: dict[str, object]) -> str:
    checkpoint = report.get("checkpoint")
    if not isinstance(checkpoint, dict):
        return str(report.get("message") or "Checkpoint not found.")
    checks = report.get("checks") if isinstance(report.get("checks"), dict) else {}
    saved = report.get("saved") if isinstance(report.get("saved"), dict) else {}
    current = report.get("current") if isinstance(report.get("current"), dict) else {}
    lines = [
        "Checkpoint status:",
        f"  id: {checkpoint.get('id')}",
        f"  label: {checkpoint.get('label') or ''}",
        f"  createdAt: {checkpoint.get('createdAt')}",
        f"  matches: {'yes' if bool(report.get('matches')) else 'no'}",
        f"  statusMatches: {'yes' if bool(checks.get('statusMatches')) else 'no'}",
        f"  stagedPatchMatches: {'yes' if bool(checks.get('stagedPatchMatches')) else 'no'}",
        f"  unstagedPatchMatches: {'yes' if bool(checks.get('unstagedPatchMatches')) else 'no'}",
        f"  untrackedFileMatches: {'yes' if bool(checks.get('untrackedFileMatches')) else 'no'}",
    ]
    if saved:
        lines.extend(
            [
                "  saved:",
                f"    changedFiles: {saved.get('changedFiles', 0)}",
                f"    stagedFiles: {saved.get('stagedFiles', 0)}",
                f"    unstagedFiles: {saved.get('unstagedFiles', 0)}",
                f"    untrackedFiles: {saved.get('untrackedFiles', 0)}",
                f"    stagedPatchChars: {saved.get('stagedPatchChars', 0)}",
                f"    unstagedPatchChars: {saved.get('unstagedPatchChars', 0)}",
                "  current:",
                f"    changedFiles: {current.get('changedFiles', 0)}",
                f"    stagedFiles: {current.get('stagedFiles', 0)}",
                f"    unstagedFiles: {current.get('unstagedFiles', 0)}",
                f"    untrackedFiles: {current.get('untrackedFiles', 0)}",
                f"    stagedPatchChars: {current.get('stagedPatchChars', 0)}",
                f"    unstagedPatchChars: {current.get('unstagedPatchChars', 0)}",
            ]
        )
    lines.append(f"  message: {report.get('message')}")
    return "\n".join(lines)


def format_check_checkpoint_restore_report_text(report: dict[str, object]) -> str:
    return format_checkpoint_restore_report_text_with_title("Check checkpoint restore:", report)


def format_checkpoint_restore_report_text(report: dict[str, object]) -> str:
    return format_checkpoint_restore_report_text_with_title("Checkpoint restore:", report)


def format_checkpoint_restore_report_text_with_title(title: str, report: dict[str, object]) -> str:
    saved = report.get("saved") if isinstance(report.get("saved"), dict) else {}
    current = report.get("current") if isinstance(report.get("current"), dict) else {}
    lines = [
        title,
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  id: {report.get('id') or '.'}",
    ]
    if "restored" in report:
        lines.append(f"  restored: {'yes' if bool(report.get('restored')) else 'no'}")
    if report.get("savedHead") or report.get("currentHead"):
        lines.append(f"  savedHead: {short_head(str(report.get('savedHead') or ''))}")
        lines.append(f"  currentHead: {short_head(str(report.get('currentHead') or ''))}")
    lines.extend(
        [
            "  saved:",
            f"    untrackedFiles: {saved.get('untrackedFiles', 0)}",
            f"    stagedPatchChars: {saved.get('stagedPatchChars', 0)}",
            f"    unstagedPatchChars: {saved.get('unstagedPatchChars', 0)}",
            "  current:",
            f"    untrackedFiles: {current.get('untrackedFiles', 0)}",
            f"  message: {report.get('message')}",
        ]
    )
    if "matches" in report:
        lines.insert(-1, f"  matches: {'yes' if bool(report.get('matches')) else 'no'}")
    return "\n".join(lines)


def format_check_checkpoint_delete_report_text(report: dict[str, object]) -> str:
    lines = [
        "Check checkpoint delete:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  canDelete: {'yes' if bool(report.get('canDelete')) else 'no'}",
        f"  id: {report.get('id') or ''}",
    ]
    if report.get("label") or report.get("createdAt"):
        lines.append(f"  label: {report.get('label') or ''}")
        lines.append(f"  createdAt: {report.get('createdAt') or ''}")
    lines.append(f"  message: {report.get('message')}")
    return "\n".join(lines)


def format_checkpoint_delete_report_text(report: dict[str, object]) -> str:
    return "\n".join(
        [
            "Checkpoint delete:",
            f"  projectRoot: {report.get('projectRoot') or '.'}",
            f"  deleted: {'yes' if bool(report.get('deleted')) else 'no'}",
            f"  id: {report.get('id') or ''}",
            f"  message: {report.get('message')}",
        ]
    )


def format_check_checkpoint_prune_report_text(report: dict[str, object]) -> str:
    if str(report.get("message") or "").startswith("Usage:"):
        return str(report["message"])
    lines = [
        "Check checkpoint prune:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  keepLast: {report.get('keepLast')}",
        f"  total: {report.get('total', 0)}",
        f"  kept: {report.get('kept', 0)}",
        f"  deleteCount: {report.get('deleteCount', 0)}",
    ]
    _append_checkpoint_item_lines(lines, report)
    lines.append(f"  message: {report.get('message')}")
    return "\n".join(lines)


def format_checkpoint_prune_report_text(report: dict[str, object]) -> str:
    if str(report.get("message") or "").startswith("Usage:"):
        return str(report["message"])
    lines = [
        "Checkpoint prune:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  keepLast: {report.get('keepLast')}",
        f"  total: {report.get('total', 0)}",
        f"  kept: {report.get('kept', 0)}",
        f"  deleted: {report.get('deleted', 0)}",
    ]
    _append_checkpoint_item_lines(lines, report)
    lines.append(f"  message: {report.get('message')}")
    return "\n".join(lines)


def _append_checkpoint_item_lines(lines: list[str], report: dict[str, object]) -> None:
    checkpoints = report.get("checkpoints")
    items = checkpoints if isinstance(checkpoints, list) else []
    if items:
        lines.append("  checkpoints:")
        for checkpoint in items:
            if not isinstance(checkpoint, dict):
                continue
            label_text = f" label={checkpoint.get('label')}" if checkpoint.get("label") else ""
            lines.append(
                "    - "
                f"{checkpoint.get('id')} created={checkpoint.get('createdAt')}"
                f"{label_text} changedFiles={checkpoint.get('changedFiles', 0)}"
                f" staged={checkpoint.get('stagedFiles', 0)}"
                f" unstaged={checkpoint.get('unstagedFiles', 0)}"
                f" untracked={checkpoint.get('untrackedFiles', 0)}"
            )
    else:
        lines.append("  checkpoints: none")
