from __future__ import annotations

from pathlib import Path

from .local_command_workspace import local_command_workspace
from .workflow_review_formatting import format_review_file
from .workspace import read_git_changes


def get_changes_report(project_root: str | Path = ".", max_files: int = 200) -> dict[str, object]:
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 500:
        raise ValueError("max_files must be at most 500.")
    root = Path(project_root).resolve()
    workspace = local_command_workspace(root, "local-changes")
    changes = read_git_changes(workspace)
    if not bool(changes["ok"]):
        return {
            "projectRoot": str(root),
            "ok": False,
            "changedFiles": {"shown": 0, "total": 0, "truncated": False, "files": []},
            "counts": {
                "staged": 0,
                "unstaged": 0,
                "untracked": 0,
                "binary": 0,
                "insertions": 0,
                "deletions": 0,
            },
            "message": str(changes["message"]),
        }

    files = [item for item in changes["files"] if isinstance(item, dict)]
    shown = files[:max_files]
    return {
        "projectRoot": str(root),
        "ok": True,
        "changedFiles": {
            "shown": len(shown),
            "total": len(files),
            "truncated": len(shown) < len(files),
            "files": shown,
        },
        "counts": _changed_file_counts(files),
        "message": str(changes["message"]),
    }


def _changed_file_counts(files: list[dict[str, object]]) -> dict[str, int]:
    return {
        "staged": sum(1 for item in files if item.get("staged") is True),
        "unstaged": sum(1 for item in files if item.get("unstaged") is True and item.get("untracked") is not True),
        "untracked": sum(1 for item in files if item.get("untracked") is True),
        "binary": sum(1 for item in files if item.get("binary") is True),
        "insertions": sum(
            int(item.get("staged_insertions") or 0) + int(item.get("unstaged_insertions") or 0)
            for item in files
        ),
        "deletions": sum(
            int(item.get("staged_deletions") or 0) + int(item.get("unstaged_deletions") or 0)
            for item in files
        ),
    }


def format_changes_report_text(report: dict[str, object]) -> str:
    changed_files = report["changedFiles"] if isinstance(report["changedFiles"], dict) else {}
    files = changed_files.get("files", []) if isinstance(changed_files, dict) else []
    counts = report["counts"] if isinstance(report["counts"], dict) else {}
    lines = [
        "Changes:",
        f"  projectRoot: {report['projectRoot']}",
        f"  ok: {'yes' if bool(report['ok']) else 'no'}",
    ]
    if bool(report["ok"]):
        lines.extend(
            [
                f"  changedFiles: {changed_files.get('total', 0)}",
                f"  shownFiles: {changed_files.get('shown', 0)}/{changed_files.get('total', 0)}",
                f"  stagedFiles: {counts.get('staged', 0)}",
                f"  unstagedFiles: {counts.get('unstaged', 0)}",
                f"  untrackedFiles: {counts.get('untracked', 0)}",
                f"  binaryFiles: {counts.get('binary', 0)}",
                f"  insertions: {counts.get('insertions', 0)}",
                f"  deletions: {counts.get('deletions', 0)}",
                f"  truncated: {'yes' if bool(changed_files.get('truncated')) else 'no'}",
            ]
        )
    if files:
        lines.append("  files:")
        lines.extend(format_review_file(item) for item in files if isinstance(item, dict))
    elif bool(report["ok"]):
        lines.append("  files: none")
    lines.append(f"  message: {report['message']}")
    return "\n".join(lines)


def get_changes_text(project_root: str | Path = ".", max_files: int = 200) -> str:
    return format_changes_report_text(get_changes_report(project_root, max_files=max_files))
