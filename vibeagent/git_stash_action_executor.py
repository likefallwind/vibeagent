from __future__ import annotations

from .types import (
    CheckGitCommitAction,
    CheckGitCommitObservation,
    CheckGitStashAction,
    CheckGitStashApplyAction,
    CheckGitStashApplyObservation,
    CheckGitStashDropAction,
    CheckGitStashDropObservation,
    CheckGitStashObservation,
    GitCommitAction,
    GitCommitObservation,
    GitStashAction,
    GitStashApplyAction,
    GitStashApplyObservation,
    GitStashDropAction,
    GitStashDropObservation,
    GitStashEntry,
    GitStashesAction,
    GitStashesObservation,
    GitStashObservation,
    Observation,
)
from .workspace import (
    RunWorkspace,
    apply_git_stash,
    commit_staged_changes,
    drop_git_stash,
    preview_apply_git_stash,
    preview_commit_staged_changes,
    preview_drop_git_stash,
    preview_stash_git_changes,
    read_git_stashes,
    stash_git_changes,
)


def execute_git_stash_action(workspace: RunWorkspace, action: object) -> Observation | None:
    if isinstance(action, GitStashesAction):
        try:
            result = read_git_stashes(workspace, max_entries=action.max_entries)
        except ValueError as error:
            result = {"ok": False, "entries": [], "total": 0, "truncated": False, "message": str(error)}
        entries = [GitStashEntry(**item) for item in result["entries"]]
        return GitStashesObservation(
            kind="git_stashes",
            ok=bool(result["ok"]),
            entries=entries,
            total=int(result["total"]),
            truncated=bool(result["truncated"]),
            message=str(result["message"]),
        )

    if isinstance(action, CheckGitStashAction):
        try:
            result = preview_stash_git_changes(workspace, action.message, include_untracked=action.include_untracked)
        except ValueError as error:
            result = {
                "ok": False,
                "message_text": action.message or "",
                "include_untracked": action.include_untracked,
                "status": "",
                "diff": "",
                "message": str(error),
            }
        return CheckGitStashObservation(
            kind="check_git_stash",
            ok=bool(result["ok"]),
            message_text=str(result["message_text"]),
            include_untracked=bool(result["include_untracked"]),
            status=str(result["status"]),
            diff=str(result["diff"]),
            message=str(result["message"]),
        )

    if isinstance(action, GitStashAction):
        try:
            result = stash_git_changes(workspace, action.message, include_untracked=action.include_untracked)
        except ValueError as error:
            result = {
                "ok": False,
                "message_text": action.message or "",
                "include_untracked": action.include_untracked,
                "stash_ref": "",
                "status": "",
                "diff": "",
                "message": str(error),
            }
        return GitStashObservation(
            kind="git_stash",
            ok=bool(result["ok"]),
            message_text=str(result["message_text"]),
            include_untracked=bool(result["include_untracked"]),
            stash_ref=str(result["stash_ref"]),
            status=str(result["status"]),
            diff=str(result["diff"]),
            message=str(result["message"]),
        )

    if isinstance(action, CheckGitStashApplyAction):
        try:
            result = preview_apply_git_stash(workspace, action.stash_ref)
        except ValueError as error:
            result = {
                "ok": False,
                "stash_ref": action.stash_ref,
                "worktree_clean": False,
                "patch": "",
                "status": "",
                "message": str(error),
            }
        return CheckGitStashApplyObservation(
            kind="check_git_stash_apply",
            ok=bool(result["ok"]),
            stash_ref=str(result["stash_ref"]),
            worktree_clean=bool(result["worktree_clean"]),
            patch=str(result["patch"]),
            status=str(result["status"]),
            message=str(result["message"]),
        )

    if isinstance(action, GitStashApplyAction):
        try:
            result = apply_git_stash(workspace, action.stash_ref)
        except ValueError as error:
            result = {"ok": False, "stash_ref": action.stash_ref, "patch": "", "status": "", "message": str(error)}
        return GitStashApplyObservation(
            kind="git_stash_apply",
            ok=bool(result["ok"]),
            stash_ref=str(result["stash_ref"]),
            patch=str(result["patch"]),
            status=str(result["status"]),
            message=str(result["message"]),
        )

    if isinstance(action, CheckGitStashDropAction):
        try:
            result = preview_drop_git_stash(workspace, action.stash_ref)
        except ValueError as error:
            result = {"ok": False, "stash_ref": action.stash_ref, "patch": "", "summary": "", "message": str(error)}
        return CheckGitStashDropObservation(
            kind="check_git_stash_drop",
            ok=bool(result["ok"]),
            stash_ref=str(result["stash_ref"]),
            patch=str(result["patch"]),
            summary=str(result["summary"]),
            message=str(result["message"]),
        )

    if isinstance(action, GitStashDropAction):
        try:
            result = drop_git_stash(workspace, action.stash_ref)
        except ValueError as error:
            result = {
                "ok": False,
                "stash_ref": action.stash_ref,
                "patch": "",
                "summary": "",
                "remaining_total": 0,
                "message": str(error),
            }
        return GitStashDropObservation(
            kind="git_stash_drop",
            ok=bool(result["ok"]),
            stash_ref=str(result["stash_ref"]),
            patch=str(result["patch"]),
            summary=str(result["summary"]),
            remaining_total=int(result["remaining_total"]),
            message=str(result["message"]),
        )

    if isinstance(action, CheckGitCommitAction):
        try:
            result = preview_commit_staged_changes(workspace, action.message)
        except ValueError as error:
            result = {"ok": False, "head_before": "", "head_after": "", "status": "", "message": str(error)}
        return CheckGitCommitObservation(
            kind="check_git_commit",
            ok=bool(result["ok"]),
            head_before=str(result["head_before"]),
            head_after=str(result["head_after"]),
            status=str(result["status"]),
            message=str(result["message"]),
        )

    if isinstance(action, GitCommitAction):
        try:
            result = commit_staged_changes(workspace, action.message)
        except ValueError as error:
            result = {"ok": False, "head_before": "", "head_after": "", "status": "", "message": str(error)}
        return GitCommitObservation(
            kind="git_commit",
            ok=bool(result["ok"]),
            head_before=str(result["head_before"]),
            head_after=str(result["head_after"]),
            status=str(result["status"]),
            message=str(result["message"]),
            message_text=action.message,
        )

    return None
