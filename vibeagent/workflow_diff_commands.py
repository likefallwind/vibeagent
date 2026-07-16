from __future__ import annotations

from pathlib import Path
import shlex

from .actions import execute_action
from .local_command_workspace import local_command_workspace
from .types import GitDiffContextsAction, GitDiffHunksAction
from .workspace import read_git_diff


def get_diff_report(project_root: str | Path = ".", argument: str | None = None, max_chars: int = 12_000) -> dict[str, object]:
    if max_chars < 100:
        raise ValueError("max_chars must be at least 100.")
    if max_chars > 200_000:
        raise ValueError("max_chars must be at most 200000.")
    parsed = parse_diff_argument(argument)
    if parsed is None:
        return {
            "projectRoot": str(Path(project_root).resolve()),
            "ok": False,
            "scope": "unstaged",
            "path": ".",
            "diff": "",
            "chars": 0,
            "truncated": False,
            "maxChars": max_chars,
            "message": "Usage: /diff [--staged|--cached] [path]",
        }

    root = Path(project_root).resolve()
    workspace = local_command_workspace(root, "local-diff")
    staged, path = parsed
    try:
        result = read_git_diff(workspace, relative_path=path, staged=staged)
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "ok": False,
            "scope": "staged" if staged else "unstaged",
            "path": path or ".",
            "diff": "",
            "chars": 0,
            "truncated": False,
            "maxChars": max_chars,
            "message": str(error),
        }
    diff, truncated = clip_with_flag(result.stdout, max_chars)
    return {
        "projectRoot": str(root),
        "ok": bool(result.ok),
        "scope": "staged" if staged else "unstaged",
        "path": path or ".",
        "diff": diff,
        "chars": len(result.stdout),
        "truncated": truncated,
        "maxChars": max_chars,
        "message": "Read git diff." if result.ok else result.stderr or "git diff failed.",
    }


def format_diff_report_text(report: dict[str, object]) -> str:
    lines = [
        "Diff:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  scope: {report.get('scope') or 'unstaged'}",
        f"  path: {report.get('path') or '.'}",
    ]
    if not bool(report.get("ok")):
        lines.append(f"  error: {report.get('message') or 'git diff failed.'}")
        return "\n".join(lines)
    diff = str(report.get("diff") or "")
    if not diff:
        lines.append("  output: no changes")
        return "\n".join(lines)

    lines.append(f"  chars: {report.get('chars', 0)}")
    lines.append(f"  truncated: {'yes' if bool(report.get('truncated')) else 'no'}")
    lines.append("")
    lines.append(diff)
    return "\n".join(lines)


def get_diff_text(project_root: str | Path = ".", argument: str | None = None, max_chars: int = 12_000) -> str:
    report = get_diff_report(project_root, argument, max_chars=max_chars)
    if str(report.get("message") or "").startswith("Usage:"):
        return str(report["message"])
    return format_diff_report_text(report)


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
    usage = "Usage: /diff-hunks [--staged|--cached] [--max-hunks N] [--max-lines N] [path]"
    limit_error = validate_diff_hunks_limits(usage, max_hunks=max_hunks, max_lines_per_hunk=max_lines_per_hunk)
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
            "message": usage,
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
    usage = "Usage: /diff-contexts [--staged|--cached] [--context-lines N] [--max-hunks N] [--max-bytes N] [path]"
    limit_error = validate_diff_contexts_limits(
        usage,
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
            "message": usage,
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


def validate_diff_hunks_limits(usage: str, max_hunks: int, max_lines_per_hunk: int) -> str | None:
    if max_hunks < 1:
        return f"{usage}\nError: max_hunks must be at least 1."
    if max_hunks > 500:
        return f"{usage}\nError: max_hunks must be at most 500."
    if max_lines_per_hunk < 1:
        return f"{usage}\nError: max_lines_per_hunk must be at least 1."
    if max_lines_per_hunk > 500:
        return f"{usage}\nError: max_lines_per_hunk must be at most 500."
    return None


def validate_diff_contexts_limits(
    usage: str,
    context_lines: int,
    max_hunks: int,
    max_bytes_per_context: int,
) -> str | None:
    if context_lines < 0:
        return f"{usage}\nError: context_lines must be at least 0."
    if context_lines > 500:
        return f"{usage}\nError: context_lines must be at most 500."
    if max_hunks < 1:
        return f"{usage}\nError: max_hunks must be at least 1."
    if max_hunks > 500:
        return f"{usage}\nError: max_hunks must be at most 500."
    if max_bytes_per_context < 1_000:
        return f"{usage}\nError: max_bytes_per_context must be at least 1000."
    if max_bytes_per_context > 200_000:
        return f"{usage}\nError: max_bytes_per_context must be at most 200000."
    return None


def parse_diff_argument(argument: str | None) -> tuple[bool, str | None] | None:
    if not argument:
        return False, None
    try:
        parts = shlex.split(argument)
    except ValueError:
        return None
    staged = False
    paths: list[str] = []
    for part in parts:
        if part in {"--staged", "--cached"}:
            staged = True
        elif part == "--":
            continue
        elif part.startswith("-"):
            return None
        else:
            paths.append(part)
    if len(paths) > 1:
        return None
    return staged, paths[0] if paths else None


def clip_with_flag(value: str, max_chars: int) -> tuple[str, bool]:
    if len(value) <= max_chars:
        return value.rstrip(), False
    return f"{value[:max_chars].rstrip()}\n[diff output truncated]", True


def _indent_block(value: str, spaces: int = 2) -> str:
    prefix = " " * spaces
    return "\n".join(f"{prefix}{line}" if line else prefix.rstrip() for line in value.splitlines())
