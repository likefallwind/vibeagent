from __future__ import annotations

from pathlib import Path

from .actions import execute_action
from .local_command_workspace import local_command_workspace
from .types import GitDiffContextsAction, GitDiffHunksAction
from .workflow_plain_diff_commands import DIFF_USAGE, format_diff_report_text, get_diff_report, get_diff_text
from .workflow_diff_utils import (
    clip_with_flag,
    indent_block as _indent_block,
    parse_diff_argument,
    usage_error as _usage_error,
    validate_diff_contexts_limits,
    validate_diff_hunks_limits,
)

DIFF_HUNKS_USAGE = "Usage: /diff-hunks [--staged|--cached] [--max-hunks N] [--max-lines N] [path]"
DIFF_CONTEXTS_USAGE = "Usage: /diff-contexts [--staged|--cached] [--context-lines N] [--max-hunks N] [--max-bytes N] [path]"


def serialize_diff_hunk(hunk: object) -> dict[str, object]:
    return {
        "file": str(getattr(hunk, "file", "")),
        "oldStart": int(getattr(hunk, "old_start", 0)),
        "oldCount": int(getattr(hunk, "old_count", 0)),
        "newStart": int(getattr(hunk, "new_start", 0)),
        "newCount": int(getattr(hunk, "new_count", 0)),
        "added": int(getattr(hunk, "added", 0)),
        "deleted": int(getattr(hunk, "deleted", 0)),
        "context": int(getattr(hunk, "context", 0)),
        "header": str(getattr(hunk, "header", "")),
        "lines": list(getattr(hunk, "lines", [])),
        "linesTruncated": bool(getattr(hunk, "lines_truncated", False)),
    }


def format_diff_hunk_lines(lines: list[str]) -> str:
    return "\n".join(lines)


def get_diff_hunks_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    max_hunks: int = 80,
    max_lines_per_hunk: int = 80,
) -> dict[str, object]:
    limit_error = validate_diff_hunks_limits(
        DIFF_HUNKS_USAGE,
        max_hunks=max_hunks,
        max_lines_per_hunk=max_lines_per_hunk,
    )
    root = Path(project_root).resolve()
    if limit_error:
        return {
            "projectRoot": str(root),
            "ok": False,
            "scope": "unstaged",
            "path": ".",
            "hunks": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "message": limit_error,
        }
    parsed = parse_diff_argument(argument)
    if parsed is None:
        return {
            "projectRoot": str(root),
            "ok": False,
            "scope": "unstaged",
            "path": ".",
            "hunks": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "message": DIFF_HUNKS_USAGE,
        }

    workspace = local_command_workspace(root, "local-diff-hunks")
    staged, path = parsed
    observation = execute_action(
        workspace,
        GitDiffHunksAction(
            type="git_diff_hunks",
            path=path,
            staged=staged,
            max_hunks=max_hunks,
            max_lines_per_hunk=max_lines_per_hunk,
        ),
    )
    if observation.kind != "git_diff_hunks":
        return {
            "projectRoot": str(root),
            "ok": False,
            "scope": "staged" if staged else "unstaged",
            "path": path or ".",
            "hunks": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "message": f"Unexpected observation: {observation.kind}",
        }
    return {
        "projectRoot": str(root),
        "ok": bool(observation.ok),
        "scope": "staged" if observation.staged else "unstaged",
        "path": observation.path or ".",
        "hunks": {
            "shown": len(observation.hunks),
            "total": observation.total_hunks,
            "truncated": bool(observation.truncated),
            "items": [serialize_diff_hunk(hunk) for hunk in observation.hunks],
        },
        "message": observation.message,
    }


def format_diff_hunks_report_text(report: dict[str, object]) -> str:
    hunks = report.get("hunks") if isinstance(report.get("hunks"), dict) else {}
    items = hunks.get("items", []) if isinstance(hunks, dict) else []
    lines = [
        "Diff hunks:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  scope: {report.get('scope') or 'unstaged'}",
        f"  path: {report.get('path') or '.'}",
        f"  hunks: {hunks.get('shown', 0)}/{hunks.get('total', 0)}",
        f"  truncated: {'yes' if bool(hunks.get('truncated')) else 'no'}",
        f"  message: {report.get('message')}",
    ]
    if not bool(report.get("ok")):
        return "\n".join(lines)
    if not items:
        lines.append("  items: none")
        return "\n".join(lines)

    lines.append("  items:")
    for index, hunk in enumerate(items, start=1):
        if not isinstance(hunk, dict):
            continue
        lines.extend(
            [
                f"    - hunk: {index}",
                f"      file: {hunk.get('file')}",
                f"      oldRange: {hunk.get('oldStart')},{hunk.get('oldCount')}",
                f"      newRange: {hunk.get('newStart')},{hunk.get('newCount')}",
                f"      added: {hunk.get('added')}",
                f"      deleted: {hunk.get('deleted')}",
                f"      context: {hunk.get('context')}",
                f"      linesTruncated: {'yes' if bool(hunk.get('linesTruncated')) else 'no'}",
                f"      header: {hunk.get('header')}",
            ]
        )
        hunk_lines = hunk.get("lines") if isinstance(hunk.get("lines"), list) else []
        if hunk_lines:
            lines.append("      lines:")
            lines.append(_indent_block(format_diff_hunk_lines([str(line) for line in hunk_lines]), spaces=8))
        else:
            lines.append("      lines: none")
    return "\n".join(lines)


def get_diff_hunks_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    max_hunks: int = 80,
    max_lines_per_hunk: int = 80,
) -> str:
    report = get_diff_hunks_report(project_root, argument, max_hunks=max_hunks, max_lines_per_hunk=max_lines_per_hunk)
    if str(report.get("message") or "").startswith("Usage:"):
        return str(report["message"])
    return format_diff_hunks_report_text(report)


def serialize_file_context_result(context: object) -> dict[str, object]:
    return {
        "path": str(getattr(context, "path", "")),
        "line": int(getattr(context, "line", 0)),
        "contextLines": int(getattr(context, "context_lines", 0)),
        "ok": bool(getattr(context, "ok", False)),
        "content": str(getattr(context, "content", "")),
        "message": str(getattr(context, "message", "")),
        "startLine": int(getattr(context, "start_line", 0)),
        "endLine": int(getattr(context, "end_line", 0)),
        "lineCount": int(getattr(context, "line_count", 0)),
        "totalLines": int(getattr(context, "total_lines", 0)),
        "targetLineExists": bool(getattr(context, "target_line_exists", False)),
        "truncated": bool(getattr(context, "truncated", False)),
        "maxBytes": int(getattr(context, "max_bytes", 0)),
    }


def get_diff_contexts_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    context_lines: int = 5,
    max_hunks: int = 80,
    max_bytes_per_context: int = 20_000,
) -> dict[str, object]:
    limit_error = validate_diff_contexts_limits(
        DIFF_CONTEXTS_USAGE,
        context_lines=context_lines,
        max_hunks=max_hunks,
        max_bytes_per_context=max_bytes_per_context,
    )
    root = Path(project_root).resolve()
    if limit_error:
        return {
            "projectRoot": str(root),
            "ok": False,
            "scope": "unstaged",
            "path": ".",
            "contextLines": context_lines,
            "contexts": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "message": limit_error,
        }
    parsed = parse_diff_argument(argument)
    if parsed is None:
        return {
            "projectRoot": str(root),
            "ok": False,
            "scope": "unstaged",
            "path": ".",
            "contextLines": context_lines,
            "contexts": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "message": DIFF_CONTEXTS_USAGE,
        }

    workspace = local_command_workspace(root, "local-diff-contexts")
    staged, path = parsed
    observation = execute_action(
        workspace,
        GitDiffContextsAction(
            type="git_diff_contexts",
            path=path,
            staged=staged,
            context_lines=context_lines,
            max_hunks=max_hunks,
            max_bytes_per_context=max_bytes_per_context,
        ),
    )
    if observation.kind != "git_diff_contexts":
        return {
            "projectRoot": str(root),
            "ok": False,
            "scope": "staged" if staged else "unstaged",
            "path": path or ".",
            "contextLines": context_lines,
            "contexts": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "message": f"Unexpected observation: {observation.kind}",
        }
    return {
        "projectRoot": str(root),
        "ok": bool(observation.ok),
        "scope": "staged" if observation.staged else "unstaged",
        "path": observation.path or ".",
        "contextLines": observation.context_lines,
        "contexts": {
            "shown": len(observation.contexts),
            "total": observation.total_hunks,
            "truncated": bool(observation.truncated),
            "items": [
                {
                    "hunk": serialize_diff_hunk(item.hunk),
                    "context": serialize_file_context_result(item.context),
                }
                for item in observation.contexts
            ],
        },
        "message": observation.message,
    }


def format_diff_contexts_report_text(report: dict[str, object]) -> str:
    contexts = report.get("contexts") if isinstance(report.get("contexts"), dict) else {}
    items = contexts.get("items", []) if isinstance(contexts, dict) else []
    lines = [
        "Diff contexts:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  scope: {report.get('scope') or 'unstaged'}",
        f"  path: {report.get('path') or '.'}",
        f"  contexts: {contexts.get('shown', 0)}/{contexts.get('total', 0)}",
        f"  contextLines: {report.get('contextLines', 0)}",
        f"  truncated: {'yes' if bool(contexts.get('truncated')) else 'no'}",
        f"  message: {report.get('message')}",
    ]
    if not bool(report.get("ok")):
        return "\n".join(lines)
    if not items:
        lines.append("  items: none")
        return "\n".join(lines)

    lines.append("  items:")
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        hunk = item.get("hunk") if isinstance(item.get("hunk"), dict) else {}
        context = item.get("context") if isinstance(item.get("context"), dict) else {}
        lines.extend(
            [
                f"    - hunk: {index}",
                f"      file: {hunk.get('file')}",
                f"      oldRange: {hunk.get('oldStart')},{hunk.get('oldCount')}",
                f"      newRange: {hunk.get('newStart')},{hunk.get('newCount')}",
                f"      added: {hunk.get('added')}",
                f"      deleted: {hunk.get('deleted')}",
                f"      contextOk: {'yes' if bool(context.get('ok')) else 'no'}",
                f"      sourceRange: {context.get('startLine', 0)}-{context.get('endLine', 0)}",
                f"      sourceTruncated: {'yes' if bool(context.get('truncated')) else 'no'}",
            ]
        )
        if bool(context.get("ok")) and context.get("content"):
            lines.append("      source:")
            lines.append(_indent_block(str(context.get("content")), spaces=8))
        elif bool(context.get("ok")):
            lines.append("      source: none")
        else:
            lines.append(f"      sourceError: {context.get('message')}")
    return "\n".join(lines)


def get_diff_contexts_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    context_lines: int = 5,
    max_hunks: int = 80,
    max_bytes_per_context: int = 20_000,
) -> str:
    report = get_diff_contexts_report(
        project_root,
        argument,
        context_lines=context_lines,
        max_hunks=max_hunks,
        max_bytes_per_context=max_bytes_per_context,
    )
    if str(report.get("message") or "").startswith("Usage:"):
        return str(report["message"])
    return format_diff_contexts_report_text(report)
