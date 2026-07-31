from __future__ import annotations

from pathlib import Path

from .local_command_workspace import local_command_workspace
from .workspace import read_git_diff
from .workflow_diff_utils import clip_with_flag, parse_diff_argument


DIFF_USAGE = "Usage: /diff [--staged|--cached] [path]"


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
            "message": DIFF_USAGE,
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
