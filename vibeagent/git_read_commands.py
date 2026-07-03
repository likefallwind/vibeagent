from __future__ import annotations

from pathlib import Path
import shlex

from .actions import execute_action
from .command_parsing import parse_optional_single_path_argument
from .read_command_parsing import parse_read_request
from .git_read_report_helpers import (
    clip as _clip,
    clip_with_flag,
    format_blame_report_text,
    format_branches_report_text,
    format_git_conflicts_report_text,
    format_git_info_report_text,
    format_git_status_report_text,
    format_log_report_text,
    format_show_report_text,
    indent_block as _indent_block,
)
from .types import GitBlameAction, GitBranchesAction, GitConflictsAction, GitInfoAction, GitLogAction, GitShowAction, GitStatusAction
from .workspace_core import RunWorkspace


def _split_nonempty_lines(value: str) -> list[str]:
    return [line for line in value.splitlines() if line.strip()]


def _git_status_payload(status: str) -> dict[str, object]:
    lines = _split_nonempty_lines(status)
    return {"text": status, "lines": lines, "count": len(lines)}


def _git_output_payload(output: str, *, truncated: bool, max_output_chars: int) -> dict[str, object]:
    lines = output.splitlines()
    return {
        "text": output,
        "chars": len(output),
        "lines": len(lines),
        "truncated": truncated,
        "maxOutputChars": max_output_chars,
    }


def _git_log_items(log: str) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for line in _split_nonempty_lines(log):
        short_hash, _, subject = line.partition(" ")
        items.append(
            {
                "hash": short_hash,
                "subject": subject,
                "raw": line,
            }
        )
    return items


def get_git_status_report(project_root: str | Path = ".") -> dict[str, object]:
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-git-status", session_dir=root / ".vibeagent" / "sessions" / "local-git-status")
    observation = execute_action(workspace, GitStatusAction(type="git_status"))
    if observation.kind != "git_status":
        return {
            "projectRoot": str(root),
            "ok": False,
            "status": _git_status_payload(""),
            "message": f"Unexpected observation: {observation.kind}",
        }
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "status": _git_status_payload(observation.status),
        "message": observation.message,
    }


def get_git_status_text(project_root: str | Path = ".") -> str:
    return format_git_status_report_text(get_git_status_report(project_root))


def get_git_conflicts_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    max_markers: int = 200,
    max_files: int = 5000,
) -> str:
    return format_git_conflicts_report_text(get_git_conflicts_report(project_root, argument, max_markers, max_files))


def get_git_conflicts_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    max_markers: int = 200,
    max_files: int = 5000,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        path = parse_optional_single_path_argument(argument)
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "ok": False,
            "path": "",
            "unmerged": {"shown": 0, "total": 0, "items": []},
            "markers": {"shown": 0, "total": 0, "items": []},
            "scannedFiles": 0,
            "totalFiles": 0,
            "truncated": False,
            "message": f"Usage: /conflicts [path]\n  message: {error}",
        }

    workspace = RunWorkspace(root=root, run_id="local-git-conflicts", session_dir=root / ".vibeagent" / "sessions" / "local-git-conflicts")
    observation = execute_action(
        workspace,
        GitConflictsAction(
            type="git_conflicts",
            path=path,
            max_markers=max_markers,
            max_files=max_files,
        ),
    )
    if observation.kind != "git_conflicts":
        return {
            "projectRoot": str(root),
            "ok": False,
            "path": path or "",
            "unmerged": {"shown": 0, "total": 0, "items": []},
            "markers": {"shown": 0, "total": 0, "items": []},
            "scannedFiles": 0,
            "totalFiles": 0,
            "truncated": False,
            "message": f"Unexpected observation: {observation.kind}",
        }

    unmerged_items = [
        {"status": item.status, "path": item.path}
        for item in observation.unmerged
    ]
    marker_items = [
        {"path": item.path, "line": item.line, "marker": item.marker, "text": item.text}
        for item in observation.markers
    ]
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "path": observation.path,
        "unmerged": {"shown": len(unmerged_items), "total": observation.unmerged_total, "items": unmerged_items},
        "markers": {"shown": len(marker_items), "total": observation.markers_total, "items": marker_items},
        "scannedFiles": observation.scanned_files,
        "totalFiles": observation.total_files,
        "truncated": observation.truncated,
        "message": observation.message,
    }


def get_git_info_report(project_root: str | Path = ".") -> dict[str, object]:
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-git-info", session_dir=root / ".vibeagent" / "sessions" / "local-git-info")
    observation = execute_action(workspace, GitInfoAction(type="git_info"))
    if observation.kind != "git_info":
        return {
            "projectRoot": str(root),
            "ok": False,
            "isGitRepo": False,
            "branch": "",
            "head": "",
            "upstream": "",
            "ahead": 0,
            "behind": 0,
            "remotes": [],
            "status": _git_status_payload(""),
            "message": f"Unexpected observation: {observation.kind}",
        }
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "isGitRepo": observation.is_git_repo,
        "branch": observation.branch,
        "head": observation.head,
        "upstream": observation.upstream,
        "ahead": observation.ahead,
        "behind": observation.behind,
        "remotes": [
            {"name": remote.name, "kind": remote.kind, "url": remote.url}
            for remote in observation.remotes
        ],
        "status": _git_status_payload(observation.status),
        "message": observation.message,
    }


def get_git_info_text(project_root: str | Path = ".") -> str:
    return format_git_info_report_text(get_git_info_report(project_root))


def get_branches_report(project_root: str | Path = ".", max_branches: int = 100) -> dict[str, object]:
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-branches", session_dir=root / ".vibeagent" / "sessions" / "local-branches")
    observation = execute_action(
        workspace,
        GitBranchesAction(type="git_branches", max_branches=max_branches),
    )
    if observation.kind != "git_branches":
        return {
            "projectRoot": str(root),
            "ok": False,
            "current": "",
            "branches": {"shown": 0, "total": 0, "truncated": False, "items": []},
            "gitStatus": _git_status_payload(""),
            "message": f"Unexpected observation: {observation.kind}",
        }
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "current": observation.current,
        "branches": {
            "shown": len(observation.branches),
            "total": observation.total,
            "truncated": observation.truncated,
            "items": [
                {"name": branch.name, "current": branch.current}
                for branch in observation.branches
            ],
        },
        "gitStatus": _git_status_payload(observation.status),
        "message": observation.message,
    }


def get_branches_text(project_root: str | Path = ".", max_branches: int = 100) -> str:
    return format_branches_report_text(get_branches_report(project_root, max_branches=max_branches))


def get_log_text(project_root: str | Path = ".", argument: str | None = None, max_count: int = 5) -> str:
    return format_log_report_text(get_log_report(project_root, argument, max_count=max_count))


def parse_log_request(argument: str | None, max_count: int = 5) -> tuple[str | None, int]:
    path: str | None = None
    selected_count = max_count
    if argument and argument.strip():
        try:
            parts = shlex.split(argument)
        except ValueError as error:
            raise ValueError(str(error)) from error
        if len(parts) > 2:
            raise ValueError("expected optional path and optional count.")
        if len(parts) == 1:
            if parts[0].isdigit():
                selected_count = int(parts[0])
            else:
                path = parts[0]
        elif len(parts) == 2:
            path = parts[0]
            if not parts[1].isdigit():
                raise ValueError(f"invalid count: {parts[1]}")
            selected_count = int(parts[1])
    if selected_count < 1:
        raise ValueError("count must be at least 1.")
    if selected_count > 50:
        raise ValueError("count must be at most 50.")
    return path, selected_count


def get_log_report(project_root: str | Path = ".", argument: str | None = None, max_count: int = 5) -> dict[str, object]:
    try:
        path, selected_count = parse_log_request(argument, max_count)
    except ValueError as error:
        return {
            "projectRoot": str(Path(project_root).resolve()),
            "ok": False,
            "path": ".",
            "maxCount": max_count,
            "commits": {"shown": 0, "items": []},
            "log": "",
            "message": f"Usage: /log [path] [count]\nError: {error}",
        }

    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-log", session_dir=root / ".vibeagent" / "sessions" / "local-log")
    observation = execute_action(
        workspace,
        GitLogAction(type="git_log", path=path, max_count=selected_count),
    )
    if observation.kind != "git_log":
        return {
            "projectRoot": str(root),
            "ok": False,
            "path": path or ".",
            "maxCount": selected_count,
            "commits": {"shown": 0, "items": []},
            "log": "",
            "message": f"Unexpected observation: {observation.kind}",
        }
    items = _git_log_items(observation.log)
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "path": observation.path or ".",
        "maxCount": observation.max_count,
        "commits": {"shown": len(items), "items": items},
        "log": observation.log,
        "message": observation.message,
    }


def get_show_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    rev: str | None = None,
    path: str | None = None,
    max_output_chars: int = 12_000,
) -> str:
    return format_show_report_text(
        get_show_report(
            project_root,
            argument,
            rev=rev,
            path=path,
            max_output_chars=max_output_chars,
        )
    )


def parse_show_request(argument: str | None = None, rev: str | None = None, path: str | None = None) -> tuple[str, str | None]:
    if argument and argument.strip():
        if rev is not None or path is not None:
            raise ValueError("show argument cannot be combined with explicit rev or path.")
        try:
            parts = shlex.split(argument)
        except ValueError as error:
            raise ValueError(str(error)) from error
        if len(parts) > 2:
            raise ValueError("expected optional rev and optional path.")
        if not parts:
            return "HEAD", None
        if len(parts) == 1:
            return parts[0], None
        return parts[0], parts[1]

    selected_rev = (rev or "HEAD").strip()
    if not selected_rev:
        raise ValueError("rev must be a non-empty string.")
    selected_path = path.strip() if path else None
    return selected_rev, selected_path


def get_show_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    rev: str | None = None,
    path: str | None = None,
    max_output_chars: int = 12_000,
) -> dict[str, object]:
    if max_output_chars < 1_000:
        return {
            "projectRoot": str(Path(project_root).resolve()),
            "ok": False,
            "rev": rev or "HEAD",
            "path": path or ".",
            "output": _git_output_payload("", truncated=False, max_output_chars=max_output_chars),
            "message": "Usage: /show [rev] [path]\nError: max_output_chars must be at least 1000.",
        }
    if max_output_chars > 50_000:
        return {
            "projectRoot": str(Path(project_root).resolve()),
            "ok": False,
            "rev": rev or "HEAD",
            "path": path or ".",
            "output": _git_output_payload("", truncated=False, max_output_chars=max_output_chars),
            "message": "Usage: /show [rev] [path]\nError: max_output_chars must be at most 50000.",
        }
    try:
        selected_rev, selected_path = parse_show_request(argument, rev, path)
    except ValueError as error:
        return {
            "projectRoot": str(Path(project_root).resolve()),
            "ok": False,
            "rev": rev or "HEAD",
            "path": path or ".",
            "output": _git_output_payload("", truncated=False, max_output_chars=max_output_chars),
            "message": f"Usage: /show [rev] [path]\nError: {error}",
        }

    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-show", session_dir=root / ".vibeagent" / "sessions" / "local-show")
    observation = execute_action(
        workspace,
        GitShowAction(type="git_show", rev=selected_rev, path=selected_path, max_output_chars=max_output_chars),
    )
    if observation.kind != "git_show":
        return {
            "projectRoot": str(root),
            "ok": False,
            "rev": selected_rev,
            "path": selected_path or ".",
            "output": _git_output_payload("", truncated=False, max_output_chars=max_output_chars),
            "message": f"Unexpected observation: {observation.kind}",
        }
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "rev": observation.rev,
        "path": observation.path or ".",
        "output": _git_output_payload(
            observation.output,
            truncated=observation.truncated,
            max_output_chars=observation.max_output_chars,
        ),
        "message": observation.message,
    }

def get_blame_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    line_range: str | None = None,
    max_output_chars: int = 12_000,
) -> str:
    return format_blame_report_text(
        get_blame_report(
            project_root,
            argument,
            line_range=line_range,
            max_output_chars=max_output_chars,
        )
    )


def get_blame_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    line_range: str | None = None,
    max_output_chars: int = 12_000,
) -> dict[str, object]:
    if max_output_chars < 1_000:
        return {
            "projectRoot": str(Path(project_root).resolve()),
            "ok": False,
            "path": "",
            "range": ".",
            "startLine": None,
            "lineCount": None,
            "output": _git_output_payload("", truncated=False, max_output_chars=max_output_chars),
            "message": "Usage: /blame <path> [start[:end]]\nError: max_output_chars must be at least 1000.",
        }
    if max_output_chars > 50_000:
        return {
            "projectRoot": str(Path(project_root).resolve()),
            "ok": False,
            "path": "",
            "range": ".",
            "startLine": None,
            "lineCount": None,
            "output": _git_output_payload("", truncated=False, max_output_chars=max_output_chars),
            "message": "Usage: /blame <path> [start[:end]]\nError: max_output_chars must be at most 50000.",
        }
    if argument is None or not argument.strip():
        return {
            "projectRoot": str(Path(project_root).resolve()),
            "ok": False,
            "path": "",
            "range": ".",
            "startLine": None,
            "lineCount": None,
            "output": _git_output_payload("", truncated=False, max_output_chars=max_output_chars),
            "message": "Usage: /blame <path> [start[:end]]",
        }
    try:
        path, start_line, line_count, range_label = parse_read_request(argument, line_range)
    except ValueError as error:
        return {
            "projectRoot": str(Path(project_root).resolve()),
            "ok": False,
            "path": argument,
            "range": line_range or ".",
            "startLine": None,
            "lineCount": None,
            "output": _git_output_payload("", truncated=False, max_output_chars=max_output_chars),
            "message": f"Usage: /blame <path> [start[:end]]\nError: {error}",
        }

    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-blame", session_dir=root / ".vibeagent" / "sessions" / "local-blame")
    observation = execute_action(
        workspace,
        GitBlameAction(
            type="git_blame",
            path=path,
            start_line=start_line,
            line_count=line_count,
            max_output_chars=max_output_chars,
        ),
    )
    if observation.kind != "git_blame":
        return {
            "projectRoot": str(root),
            "ok": False,
            "path": path,
            "range": range_label or ".",
            "startLine": start_line,
            "lineCount": line_count,
            "output": _git_output_payload("", truncated=False, max_output_chars=max_output_chars),
            "message": f"Unexpected observation: {observation.kind}",
        }
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "path": observation.path,
        "range": range_label or ".",
        "startLine": observation.start_line,
        "lineCount": observation.line_count,
        "output": _git_output_payload(
            observation.blame,
            truncated=observation.truncated,
            max_output_chars=observation.max_output_chars,
        ),
        "message": observation.message,
    }
