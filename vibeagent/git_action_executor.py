from __future__ import annotations

from .process_runtime import truncate_command_output
from .types import (
    CheckGitCommitAction,
    CheckGitCommitObservation,
    CheckGitFetchAction,
    CheckGitFetchObservation,
    CheckGitPullAction,
    CheckGitPullObservation,
    CheckGitPushAction,
    CheckGitPushObservation,
    CheckGitRestoreAction,
    CheckGitRestoreObservation,
    CheckGitStashAction,
    CheckGitStashApplyAction,
    CheckGitStashApplyObservation,
    CheckGitStashDropAction,
    CheckGitStashDropObservation,
    CheckGitStashObservation,
    CheckGitStageAction,
    CheckGitStageObservation,
    CheckGitSwitchAction,
    CheckGitSwitchObservation,
    CheckGitUnstageAction,
    CheckGitUnstageObservation,
    GitBlameAction,
    GitBlameObservation,
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
    GitCommitAction,
    GitCommitObservation,
    GitDiffAction,
    GitDiffContext,
    GitDiffContextsAction,
    GitDiffContextsObservation,
    GitDiffHunk,
    GitDiffHunksAction,
    GitDiffHunksObservation,
    GitDiffObservation,
    GitFetchAction,
    GitFetchObservation,
    GitInfoAction,
    GitInfoObservation,
    GitLogAction,
    GitLogObservation,
    GitPullAction,
    GitPullObservation,
    GitPushAction,
    GitPushObservation,
    GitRemote,
    GitRestoreAction,
    GitRestoreObservation,
    GitShowAction,
    GitShowObservation,
    GitStageAction,
    GitStageObservation,
    GitStashAction,
    GitStashApplyAction,
    GitStashApplyObservation,
    GitStashDropAction,
    GitStashDropObservation,
    GitStashEntry,
    GitStashesAction,
    GitStashesObservation,
    GitStashObservation,
    GitStatusAction,
    GitStatusObservation,
    GitSwitchAction,
    GitSwitchObservation,
    GitUnstageAction,
    GitUnstageObservation,
    Observation,
    ReadFileContextResult,
)
from .workspace import (
    RunWorkspace,
    apply_git_stash,
    commit_staged_changes,
    drop_git_stash,
    fetch_git_remote,
    pull_git_upstream,
    push_git_upstream,
    read_git_blame,
    read_git_branches,
    read_git_changes,
    read_git_conflicts,
    read_git_diff,
    read_git_diff_hunks,
    read_git_info,
    read_git_log,
    read_git_show,
    read_git_stashes,
    read_git_status,
    read_project_file_context_result,
    restore_git_paths,
    preview_apply_git_stash,
    preview_commit_staged_changes,
    preview_drop_git_stash,
    preview_fetch_git_remote,
    preview_pull_git_upstream,
    preview_push_git_upstream,
    preview_restore_git_paths,
    preview_stage_git_paths,
    preview_stash_git_changes,
    preview_switch_git_branch,
    preview_unstage_git_paths,
    stage_git_paths,
    stash_git_changes,
    switch_git_branch,
    unstage_git_paths,
)


def execute_git_action(workspace: RunWorkspace, action: object) -> Observation | None:
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
            result = {"ok": False, "stash_ref": action.stash_ref, "worktree_clean": False, "patch": "", "status": "", "message": str(error)}
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
            result = {"ok": False, "stash_ref": action.stash_ref, "patch": "", "summary": "", "remaining_total": 0, "message": str(error)}
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
        )

    if isinstance(action, GitDiffAction):
        try:
            result = read_git_diff(workspace, action.path, action.staged)
        except ValueError as error:
            return GitDiffObservation(
                kind="git_diff",
                ok=False,
                diff="",
                path=action.path,
                staged=action.staged,
                truncated=False,
                max_output_chars=action.max_output_chars,
                message=str(error),
            )
        diff, truncated = truncate_command_output(result.stdout, action.max_output_chars)
        message = "Read git diff." if result.ok else result.stderr or "git diff failed."
        return GitDiffObservation(
            kind="git_diff",
            ok=result.ok,
            diff=diff,
            path=action.path,
            staged=action.staged,
            truncated=truncated,
            max_output_chars=action.max_output_chars,
            message=message,
        )

    if isinstance(action, GitDiffHunksAction):
        try:
            summary = read_git_diff_hunks(
                workspace,
                action.path,
                action.staged,
                max_hunks=action.max_hunks,
                max_lines_per_hunk=action.max_lines_per_hunk,
            )
            hunks = [GitDiffHunk(**item) for item in summary["hunks"]]
            return GitDiffHunksObservation(
                kind="git_diff_hunks",
                ok=bool(summary["ok"]),
                hunks=hunks,
                total_hunks=int(summary["total_hunks"]),
                truncated=bool(summary["truncated"]),
                path=action.path,
                staged=action.staged,
                message=str(summary["message"]),
            )
        except ValueError as error:
            return GitDiffHunksObservation(
                kind="git_diff_hunks",
                ok=False,
                hunks=[],
                total_hunks=0,
                truncated=False,
                path=action.path,
                staged=action.staged,
                message=str(error),
            )

    if isinstance(action, GitDiffContextsAction):
        try:
            summary = read_git_diff_hunks(
                workspace,
                action.path,
                action.staged,
                max_hunks=action.max_hunks,
                max_lines_per_hunk=1,
            )
            contexts: list[GitDiffContext] = []
            for item in summary["hunks"]:
                hunk = GitDiffHunk(**item)
                try:
                    result = read_project_file_context_result(
                        workspace,
                        hunk.file,
                        line=max(1, hunk.new_start),
                        context_lines=action.context_lines,
                        max_bytes=action.max_bytes_per_context,
                    )
                    context = ReadFileContextResult(
                        path=hunk.file,
                        line=int(result["line"]),
                        context_lines=int(result["context_lines"]),
                        ok=True,
                        content=str(result["content"]),
                        message=f"Read {hunk.file} around diff hunk line {hunk.new_start}.",
                        start_line=int(result["start_line"]),
                        end_line=int(result["end_line"]),
                        line_count=int(result["line_count"]),
                        total_lines=int(result["total_lines"]),
                        target_line_exists=bool(result["target_line_exists"]),
                        truncated=bool(result["truncated"]),
                        max_bytes=int(result["max_bytes"]),
                    )
                except ValueError as error:
                    context = ReadFileContextResult(
                        path=hunk.file,
                        line=max(1, hunk.new_start),
                        context_lines=action.context_lines,
                        ok=False,
                        content="",
                        message=str(error),
                        max_bytes=action.max_bytes_per_context,
                    )
                contexts.append(GitDiffContext(hunk=hunk, context=context))
            return GitDiffContextsObservation(
                kind="git_diff_contexts",
                ok=bool(summary["ok"]),
                contexts=contexts,
                total_hunks=int(summary["total_hunks"]),
                truncated=bool(summary["truncated"]),
                path=action.path,
                staged=action.staged,
                context_lines=action.context_lines,
                message=str(summary["message"]),
            )
        except ValueError as error:
            return GitDiffContextsObservation(
                kind="git_diff_contexts",
                ok=False,
                contexts=[],
                total_hunks=0,
                truncated=False,
                path=action.path,
                staged=action.staged,
                context_lines=action.context_lines,
                message=str(error),
            )

    if isinstance(action, GitLogAction):
        try:
            result = read_git_log(workspace, action.max_count, action.path)
        except ValueError as error:
            return GitLogObservation(
                kind="git_log",
                ok=False,
                log="",
                max_count=action.max_count,
                path=action.path,
                message=str(error),
            )
        message = "Read git log." if result.ok else result.stderr or "git log failed."
        return GitLogObservation(
            kind="git_log",
            ok=result.ok,
            log=result.stdout,
            max_count=action.max_count,
            path=action.path,
            message=message,
        )

    if isinstance(action, GitShowAction):
        try:
            result = read_git_show(workspace, action.rev, action.path)
        except ValueError as error:
            return GitShowObservation(
                kind="git_show",
                ok=False,
                output="",
                rev=action.rev,
                path=action.path,
                truncated=False,
                max_output_chars=action.max_output_chars,
                message=str(error),
            )
        output, truncated = truncate_command_output(result.stdout, action.max_output_chars)
        message = "Read git show." if result.ok else result.stderr or "git show failed."
        return GitShowObservation(
            kind="git_show",
            ok=result.ok,
            output=output,
            rev=action.rev,
            path=action.path,
            truncated=truncated,
            max_output_chars=action.max_output_chars,
            message=message,
        )

    if isinstance(action, GitBlameAction):
        try:
            result = read_git_blame(workspace, action.path, action.start_line, action.line_count)
        except ValueError as error:
            return GitBlameObservation(
                kind="git_blame",
                ok=False,
                blame="",
                path=action.path,
                start_line=action.start_line,
                line_count=action.line_count,
                truncated=False,
                max_output_chars=action.max_output_chars,
                message=str(error),
            )
        blame, truncated = truncate_command_output(result.stdout, action.max_output_chars)
        message = "Read git blame." if result.ok else result.stderr or "git blame failed."
        return GitBlameObservation(
            kind="git_blame",
            ok=result.ok,
            blame=blame,
            path=action.path,
            start_line=action.start_line,
            line_count=action.line_count,
            truncated=truncated,
            max_output_chars=action.max_output_chars,
            message=message,
        )

    return None
