from __future__ import annotations

from .types import (
    CheckGitFetchAction,
    CheckGitFetchObservation,
    CheckGitPullAction,
    CheckGitPullObservation,
    CheckGitPushAction,
    CheckGitPushObservation,
    GitFetchAction,
    GitFetchObservation,
    GitPullAction,
    GitPullObservation,
    GitPushAction,
    GitPushObservation,
    Observation,
)
from .workspace import (
    RunWorkspace,
    fetch_git_remote,
    preview_fetch_git_remote,
    preview_pull_git_upstream,
    preview_push_git_upstream,
    pull_git_upstream,
    push_git_upstream,
)


def execute_git_remote_action(workspace: RunWorkspace, action: object) -> Observation | None:
    if isinstance(action, CheckGitFetchAction):
        try:
            result = preview_fetch_git_remote(workspace, action.remote)
        except ValueError as error:
            result = {
                "ok": False,
                "remote": action.remote or "",
                "remote_url": "",
                "branch": "",
                "upstream": "",
                "ahead": 0,
                "behind": 0,
                "message": str(error),
            }
        return CheckGitFetchObservation(
            kind="check_git_fetch",
            ok=bool(result["ok"]),
            remote=str(result["remote"]),
            remote_url=str(result["remote_url"]),
            branch=str(result["branch"]),
            upstream=str(result["upstream"]),
            ahead=int(result["ahead"]),
            behind=int(result["behind"]),
            message=str(result["message"]),
        )

    if isinstance(action, GitFetchAction):
        try:
            result = fetch_git_remote(workspace, action.remote)
        except ValueError as error:
            result = {
                "ok": False,
                "remote": action.remote or "",
                "remote_url": "",
                "branch": "",
                "upstream": "",
                "ahead_before": 0,
                "behind_before": 0,
                "ahead_after": 0,
                "behind_after": 0,
                "message": str(error),
            }
        return GitFetchObservation(
            kind="git_fetch",
            ok=bool(result["ok"]),
            remote=str(result["remote"]),
            remote_url=str(result["remote_url"]),
            branch=str(result["branch"]),
            upstream=str(result["upstream"]),
            ahead_before=int(result["ahead_before"]),
            behind_before=int(result["behind_before"]),
            ahead_after=int(result["ahead_after"]),
            behind_after=int(result["behind_after"]),
            message=str(result["message"]),
        )

    if isinstance(action, CheckGitPullAction):
        try:
            result = preview_pull_git_upstream(workspace)
        except ValueError as error:
            result = {
                "ok": False,
                "remote": "",
                "branch": "",
                "current": "",
                "upstream": "",
                "ahead": 0,
                "behind": 0,
                "worktree_clean": False,
                "status": "",
                "message": str(error),
            }
        return CheckGitPullObservation(
            kind="check_git_pull",
            ok=bool(result["ok"]),
            remote=str(result["remote"]),
            branch=str(result["branch"]),
            current=str(result["current"]),
            upstream=str(result["upstream"]),
            ahead=int(result["ahead"]),
            behind=int(result["behind"]),
            worktree_clean=bool(result["worktree_clean"]),
            status=str(result["status"]),
            message=str(result["message"]),
        )

    if isinstance(action, GitPullAction):
        try:
            result = pull_git_upstream(workspace)
        except ValueError as error:
            result = {
                "ok": False,
                "remote": "",
                "branch": "",
                "current_before": "",
                "current_after": "",
                "upstream": "",
                "ahead_before": 0,
                "behind_before": 0,
                "ahead_after": 0,
                "behind_after": 0,
                "status": "",
                "message": str(error),
            }
        return GitPullObservation(
            kind="git_pull",
            ok=bool(result["ok"]),
            remote=str(result["remote"]),
            branch=str(result["branch"]),
            current_before=str(result["current_before"]),
            current_after=str(result["current_after"]),
            upstream=str(result["upstream"]),
            ahead_before=int(result["ahead_before"]),
            behind_before=int(result["behind_before"]),
            ahead_after=int(result["ahead_after"]),
            behind_after=int(result["behind_after"]),
            status=str(result["status"]),
            message=str(result["message"]),
        )

    if isinstance(action, CheckGitPushAction):
        try:
            result = preview_push_git_upstream(workspace)
        except ValueError as error:
            result = {
                "ok": False,
                "remote": "",
                "branch": "",
                "current": "",
                "upstream": "",
                "ahead": 0,
                "behind": 0,
                "worktree_clean": False,
                "status": "",
                "message": str(error),
            }
        return CheckGitPushObservation(
            kind="check_git_push",
            ok=bool(result["ok"]),
            remote=str(result["remote"]),
            branch=str(result["branch"]),
            current=str(result["current"]),
            upstream=str(result["upstream"]),
            ahead=int(result["ahead"]),
            behind=int(result["behind"]),
            worktree_clean=bool(result["worktree_clean"]),
            status=str(result["status"]),
            message=str(result["message"]),
        )

    if isinstance(action, GitPushAction):
        try:
            result = push_git_upstream(workspace)
        except ValueError as error:
            result = {
                "ok": False,
                "remote": "",
                "branch": "",
                "current": "",
                "upstream": "",
                "ahead_before": 0,
                "behind_before": 0,
                "status": "",
                "message": str(error),
            }
        return GitPushObservation(
            kind="git_push",
            ok=bool(result["ok"]),
            remote=str(result["remote"]),
            branch=str(result["branch"]),
            current=str(result["current"]),
            upstream=str(result["upstream"]),
            ahead_before=int(result["ahead_before"]),
            behind_before=int(result["behind_before"]),
            status=str(result["status"]),
            message=str(result["message"]),
        )

    return None
