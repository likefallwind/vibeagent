from __future__ import annotations

from .types import (
    GitBranchInfo,
    GitBranchesAction,
    GitBranchesObservation,
    GitChangeFile,
    GitChangesAction,
    GitChangesObservation,
    GitConflictMarker,
    GitConflictStatus,
    GitConflictsAction,
    GitConflictsObservation,
    GitInfoAction,
    GitInfoObservation,
    GitRemote,
    GitStatusAction,
    GitStatusObservation,
    Observation,
)
from .workspace import (
    RunWorkspace,
    read_git_branches,
    read_git_changes,
    read_git_conflicts,
    read_git_info,
    read_git_status,
)


def execute_git_info_action(workspace: RunWorkspace, action: object) -> Observation | None:
    if isinstance(action, GitStatusAction):
        result = read_git_status(workspace)
        message = "Read git status." if result.ok else result.stderr or "git status failed."
        return GitStatusObservation(
            kind="git_status",
            ok=result.ok,
            status=result.stdout,
            message=message,
        )

    if isinstance(action, GitConflictsAction):
        try:
            conflicts = read_git_conflicts(
                workspace,
                action.path,
                max_markers=action.max_markers,
                max_files=action.max_files,
            )
            unmerged = [GitConflictStatus(**item) for item in conflicts["unmerged"]]
            markers = [GitConflictMarker(**item) for item in conflicts["markers"]]
            return GitConflictsObservation(
                kind="git_conflicts",
                ok=bool(conflicts["ok"]),
                path=str(conflicts["path"]),
                unmerged=unmerged,
                unmerged_total=int(conflicts["unmerged_total"]),
                markers=markers,
                markers_total=int(conflicts["markers_total"]),
                scanned_files=int(conflicts["scanned_files"]),
                total_files=int(conflicts["total_files"]),
                truncated=bool(conflicts["truncated"]),
                message=str(conflicts["message"]),
            )
        except ValueError as error:
            return GitConflictsObservation(
                kind="git_conflicts",
                ok=False,
                path=action.path or ".",
                unmerged=[],
                unmerged_total=0,
                markers=[],
                markers_total=0,
                scanned_files=0,
                total_files=0,
                truncated=False,
                message=str(error),
            )

    if isinstance(action, GitInfoAction):
        info = read_git_info(workspace)
        remotes = [GitRemote(**item) for item in info["remotes"]]
        return GitInfoObservation(
            kind="git_info",
            ok=bool(info["ok"]),
            is_git_repo=bool(info["is_git_repo"]),
            branch=str(info["branch"]),
            head=str(info["head"]),
            upstream=str(info["upstream"]),
            ahead=int(info["ahead"]),
            behind=int(info["behind"]),
            remotes=remotes,
            status=str(info["status"]),
            message=str(info["message"]),
        )

    if isinstance(action, GitChangesAction):
        changes = read_git_changes(workspace)
        files = [GitChangeFile(**item) for item in changes["files"]]
        return GitChangesObservation(
            kind="git_changes",
            ok=bool(changes["ok"]),
            files=files,
            status=str(changes["status"]),
            message=str(changes["message"]),
        )

    if isinstance(action, GitBranchesAction):
        try:
            result = read_git_branches(workspace, max_branches=action.max_branches)
        except ValueError as error:
            result = {
                "ok": False,
                "current": "",
                "branches": [],
                "total": 0,
                "truncated": False,
                "status": "",
                "message": str(error),
            }
        branches = [GitBranchInfo(**item) for item in result["branches"]]
        return GitBranchesObservation(
            kind="git_branches",
            ok=bool(result["ok"]),
            current=str(result["current"]),
            branches=branches,
            total=int(result["total"]),
            truncated=bool(result["truncated"]),
            status=str(result["status"]),
            message=str(result["message"]),
        )

    return None
