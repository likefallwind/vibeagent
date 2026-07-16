from __future__ import annotations

from pathlib import Path

from .actions import execute_action
from .command_parsing import parse_optional_single_path_argument
from .git_history_commands import (
    _git_output_payload,
    get_blame_report,
    get_blame_text,
    get_log_report,
    get_log_text,
    get_show_report,
    get_show_text,
    parse_log_request,
    parse_show_request,
)
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
from .local_command_workspace import local_command_workspace
from .types import GitBranchesAction, GitConflictsAction, GitInfoAction, GitStatusAction


def _split_nonempty_lines(value: str) -> list[str]:
    return [line for line in value.splitlines() if line.strip()]


def _git_status_payload(status: str) -> dict[str, object]:
    lines = _split_nonempty_lines(status)
    return {"text": status, "lines": lines, "count": len(lines)}


def get_git_status_report(project_root: str | Path = ".") -> dict[str, object]:
    root = Path(project_root).resolve()
    workspace = local_command_workspace(root, "local-git-status")
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

    workspace = local_command_workspace(root, "local-git-conflicts")
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
    workspace = local_command_workspace(root, "local-git-info")
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
    workspace = local_command_workspace(root, "local-branches")
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
