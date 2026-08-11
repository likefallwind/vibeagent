from __future__ import annotations

from .types import Observation


EXTENDED_GIT_NEXT_ACTION_KINDS = {
    "git_conflicts",
    "git_info",
    "git_branches",
    "check_git_fetch",
    "git_fetch",
    "check_git_pull",
    "git_pull",
    "check_git_push",
    "git_push",
    "check_github_pr_create",
    "github_pr_create",
    "check_git_restore",
    "git_restore",
    "git_stashes",
    "check_git_stash",
    "git_stash",
    "check_git_stash_apply",
    "git_stash_apply",
    "check_git_stash_drop",
    "git_stash_drop",
    "check_git_switch",
    "git_switch",
    "git_log",
    "git_show",
    "git_blame",
    "review_changes",
}


def _format_next_action_items(items: list[str], max_items: int = 3) -> str:
    shown = items[:max_items]
    suffix = "" if len(items) <= max_items else f"; +{len(items) - max_items} more"
    return "; ".join(shown) + suffix


def _branch_labels(values: object) -> list[str]:
    labels: list[str] = []
    if not isinstance(values, list):
        return labels
    for value in values:
        name = str(getattr(value, "name", "") or "").strip()
        if name:
            labels.append(f"{name} (current)" if getattr(value, "current", False) else name)
    return labels


def _paths_label(values: object) -> str:
    if not isinstance(values, list):
        return "the selected path(s)"
    paths = [str(value).strip() for value in values if str(value).strip()]
    return _format_next_action_items(paths) if paths else "the selected path(s)"


def _git_conflicts_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        return f"{base} Git conflicts could not be inspected. Use git_status or git_info to recover repository state."

    unmerged = int(getattr(latest, "unmerged_total", 0) or 0)
    markers = int(getattr(latest, "markers_total", 0) or 0)
    if unmerged or markers:
        return (
            f"{base} Git conflict inspection found {unmerged} unmerged path(s) and {markers} conflict marker(s). "
            "Use read_file_context or git_diff_contexts on the conflicted files, resolve them, then rerun git_conflicts."
        )
    return f"{base} Git conflict inspection found no conflicts. Continue with the requested git or coding workflow."


def _git_info_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False) or not getattr(latest, "is_git_repo", True):
        return f"{base} Git info is unavailable or this is not a git repository. Continue without git actions unless repository setup is required."

    ahead = int(getattr(latest, "ahead", 0) or 0)
    behind = int(getattr(latest, "behind", 0) or 0)
    status = str(getattr(latest, "status", "") or "").strip()
    if status:
        return (
            f"{base} Git info shows branch {getattr(latest, 'branch', '')} with worktree changes. "
            "Use git_changes, git_diff, or review_changes before staging or committing."
        )
    if behind:
        return (
            f"{base} Git info shows the branch is behind by {behind} commit(s)"
            f"{' and ahead by ' + str(ahead) + ' commit(s)' if ahead else ''}. "
            "Use check_git_pull or check_git_fetch before syncing, unless the task should stay local."
        )
    if ahead:
        return (
            f"{base} Git info shows the branch is ahead by {ahead} commit(s). "
            "Use check_git_push only if pushing was requested, or continue local work."
        )
    return f"{base} Git info shows a clean synchronized branch. Continue the requested work or answer directly if complete."


def _git_branches_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        return f"{base} Git branches could not be read. Use git_info or git_status to recover repository state."

    branches = _branch_labels(getattr(latest, "branches", []))
    if branches:
        return (
            f"{base} Git branches were listed: {_format_next_action_items(branches)}. "
            "Use check_git_switch before switching or creating a branch, or continue on the current branch."
        )
    return f"{base} No git branches were listed. Use git_info or git_status before choosing another git action."


def _check_git_fetch_next_action_instruction(base: str, latest: Observation) -> str:
    if getattr(latest, "ok", False):
        return (
            f"{base} Git fetch dry-run succeeded for {getattr(latest, 'remote', 'remote')}. "
            "Run git_fetch only if refreshing remote state is needed."
        )
    return f"{base} Git fetch dry-run failed. Inspect the remote, branch, or network error before fetching."


def _git_fetch_next_action_instruction(base: str, latest: Observation) -> str:
    if getattr(latest, "ok", False):
        behind = int(getattr(latest, "behind_after", 0) or 0)
        if behind:
            return f"{base} Git fetch completed and the branch is behind by {behind} commit(s). Use check_git_pull before pulling."
        return f"{base} Git fetch completed. Continue the requested work, inspect git_info, or answer directly if complete."
    return f"{base} Git fetch failed. Inspect the fetch error, remote, or network state before retrying."


def _check_git_pull_next_action_instruction(base: str, latest: Observation) -> str:
    if getattr(latest, "ok", False):
        return f"{base} Git pull dry-run succeeded. Run git_pull only if syncing the branch is intended."
    if not getattr(latest, "worktree_clean", True):
        return f"{base} Git pull dry-run failed because the worktree is not clean. Inspect git_status and commit, stash, or restore first."
    return f"{base} Git pull dry-run failed. Inspect branch/upstream state before pulling."


def _git_pull_next_action_instruction(base: str, latest: Observation) -> str:
    if getattr(latest, "ok", False):
        return f"{base} Git pull completed. Use git_status and relevant verification before continuing local edits or answering."
    return f"{base} Git pull failed. Inspect conflicts, status, or the pull error before retrying."


def _check_git_push_next_action_instruction(base: str, latest: Observation) -> str:
    if getattr(latest, "ok", False):
        return f"{base} Git push dry-run succeeded. Run git_push only if publishing was explicitly requested."
    if not getattr(latest, "worktree_clean", True):
        return f"{base} Git push dry-run failed because the worktree is not clean. Commit or clean local changes before pushing."
    behind = int(getattr(latest, "behind", 0) or 0)
    if behind:
        return f"{base} Git push dry-run found the branch behind by {behind} commit(s). Fetch or pull before pushing."
    return f"{base} Git push dry-run failed. Inspect upstream, branch, or remote state before pushing."


def _git_push_next_action_instruction(base: str, latest: Observation) -> str:
    if getattr(latest, "ok", False):
        return f"{base} Git push completed. Use git_status or answer directly with the published branch details."
    return f"{base} Git push failed. Inspect the remote error and branch state before trying again."


def _check_git_restore_next_action_instruction(base: str, latest: Observation) -> str:
    paths = _paths_label(getattr(latest, "paths", []))
    if getattr(latest, "ok", False):
        return f"{base} Git restore dry-run succeeded for {paths}. Apply git_restore only if discarding those changes is intended."
    return f"{base} Git restore dry-run failed for {paths}. Inspect git_status and choose valid paths before restoring."


def _git_restore_next_action_instruction(base: str, latest: Observation) -> str:
    paths = _paths_label(getattr(latest, "paths", []))
    if getattr(latest, "ok", False):
        return f"{base} Git restore completed for {paths}. Use git_status to confirm the worktree before continuing."
    return f"{base} Git restore failed for {paths}. Inspect git_status and the restore error before trying again."


def _git_stashes_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        return f"{base} Git stashes could not be listed. Inspect git_status or continue without stash actions."
    total = int(getattr(latest, "total", 0) or 0)
    if total:
        return (
            f"{base} Git stash list found {total} stash(es). Use check_git_stash_apply or check_git_stash_drop "
            "before changing stash state."
        )
    return f"{base} No git stashes were found. Continue the requested work or use check_git_stash if saving changes is needed."


def _check_git_stash_next_action_instruction(base: str, latest: Observation) -> str:
    if getattr(latest, "ok", False):
        return f"{base} Git stash dry-run succeeded. Apply git_stash only if saving the current changes is intended."
    return f"{base} Git stash dry-run failed. Inspect git_status or the stash message before trying again."


def _git_stash_next_action_instruction(base: str, latest: Observation) -> str:
    if getattr(latest, "ok", False):
        return f"{base} Git stash completed. Use git_status or git_stashes to confirm saved changes before continuing."
    return f"{base} Git stash failed. Inspect git_status and the stash error before trying again."


def _check_git_stash_apply_next_action_instruction(base: str, latest: Observation) -> str:
    if getattr(latest, "ok", False):
        return f"{base} Git stash apply dry-run succeeded for {getattr(latest, 'stash_ref', 'stash')}. Apply only if restoring those changes is intended."
    if not getattr(latest, "worktree_clean", True):
        return f"{base} Git stash apply dry-run failed because the worktree is not clean. Inspect git_status before applying."
    return f"{base} Git stash apply dry-run failed. Inspect the stash ref or patch before trying again."


def _git_stash_apply_next_action_instruction(base: str, latest: Observation) -> str:
    if getattr(latest, "ok", False):
        return f"{base} Git stash apply completed. Use git_status, git_diff, or review_changes before continuing."
    return f"{base} Git stash apply failed. Inspect conflicts, git_status, or the apply error before retrying."


def _check_git_stash_drop_next_action_instruction(base: str, latest: Observation) -> str:
    if getattr(latest, "ok", False):
        return f"{base} Git stash drop dry-run succeeded for {getattr(latest, 'stash_ref', 'stash')}. Drop only if that stash is no longer needed."
    return f"{base} Git stash drop dry-run failed. Inspect git_stashes before trying again."


def _git_stash_drop_next_action_instruction(base: str, latest: Observation) -> str:
    if getattr(latest, "ok", False):
        return f"{base} Git stash drop completed. Use git_stashes if you need to confirm remaining stash entries."
    return f"{base} Git stash drop failed. Inspect git_stashes and the drop error before retrying."


def _check_git_switch_next_action_instruction(base: str, latest: Observation) -> str:
    branch = str(getattr(latest, "branch", "") or "target branch")
    if getattr(latest, "ok", False):
        return f"{base} Git switch dry-run succeeded for {branch}. Run git_switch only if changing branches is intended."
    if not getattr(latest, "worktree_clean", True):
        return f"{base} Git switch dry-run failed because the worktree is not clean. Commit, stash, or restore before switching."
    return f"{base} Git switch dry-run failed for {branch}. Inspect branch existence or git status before trying again."


def _git_switch_next_action_instruction(base: str, latest: Observation) -> str:
    branch = str(getattr(latest, "branch", "") or "target branch")
    if getattr(latest, "ok", False):
        return f"{base} Git switch completed to {branch}. Use git_status or continue the requested work on the new branch."
    return f"{base} Git switch failed for {branch}. Inspect git_status and branch state before retrying."


def _git_history_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        return f"{base} Git history could not be read. Check the revision, path, or repository state before trying another history query."
    if latest.kind == "git_blame":
        return (
            f"{base} Git blame was read for {getattr(latest, 'path', 'the selected file')}. "
            "Use it to understand ownership or recent changes, then inspect source or continue editing if needed."
        )
    if latest.kind == "git_show" and getattr(latest, "truncated", False):
        return f"{base} Git show output was truncated. Re-run git_show with a narrower path or inspect relevant files directly."
    return f"{base} Git history was read. Use it to decide whether to inspect source, continue the change, or answer directly."


def _review_changes_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        return f"{base} Change review failed. Inspect git_status, git_diff, or the review message before continuing."
    if not getattr(latest, "changes_ok", True):
        return f"{base} Change review found issues. Inspect the review output, fix blocking changes, and rerun review_changes."
    suggested_total = int(getattr(latest, "suggested_checks_total", 0) or 0)
    if suggested_total:
        return f"{base} Change review passed and suggested checks are available. Run relevant suggested or focused checks before final_review."
    return f"{base} Change review passed. Run any required verification, then use final_review before finishing."


def extended_git_next_action_instruction(base: str, latest: Observation) -> str:
    if latest.kind == "git_conflicts":
        return _git_conflicts_next_action_instruction(base, latest)
    if latest.kind == "git_info":
        return _git_info_next_action_instruction(base, latest)
    if latest.kind == "git_branches":
        return _git_branches_next_action_instruction(base, latest)
    if latest.kind == "check_git_fetch":
        return _check_git_fetch_next_action_instruction(base, latest)
    if latest.kind == "git_fetch":
        return _git_fetch_next_action_instruction(base, latest)
    if latest.kind == "check_git_pull":
        return _check_git_pull_next_action_instruction(base, latest)
    if latest.kind == "git_pull":
        return _git_pull_next_action_instruction(base, latest)
    if latest.kind == "check_git_push":
        return _check_git_push_next_action_instruction(base, latest)
    if latest.kind == "git_push":
        return _git_push_next_action_instruction(base, latest)
    if latest.kind == "check_github_pr_create":
        if getattr(latest, "ok", False):
            return f"{base} Pull request validation passed. Run github_pr_create only if pull request publication was requested."
        return (
            f"{base} Pull request validation failed. Resolve the reported branch, remote, base, push, or gh prerequisite, "
            "then rerun check_github_pr_create."
        )
    if latest.kind == "github_pr_create":
        if getattr(latest, "ok", False):
            return f"{base} The pull request was created. Report its URL and the verified head/base branches."
        return f"{base} Pull request creation failed. Inspect the gh message, fix the cause, and revalidate before retrying."
    if latest.kind == "check_git_restore":
        return _check_git_restore_next_action_instruction(base, latest)
    if latest.kind == "git_restore":
        return _git_restore_next_action_instruction(base, latest)
    if latest.kind == "git_stashes":
        return _git_stashes_next_action_instruction(base, latest)
    if latest.kind == "check_git_stash":
        return _check_git_stash_next_action_instruction(base, latest)
    if latest.kind == "git_stash":
        return _git_stash_next_action_instruction(base, latest)
    if latest.kind == "check_git_stash_apply":
        return _check_git_stash_apply_next_action_instruction(base, latest)
    if latest.kind == "git_stash_apply":
        return _git_stash_apply_next_action_instruction(base, latest)
    if latest.kind == "check_git_stash_drop":
        return _check_git_stash_drop_next_action_instruction(base, latest)
    if latest.kind == "git_stash_drop":
        return _git_stash_drop_next_action_instruction(base, latest)
    if latest.kind == "check_git_switch":
        return _check_git_switch_next_action_instruction(base, latest)
    if latest.kind == "git_switch":
        return _git_switch_next_action_instruction(base, latest)
    if latest.kind in {"git_log", "git_show", "git_blame"}:
        return _git_history_next_action_instruction(base, latest)
    if latest.kind == "review_changes":
        return _review_changes_next_action_instruction(base, latest)

    raise ValueError(f"Unsupported extended git next-action kind: {latest.kind}")
