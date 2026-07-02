from __future__ import annotations

import re

from .workspace_core import GitCommandResult, RunWorkspace
from .workspace_git_utils import run_readonly_git
from .workspace_resolve import resolve_inside_run


def read_git_diff(workspace: RunWorkspace, relative_path: str | None = None, staged: bool = False) -> GitCommandResult:
    args = ["diff"]
    if staged:
        args.append("--cached")
    if relative_path:
        resolve_inside_run(workspace.root, relative_path)
        args.extend(["--", relative_path])
    return run_readonly_git(workspace.root, args)


def read_git_diff_hunks(
    workspace: RunWorkspace,
    relative_path: str | None = None,
    staged: bool = False,
    max_hunks: int = 80,
    max_lines_per_hunk: int = 80,
) -> dict[str, object]:
    if max_hunks < 1:
        raise ValueError("max_hunks must be at least 1.")
    if max_hunks > 500:
        raise ValueError("max_hunks must be at most 500.")
    if max_lines_per_hunk < 1:
        raise ValueError("max_lines_per_hunk must be at least 1.")
    if max_lines_per_hunk > 500:
        raise ValueError("max_lines_per_hunk must be at most 500.")

    result = read_git_diff(workspace, relative_path, staged)
    hunks = parse_git_diff_hunks(result.stdout, max_hunks=max_hunks, max_lines_per_hunk=max_lines_per_hunk)
    return {
        "ok": result.ok,
        "hunks": hunks["hunks"],
        "total_hunks": hunks["total_hunks"],
        "truncated": bool(hunks["truncated"]),
        "path": relative_path,
        "staged": staged,
        "message": "Read git diff hunks." if result.ok else result.stderr or "git diff failed.",
    }


def parse_git_diff_hunks(diff: str, max_hunks: int = 80, max_lines_per_hunk: int = 80) -> dict[str, object]:
    hunks: list[dict[str, object]] = []
    total_hunks = 0
    current_file = ""
    current_hunk: dict[str, object] | None = None
    current_lines: list[str] = []
    lines_truncated = False

    def finish_hunk() -> None:
        nonlocal current_hunk, current_lines, lines_truncated
        if current_hunk is None:
            return
        current_hunk["lines"] = current_lines
        current_hunk["lines_truncated"] = lines_truncated
        if len(hunks) < max_hunks:
            hunks.append(current_hunk)
        current_hunk = None
        current_lines = []
        lines_truncated = False

    for line in diff.splitlines():
        if line.startswith("diff --git "):
            finish_hunk()
            current_file = parse_git_diff_file_path(line)
            continue
        hunk_match = re.match(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
        if hunk_match:
            finish_hunk()
            total_hunks += 1
            old_start = int(hunk_match.group(1))
            old_count = int(hunk_match.group(2) or "1")
            new_start = int(hunk_match.group(3))
            new_count = int(hunk_match.group(4) or "1")
            current_hunk = {
                "file": current_file,
                "old_start": old_start,
                "old_count": old_count,
                "new_start": new_start,
                "new_count": new_count,
                "added": 0,
                "deleted": 0,
                "context": 0,
                "header": line,
            }
            current_lines = []
            lines_truncated = False
            continue
        if current_hunk is None:
            continue
        if line.startswith("+") and not line.startswith("+++"):
            current_hunk["added"] = int(current_hunk["added"]) + 1
        elif line.startswith("-") and not line.startswith("---"):
            current_hunk["deleted"] = int(current_hunk["deleted"]) + 1
        elif line.startswith(" "):
            current_hunk["context"] = int(current_hunk["context"]) + 1
        if len(current_lines) < max_lines_per_hunk:
            current_lines.append(line)
        else:
            lines_truncated = True

    finish_hunk()
    return {
        "hunks": hunks,
        "total_hunks": total_hunks,
        "truncated": total_hunks > len(hunks) or any(bool(hunk["lines_truncated"]) for hunk in hunks),
    }


def parse_git_diff_file_path(line: str) -> str:
    match = re.match(r"^diff --git a/(.*?) b/(.*)$", line)
    if not match:
        return ""
    return match.group(2)


def read_git_log(workspace: RunWorkspace, max_count: int = 5, relative_path: str | None = None) -> GitCommandResult:
    if max_count < 1:
        raise ValueError("max_count must be at least 1.")
    if max_count > 50:
        raise ValueError("max_count must be at most 50.")
    args = ["log", "--oneline", "--decorate", f"--max-count={max_count}"]
    if relative_path:
        resolve_inside_run(workspace.root, relative_path)
        args.extend(["--", relative_path])
    return run_readonly_git(workspace.root, args)


def read_git_show(workspace: RunWorkspace, rev: str = "HEAD", relative_path: str | None = None) -> GitCommandResult:
    rev = rev.strip()
    if not rev:
        raise ValueError("rev must be a non-empty string.")
    if rev.startswith("-"):
        raise ValueError("rev must not start with '-'.")
    args = ["show", "--stat", "--patch", "--format=fuller", "--no-ext-diff", rev]
    if relative_path:
        resolve_inside_run(workspace.root, relative_path)
        args.extend(["--", relative_path])
    return run_readonly_git(workspace.root, args)


def read_git_blame(
    workspace: RunWorkspace,
    relative_path: str,
    start_line: int | None = None,
    line_count: int | None = None,
) -> GitCommandResult:
    if not relative_path or not relative_path.strip():
        raise ValueError("path must be a non-empty string.")
    target = resolve_inside_run(workspace.root, relative_path)
    if not target.is_file():
        raise ValueError(f"Path is not a file: {relative_path}")
    if start_line is not None and start_line < 1:
        raise ValueError("start_line must be at least 1.")
    if line_count is not None and line_count < 1:
        raise ValueError("line_count must be at least 1.")
    if line_count is not None and line_count > 1000:
        raise ValueError("line_count must be at most 1000.")

    args = ["blame", "--date=short"]
    if start_line is not None:
        args.extend(["-L", f"{start_line},+{line_count or 120}"])
    args.extend(["--", relative_path])
    return run_readonly_git(workspace.root, args)
