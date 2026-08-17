from __future__ import annotations

from .workspace_core import GitCommandResult, RunWorkspace
from .workspace_git_diff_parser import (
    StreamingGitDiffHunkParser,
    parse_git_diff_file_path,
    parse_git_diff_hunks,
)
from .workspace_git_utils import run_readonly_git, run_streaming_readonly_git
from .workspace_resolve import resolve_inside_run


def read_git_diff(
    workspace: RunWorkspace,
    relative_path: str | None = None,
    staged: bool = False,
    *,
    max_output_chars: int | None = None,
) -> GitCommandResult:
    args = _git_diff_args(workspace, relative_path, staged)
    return run_readonly_git(workspace.root, args, max_output_chars=max_output_chars)


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

    parser = StreamingGitDiffHunkParser(
        max_hunks=max_hunks,
        max_lines_per_hunk=max_lines_per_hunk,
    )
    result = run_streaming_readonly_git(
        workspace.root,
        _git_diff_args(workspace, relative_path, staged),
        parser.append,
    )
    hunks = (
        parser.finish()
        if result.exit_code is not None
        else {"hunks": [], "total_hunks": 0, "truncated": False}
    )
    return {
        "ok": result.ok,
        "hunks": hunks["hunks"],
        "total_hunks": hunks["total_hunks"],
        "truncated": bool(hunks["truncated"]),
        "path": relative_path,
        "staged": staged,
        "message": "Read git diff hunks." if result.ok else result.stderr or "git diff failed.",
    }


def _git_diff_args(workspace: RunWorkspace, relative_path: str | None, staged: bool) -> list[str]:
    args = ["diff"]
    if staged:
        args.append("--cached")
    if relative_path:
        resolve_inside_run(workspace.root, relative_path)
        args.extend(["--", relative_path])
    return args


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


def read_git_show(
    workspace: RunWorkspace,
    rev: str = "HEAD",
    relative_path: str | None = None,
    *,
    max_output_chars: int | None = None,
) -> GitCommandResult:
    rev = rev.strip()
    if not rev:
        raise ValueError("rev must be a non-empty string.")
    if rev.startswith("-"):
        raise ValueError("rev must not start with '-'.")
    args = ["show", "--stat", "--patch", "--format=fuller", "--no-ext-diff", rev]
    if relative_path:
        resolve_inside_run(workspace.root, relative_path)
        args.extend(["--", relative_path])
    return run_readonly_git(workspace.root, args, max_output_chars=max_output_chars)


def read_git_blame(
    workspace: RunWorkspace,
    relative_path: str,
    start_line: int | None = None,
    line_count: int | None = None,
    *,
    max_output_chars: int | None = None,
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
    return run_readonly_git(workspace.root, args, max_output_chars=max_output_chars)
