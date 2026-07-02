from __future__ import annotations

from .prompt_observation_utils import truncate


def format_checkpoint_observation(index: int, observation: object) -> str | None:
    if observation.kind == "checkpoint_show":
        return _format_checkpoint_show(index, observation)
    if observation.kind == "checkpoint_diff":
        return _format_checkpoint_diff(index, observation)
    if observation.kind == "checkpoint_status":
        return _format_checkpoint_status(index, observation)
    if observation.kind == "check_checkpoint_restore":
        return _format_check_checkpoint_restore(index, observation)
    if observation.kind == "checkpoint_restore":
        return _format_checkpoint_restore(index, observation)
    if observation.kind == "check_checkpoint_delete":
        return "\n".join(
            [
                f"{index}. check_checkpoint_delete {observation.checkpoint_id}: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"canDelete: {str(observation.can_delete).lower()}",
                f"createdAt: {observation.created_at or 'none'}",
            ]
        )
    if observation.kind == "checkpoint_delete":
        return "\n".join(
            [
                f"{index}. checkpoint_delete {observation.checkpoint_id}: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"deleted: {str(observation.deleted).lower()}",
            ]
        )
    if observation.kind == "check_checkpoint_prune":
        checkpoint_ids = ", ".join(item.checkpoint_id for item in observation.checkpoints) or "none"
        return "\n".join(
            [
                f"{index}. check_checkpoint_prune keep_last={observation.keep_last}: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"total/kept/deleteCount: {observation.total}/{observation.kept}/{observation.delete_count}",
                f"deleteCheckpoints: {checkpoint_ids}",
            ]
        )
    if observation.kind == "checkpoint_prune":
        checkpoint_ids = ", ".join(item.checkpoint_id for item in observation.checkpoints) or "none"
        return "\n".join(
            [
                f"{index}. checkpoint_prune keep_last={observation.keep_last}: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"total/kept/deleted: {observation.total}/{observation.kept}/{observation.deleted}",
                f"deletedCheckpoints: {checkpoint_ids}",
            ]
        )
    return None


def _format_checkpoint_show(index: int, observation: object) -> str:
    checkpoint = observation.checkpoint
    parts = [
        f"{index}. checkpoint_show: {observation.message}",
        f"ok: {str(observation.ok).lower()}",
    ]
    if checkpoint is not None:
        parts.extend(
            [
                f"id: {checkpoint.checkpoint_id}",
                f"label: {checkpoint.label or 'none'}",
                f"createdAt: {checkpoint.created_at}",
                f"projectRoot: {observation.project_root or 'none'}",
                f"head: {checkpoint.head}",
                f"changedFiles: {checkpoint.changed_files}",
                f"stagedFiles: {checkpoint.staged_files}",
                f"unstagedFiles: {checkpoint.unstaged_files}",
                f"untrackedFiles: {checkpoint.untracked_files}",
                f"untrackedSavedFiles: {observation.untracked_saved_files}",
                f"untrackedSkippedFiles: {observation.untracked_skipped_files}",
                f"savedUntrackedPathsTruncated: {str(observation.saved_untracked_paths_truncated).lower()}",
                f"savedUntrackedPaths: {', '.join(observation.saved_untracked_paths) or 'none'}",
                f"stagedPatchChars: {observation.staged_patch_chars}",
                f"unstagedPatchChars: {observation.unstaged_patch_chars}",
            ]
        )
    if observation.git_status:
        parts.append(f"gitStatus:\n{truncate(observation.git_status)}")
    return "\n".join(parts)


def _format_checkpoint_diff(index: int, observation: object) -> str:
    return "\n".join(
        [
            f"{index}. checkpoint_diff {observation.checkpoint_id}: {observation.message}",
            f"ok: {str(observation.ok).lower()}",
            f"label: {observation.label or 'none'}",
            f"createdAt: {observation.created_at or 'none'}",
            f"maxChars: {observation.max_chars}",
            f"stagedPatchChars: {observation.staged_patch_chars}",
            f"stagedPatchTruncated: {str(observation.staged_patch_truncated).lower()}",
            f"stagedPatch:\n{truncate(observation.staged_patch) if observation.staged_patch else 'no staged changes'}",
            f"unstagedPatchChars: {observation.unstaged_patch_chars}",
            f"unstagedPatchTruncated: {str(observation.unstaged_patch_truncated).lower()}",
            f"unstagedPatch:\n{truncate(observation.unstaged_patch) if observation.unstaged_patch else 'no unstaged changes'}",
        ]
    )


def _format_checkpoint_status(index: int, observation: object) -> str:
    return "\n".join(
        [
            f"{index}. checkpoint_status {observation.checkpoint_id}: {observation.message}",
            f"ok: {str(observation.ok).lower()}",
            f"matches: {str(observation.matches).lower()}",
            f"statusMatches: {str(observation.status_matches).lower()}",
            f"stagedPatchMatches: {str(observation.staged_patch_matches).lower()}",
            f"unstagedPatchMatches: {str(observation.unstaged_patch_matches).lower()}",
            f"untrackedFileMatches: {str(observation.untracked_file_matches).lower()}",
            (
                "saved/current changedFiles: "
                f"{observation.saved_changed_files}/{observation.current_changed_files}, "
                f"staged: {observation.saved_staged_files}/{observation.current_staged_files}, "
                f"unstaged: {observation.saved_unstaged_files}/{observation.current_unstaged_files}, "
                f"untracked: {observation.saved_untracked_files}/{observation.current_untracked_files}"
            ),
        ]
    )


def _format_check_checkpoint_restore(index: int, observation: object) -> str:
    return "\n".join(
        [
            f"{index}. check_checkpoint_restore {observation.checkpoint_id}: {observation.message}",
            f"ok: {str(observation.ok).lower()}",
            f"canRestore: {str(observation.can_restore).lower()}",
            f"savedHead: {observation.saved_head or 'none'}",
            f"currentHead: {observation.current_head or 'none'}",
            f"savedUntrackedFiles: {observation.saved_untracked_files}",
            f"currentUntrackedFiles: {observation.current_untracked_files}",
            f"stagedPatchChars: {observation.staged_patch_chars}",
            f"unstagedPatchChars: {observation.unstaged_patch_chars}",
        ]
    )


def _format_checkpoint_restore(index: int, observation: object) -> str:
    return "\n".join(
        [
            f"{index}. checkpoint_restore {observation.checkpoint_id}: {observation.message}",
            f"ok: {str(observation.ok).lower()}",
            f"restored: {str(observation.restored).lower()}",
            f"matches: {str(observation.matches).lower()}",
            f"savedHead: {observation.saved_head or 'none'}",
            f"currentHead: {observation.current_head or 'none'}",
            f"savedUntrackedFiles: {observation.saved_untracked_files}",
            f"currentUntrackedFiles: {observation.current_untracked_files}",
            f"stagedPatchChars: {observation.staged_patch_chars}",
            f"unstagedPatchChars: {observation.unstaged_patch_chars}",
        ]
    )


__all__ = ["format_checkpoint_observation"]
