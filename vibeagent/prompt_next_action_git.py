from __future__ import annotations

from .types import Observation


GIT_NEXT_ACTION_KINDS = {
    "git_status",
    "git_changes",
    "git_diff",
    "git_diff_hunks",
    "git_diff_contexts",
    "check_git_stage",
    "git_stage",
    "check_git_unstage",
    "git_unstage",
    "check_git_commit",
    "git_commit",
}


def _format_next_action_items(items: list[str], max_items: int = 3) -> str:
    shown = items[:max_items]
    suffix = "" if len(items) <= max_items else f"; +{len(items) - max_items} more"
    return "; ".join(shown) + suffix


def _changed_file_labels(values: object) -> list[str]:
    labels: list[str] = []
    if not isinstance(values, list):
        return labels
    for value in values:
        path = str(getattr(value, "path", "") or "").strip()
        status = str(getattr(value, "status", "") or "").strip()
        if path and status:
            labels.append(f"{path} ({status})")
        elif path:
            labels.append(path)
    return labels


def _paths_label(values: object) -> str:
    if not isinstance(values, list):
        return "the selected path(s)"
    paths = [str(value).strip() for value in values if str(value).strip()]
    return _format_next_action_items(paths) if paths else "the selected path(s)"


def _git_status_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        return f"{base} Git status could not be read. Inspect the message or continue without git context."

    status = str(getattr(latest, "status", "") or "").strip()
    if status:
        return (
            f"{base} Git status shows existing worktree changes. Use git_changes, git_diff, or review_changes "
            "to inspect them before editing, staging, committing, or answering."
        )
    return f"{base} Git status is clean. Continue the requested work or answer directly if the task is complete."


def _git_changes_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        return f"{base} Git changes could not be read. Use git_status or git_diff to inspect the worktree another way."

    files = _changed_file_labels(getattr(latest, "files", []))
    if files:
        return (
            f"{base} Git changes lists changed file(s): {_format_next_action_items(files)}. "
            "Use git_diff, git_diff_contexts, or review_changes to inspect changes before staging, committing, or finishing."
        )
    return f"{base} Git changes found no changed files. Continue with the requested work or answer directly if complete."


def _git_diff_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        return f"{base} Git diff could not be read. Use git_status or git_changes to recover the worktree state."

    if str(getattr(latest, "diff", "") or "").strip():
        return (
            f"{base} Git diff shows concrete changes. Review whether they match the request, "
            "continue editing if needed, then run relevant verification before finishing."
        )
    return f"{base} Git diff is empty. Use git_status or git_changes if you expected changes, otherwise continue or answer directly."


def _git_diff_hunks_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        return f"{base} Git diff hunks could not be read. Use git_diff or git_status to inspect changes."

    total = int(getattr(latest, "total_hunks", 0) or 0)
    if total > 0:
        return (
            f"{base} Git diff hunks found {total} hunk(s). Use git_diff_contexts or read_file_context "
            "to inspect source context before editing, then verify the change."
        )
    return f"{base} Git diff hunks found no changes. Continue with the requested work or answer directly if complete."


def _git_diff_contexts_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        return f"{base} Git diff contexts could not be read. Use git_diff or read_file_context for targeted inspection."

    context_count = len(getattr(latest, "contexts", []) or [])
    if context_count > 0:
        return (
            f"{base} Git diff contexts provide source context for {context_count} hunk(s). "
            "Use the context to continue editing, then run focused or suggested checks before finishing."
        )
    return f"{base} Git diff contexts found no source context. Use git_diff or direct file reads if more detail is needed."


def _check_git_stage_next_action_instruction(base: str, latest: Observation) -> str:
    paths = _paths_label(getattr(latest, "paths", []))
    if getattr(latest, "ok", False):
        return (
            f"{base} Git stage dry-run succeeded for {paths}. Apply git_stage only if staging is intended, "
            "then use git_status or check_git_commit before committing."
        )
    return f"{base} Git stage dry-run failed for {paths}. Inspect status and choose valid paths before staging."


def _git_stage_next_action_instruction(base: str, latest: Observation) -> str:
    paths = _paths_label(getattr(latest, "paths", []))
    if getattr(latest, "ok", False):
        return (
            f"{base} Git stage completed for {paths}. Use git_status or check_git_commit next if preparing a commit, "
            "or continue editing if more work remains."
        )
    return f"{base} Git stage failed for {paths}. Inspect status and fix the path selection before continuing."


def _check_git_unstage_next_action_instruction(base: str, latest: Observation) -> str:
    paths = _paths_label(getattr(latest, "paths", []))
    if getattr(latest, "ok", False):
        return f"{base} Git unstage dry-run succeeded for {paths}. Apply git_unstage only if unstaging is intended."
    return f"{base} Git unstage dry-run failed for {paths}. Inspect git_status before trying again."


def _git_unstage_next_action_instruction(base: str, latest: Observation) -> str:
    paths = _paths_label(getattr(latest, "paths", []))
    if getattr(latest, "ok", False):
        return f"{base} Git unstage completed for {paths}. Use git_status to confirm the staging state if needed."
    return f"{base} Git unstage failed for {paths}. Inspect git_status before trying again."


def _check_git_commit_next_action_instruction(base: str, latest: Observation) -> str:
    if getattr(latest, "ok", False):
        return (
            f"{base} Git commit dry-run succeeded. Commit only after required verification is complete, "
            "or continue editing if the staged diff is not final."
        )
    return f"{base} Git commit dry-run failed. Inspect git_status, staged changes, or the commit message before committing."


def _git_commit_next_action_instruction(base: str, latest: Observation) -> str:
    if getattr(latest, "ok", False):
        return (
            f"{base} Git commit completed. Use git_status to confirm the worktree, git_push if explicitly requested, "
            "or answer directly with the commit hash."
        )
    return f"{base} Git commit failed. Inspect git_status and the commit error before trying again."


def git_next_action_instruction(base: str, latest: Observation) -> str:
    if latest.kind == "git_status":
        return _git_status_next_action_instruction(base, latest)
    if latest.kind == "git_changes":
        return _git_changes_next_action_instruction(base, latest)
    if latest.kind == "git_diff":
        return _git_diff_next_action_instruction(base, latest)
    if latest.kind == "git_diff_hunks":
        return _git_diff_hunks_next_action_instruction(base, latest)
    if latest.kind == "git_diff_contexts":
        return _git_diff_contexts_next_action_instruction(base, latest)
    if latest.kind == "check_git_stage":
        return _check_git_stage_next_action_instruction(base, latest)
    if latest.kind == "git_stage":
        return _git_stage_next_action_instruction(base, latest)
    if latest.kind == "check_git_unstage":
        return _check_git_unstage_next_action_instruction(base, latest)
    if latest.kind == "git_unstage":
        return _git_unstage_next_action_instruction(base, latest)
    if latest.kind == "check_git_commit":
        return _check_git_commit_next_action_instruction(base, latest)
    if latest.kind == "git_commit":
        return _git_commit_next_action_instruction(base, latest)

    raise ValueError(f"Unsupported git next-action kind: {latest.kind}")
