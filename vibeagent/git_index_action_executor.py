from __future__ import annotations

from .types import (
    CheckGitRestoreAction,
    CheckGitRestoreObservation,
    CheckGitStageAction,
    CheckGitStageObservation,
    CheckGitSwitchAction,
    CheckGitSwitchObservation,
    CheckGitUnstageAction,
    CheckGitUnstageObservation,
    GitRestoreAction,
    GitRestoreObservation,
    GitStageAction,
    GitStageObservation,
    GitSwitchAction,
    GitSwitchObservation,
    GitUnstageAction,
    GitUnstageObservation,
    Observation,
)
from .workspace import (
    RunWorkspace,
    preview_restore_git_paths,
    preview_stage_git_paths,
    preview_switch_git_branch,
    preview_unstage_git_paths,
    restore_git_paths,
    stage_git_paths,
    switch_git_branch,
    unstage_git_paths,
)


def execute_git_index_action(workspace: RunWorkspace, action: object) -> Observation | None:
    if isinstance(action, CheckGitSwitchAction):
        try:
            result = preview_switch_git_branch(workspace, action.branch, create=action.create)
        except ValueError as error:
            result = {
                "ok": False,
                "branch": action.branch,
                "create": action.create,
                "current_before": "",
                "branch_exists": False,
                "worktree_clean": False,
                "status": "",
                "message": str(error),
            }
        return CheckGitSwitchObservation(
            kind="check_git_switch",
            ok=bool(result["ok"]),
            branch=str(result["branch"]),
            create=bool(result["create"]),
            current_before=str(result["current_before"]),
            branch_exists=bool(result["branch_exists"]),
            worktree_clean=bool(result["worktree_clean"]),
            status=str(result["status"]),
            message=str(result["message"]),
        )

    if isinstance(action, GitSwitchAction):
        try:
            result = switch_git_branch(workspace, action.branch, create=action.create)
        except ValueError as error:
            result = {
                "ok": False,
                "branch": action.branch,
                "create": action.create,
                "current_before": "",
                "current_after": "",
                "status": "",
                "message": str(error),
            }
        return GitSwitchObservation(
            kind="git_switch",
            ok=bool(result["ok"]),
            branch=str(result["branch"]),
            create=bool(result["create"]),
            current_before=str(result["current_before"]),
            current_after=str(result["current_after"]),
            status=str(result["status"]),
            message=str(result["message"]),
        )

    if isinstance(action, CheckGitStageAction):
        try:
            result = preview_stage_git_paths(workspace, action.paths)
        except ValueError as error:
            result = {"ok": False, "paths": action.paths, "status": "", "message": str(error)}
        return CheckGitStageObservation(
            kind="check_git_stage",
            ok=bool(result["ok"]),
            paths=list(result["paths"]),
            status=str(result["status"]),
            message=str(result["message"]),
        )

    if isinstance(action, GitStageAction):
        try:
            result = stage_git_paths(workspace, action.paths)
        except ValueError as error:
            result = {"ok": False, "paths": action.paths, "status": "", "message": str(error)}
        return GitStageObservation(
            kind="git_stage",
            ok=bool(result["ok"]),
            paths=list(result["paths"]),
            status=str(result["status"]),
            message=str(result["message"]),
        )

    if isinstance(action, CheckGitUnstageAction):
        try:
            result = preview_unstage_git_paths(workspace, action.paths)
        except ValueError as error:
            result = {"ok": False, "paths": action.paths, "status": "", "message": str(error)}
        return CheckGitUnstageObservation(
            kind="check_git_unstage",
            ok=bool(result["ok"]),
            paths=list(result["paths"]),
            status=str(result["status"]),
            message=str(result["message"]),
        )

    if isinstance(action, GitUnstageAction):
        try:
            result = unstage_git_paths(workspace, action.paths)
        except ValueError as error:
            result = {"ok": False, "paths": action.paths, "status": "", "message": str(error)}
        return GitUnstageObservation(
            kind="git_unstage",
            ok=bool(result["ok"]),
            paths=list(result["paths"]),
            status=str(result["status"]),
            message=str(result["message"]),
        )

    if isinstance(action, CheckGitRestoreAction):
        try:
            result = preview_restore_git_paths(workspace, action.paths)
        except ValueError as error:
            result = {"ok": False, "paths": action.paths, "diff": "", "status": "", "message": str(error)}
        return CheckGitRestoreObservation(
            kind="check_git_restore",
            ok=bool(result["ok"]),
            paths=list(result["paths"]),
            diff=str(result["diff"]),
            status=str(result["status"]),
            message=str(result["message"]),
        )

    if isinstance(action, GitRestoreAction):
        try:
            result = restore_git_paths(workspace, action.paths)
        except ValueError as error:
            result = {"ok": False, "paths": action.paths, "diff": "", "status": "", "message": str(error)}
        return GitRestoreObservation(
            kind="git_restore",
            ok=bool(result["ok"]),
            paths=list(result["paths"]),
            diff=str(result["diff"]),
            status=str(result["status"]),
            message=str(result["message"]),
        )

    return None
