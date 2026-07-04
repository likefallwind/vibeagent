from __future__ import annotations

from .types import Observation


CHECKPOINT_NEXT_ACTION_KINDS = {
    "checkpoint_create",
    "checkpoint_list",
    "checkpoint_show",
    "checkpoint_diff",
    "checkpoint_status",
    "check_checkpoint_restore",
    "checkpoint_restore",
    "check_checkpoint_delete",
    "checkpoint_delete",
    "check_checkpoint_prune",
    "checkpoint_prune",
}


def _checkpoint_list_next_action_instruction(base: str, latest: Observation) -> str:
    total = int(getattr(latest, "total", 0) or 0)
    if not getattr(latest, "ok", False):
        return (
            f"{base} Checkpoint list could not be read. Inspect the error, continue without rollback context, "
            "or create a new checkpoint before risky work."
        )
    if total > 0:
        return (
            f"{base} Checkpoint list found {total} saved checkpoint(s). "
            "Use checkpoint_show, checkpoint_diff, or checkpoint_status on the relevant checkpoint before restoring or deleting anything."
        )
    return (
        f"{base} No checkpoints are available. Create a checkpoint before risky edits, "
        "or continue with the requested work if no rollback point is needed."
    )


def _checkpoint_show_next_action_instruction(base: str, latest: Observation) -> str:
    checkpoint = getattr(latest, "checkpoint", None)
    if not getattr(latest, "ok", False) or checkpoint is None:
        return (
            f"{base} Checkpoint metadata could not be read. Use checkpoint_list to choose a valid checkpoint, "
            "or continue without restoring if no checkpoint is needed."
        )
    checkpoint_id = str(getattr(checkpoint, "checkpoint_id", "") or "latest")
    return (
        f"{base} Checkpoint metadata is available. Use checkpoint_diff or checkpoint_status for {checkpoint_id} "
        "before deciding whether to restore, delete, or continue."
    )


def _checkpoint_diff_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        return (
            f"{base} Checkpoint diff could not be read. Use checkpoint_show or checkpoint_status to inspect the checkpoint, "
            "or choose a different checkpoint."
        )
    has_patch = int(getattr(latest, "staged_patch_chars", 0) or 0) > 0 or int(getattr(latest, "unstaged_patch_chars", 0) or 0) > 0
    if has_patch:
        return (
            f"{base} Checkpoint diff shows saved changes. Inspect whether the patch matches the desired rollback point, "
            "then use check_checkpoint_restore before restoring or continue with edits."
        )
    return (
        f"{base} Checkpoint diff has no saved patch content. Use checkpoint_status or checkpoint_show to verify whether untracked files or status still matter."
    )


def _checkpoint_status_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        return (
            f"{base} Checkpoint status could not be compared. Use checkpoint_show or checkpoint_list to choose a valid checkpoint, "
            "or continue without restoring."
        )
    if getattr(latest, "matches", False):
        return (
            f"{base} Current worktree matches the checkpoint. Continue with the requested work, "
            "or answer directly if the task is complete."
        )
    return (
        f"{base} Current worktree differs from the checkpoint. Use checkpoint_diff to inspect saved changes, "
        "then use check_checkpoint_restore before any restore decision."
    )


def _check_checkpoint_restore_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False) or not getattr(latest, "can_restore", False):
        return (
            f"{base} Checkpoint restore is not currently safe. Inspect checkpoint_status, checkpoint_show, or the reported message, "
            "then choose a different checkpoint or continue without restoring."
        )
    return (
        f"{base} Checkpoint restore preview is safe. If rollback is intended, request checkpoint_restore for this checkpoint; "
        "otherwise continue with the current worktree."
    )


def _checkpoint_restore_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False) or not getattr(latest, "restored", False):
        return (
            f"{base} Checkpoint restore did not complete. Inspect the message and checkpoint_status before trying another restore or continuing."
        )
    if getattr(latest, "matches", False):
        return (
            f"{base} Checkpoint restore completed and the worktree matches the checkpoint. "
            "Run the relevant verification checks or continue from the restored state."
        )
    return (
        f"{base} Checkpoint restore completed but status does not match. Inspect checkpoint_status and git_diff before continuing."
    )


def _check_checkpoint_delete_next_action_instruction(base: str, latest: Observation) -> str:
    if getattr(latest, "ok", False) and getattr(latest, "can_delete", False):
        return (
            f"{base} Checkpoint delete preview is safe. Delete only if the checkpoint is no longer needed; "
            "otherwise continue without deleting it."
        )
    return (
        f"{base} Checkpoint delete preview is not ready. Use checkpoint_list to choose a valid checkpoint, "
        "or continue without deleting anything."
    )


def _checkpoint_delete_next_action_instruction(base: str, latest: Observation) -> str:
    if getattr(latest, "ok", False) and getattr(latest, "deleted", False):
        return f"{base} Checkpoint was deleted. Continue with the requested work or answer directly if the task is complete."
    return f"{base} Checkpoint delete failed. Inspect the message, then choose a valid checkpoint or continue without deleting."


def _check_checkpoint_prune_next_action_instruction(base: str, latest: Observation) -> str:
    delete_count = int(getattr(latest, "delete_count", 0) or 0)
    if getattr(latest, "ok", False) and delete_count > 0:
        return (
            f"{base} Checkpoint prune preview would delete {delete_count} checkpoint(s). "
            "Proceed with checkpoint_prune only if those rollback points are no longer needed."
        )
    if getattr(latest, "ok", False):
        return f"{base} Checkpoint prune preview has nothing to delete. Continue with the requested work."
    return f"{base} Checkpoint prune preview failed. Inspect the message or continue without pruning."


def _checkpoint_prune_next_action_instruction(base: str, latest: Observation) -> str:
    deleted = int(getattr(latest, "deleted", 0) or 0)
    if getattr(latest, "ok", False):
        return f"{base} Checkpoint prune completed and deleted {deleted} checkpoint(s). Continue with the requested work."
    return f"{base} Checkpoint prune failed. Inspect the message or continue without pruning."


def checkpoint_next_action_instruction(base: str, latest: Observation) -> str:
    if latest.kind == "checkpoint_create":
        if getattr(latest, "ok", False):
            return (
                f"{base} Checkpoint was saved. Continue with the risky edit, command, or next planned step; "
                "use checkpoint_status later if rollback state matters."
            )
        return f"{base} Checkpoint creation failed. Inspect the message before risky edits, or continue only if no rollback point is needed."
    if latest.kind == "checkpoint_list":
        return _checkpoint_list_next_action_instruction(base, latest)
    if latest.kind == "checkpoint_show":
        return _checkpoint_show_next_action_instruction(base, latest)
    if latest.kind == "checkpoint_diff":
        return _checkpoint_diff_next_action_instruction(base, latest)
    if latest.kind == "checkpoint_status":
        return _checkpoint_status_next_action_instruction(base, latest)
    if latest.kind == "check_checkpoint_restore":
        return _check_checkpoint_restore_next_action_instruction(base, latest)
    if latest.kind == "checkpoint_restore":
        return _checkpoint_restore_next_action_instruction(base, latest)
    if latest.kind == "check_checkpoint_delete":
        return _check_checkpoint_delete_next_action_instruction(base, latest)
    if latest.kind == "checkpoint_delete":
        return _checkpoint_delete_next_action_instruction(base, latest)
    if latest.kind == "check_checkpoint_prune":
        return _check_checkpoint_prune_next_action_instruction(base, latest)
    if latest.kind == "checkpoint_prune":
        return _checkpoint_prune_next_action_instruction(base, latest)

    raise ValueError(f"Unsupported checkpoint next-action kind: {latest.kind}")
