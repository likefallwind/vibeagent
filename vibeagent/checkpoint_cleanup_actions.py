from __future__ import annotations

import shutil
from pathlib import Path

from .checkpoint_storage import checkpoint_directory_for_deletion, read_checkpoint_infos, read_checkpoint_metadata
from .types import (
    CheckCheckpointDeleteObservation,
    CheckCheckpointPruneObservation,
    CheckpointDeleteObservation,
    CheckpointPruneObservation,
)


def check_checkpoint_delete_observation(root: Path, checkpoint_id: str) -> CheckCheckpointDeleteObservation:
    metadata, message = read_checkpoint_metadata(root, checkpoint_id)
    if metadata is None:
        return CheckCheckpointDeleteObservation(
            kind="check_checkpoint_delete",
            ok=False,
            checkpoint_id=checkpoint_id,
            can_delete=False,
            label="",
            created_at="",
            message=message,
        )
    resolved_id = checkpoint_id.strip()
    display_id = str(metadata.get("id") or resolved_id)
    return CheckCheckpointDeleteObservation(
        kind="check_checkpoint_delete",
        ok=True,
        checkpoint_id=display_id,
        can_delete=True,
        label=str(metadata.get("label") or ""),
        created_at=str(metadata.get("created_at") or ""),
        message=f"Checkpoint delete would remove saved checkpoint {display_id}.",
    )


def checkpoint_delete_observation(root: Path, checkpoint_id: str) -> CheckpointDeleteObservation:
    preview = check_checkpoint_delete_observation(root, checkpoint_id)
    if not preview.ok:
        return CheckpointDeleteObservation(
            kind="checkpoint_delete",
            ok=False,
            checkpoint_id=preview.checkpoint_id,
            deleted=False,
            message=preview.message,
        )
    resolved_id = checkpoint_id.strip()
    display_id = preview.checkpoint_id
    checkpoint_dir, message = checkpoint_directory_for_deletion(root, resolved_id)
    if checkpoint_dir is None:
        return CheckpointDeleteObservation(
            kind="checkpoint_delete",
            ok=False,
            checkpoint_id=display_id,
            deleted=False,
            message=message,
        )
    try:
        shutil.rmtree(checkpoint_dir)
    except OSError as error:
        return CheckpointDeleteObservation(
            kind="checkpoint_delete",
            ok=False,
            checkpoint_id=display_id,
            deleted=False,
            message=f"Failed to delete checkpoint {display_id}: {error}",
        )
    return CheckpointDeleteObservation(
        kind="checkpoint_delete",
        ok=True,
        checkpoint_id=display_id,
        deleted=True,
        message=f"Deleted checkpoint {display_id}.",
    )


def check_checkpoint_prune_observation(root: Path, keep_last: int) -> CheckCheckpointPruneObservation:
    checkpoints = read_checkpoint_infos(root)
    to_delete = checkpoints[keep_last:] if keep_last < len(checkpoints) else []
    kept = len(checkpoints) - len(to_delete)
    return CheckCheckpointPruneObservation(
        kind="check_checkpoint_prune",
        ok=True,
        keep_last=keep_last,
        total=len(checkpoints),
        kept=kept,
        delete_count=len(to_delete),
        checkpoints=to_delete,
        message=(
            f"Checkpoint prune would delete {len(to_delete)} saved checkpoint(s)."
            if to_delete
            else "No checkpoints need pruning."
        ),
    )


def checkpoint_prune_observation(root: Path, keep_last: int) -> CheckpointPruneObservation:
    preview = check_checkpoint_prune_observation(root, keep_last)
    deleted = 0
    for checkpoint in preview.checkpoints:
        checkpoint_dir, message = checkpoint_directory_for_deletion(root, checkpoint.checkpoint_id)
        if checkpoint_dir is None:
            return CheckpointPruneObservation(
                kind="checkpoint_prune",
                ok=False,
                keep_last=keep_last,
                total=preview.total,
                kept=preview.kept,
                deleted=deleted,
                checkpoints=preview.checkpoints,
                message=message,
            )
        try:
            shutil.rmtree(checkpoint_dir)
        except OSError as error:
            return CheckpointPruneObservation(
                kind="checkpoint_prune",
                ok=False,
                keep_last=keep_last,
                total=preview.total,
                kept=preview.kept,
                deleted=deleted,
                checkpoints=preview.checkpoints,
                message=f"Failed to prune checkpoint {checkpoint.checkpoint_id}: {error}",
            )
        deleted += 1
    return CheckpointPruneObservation(
        kind="checkpoint_prune",
        ok=True,
        keep_last=keep_last,
        total=preview.total,
        kept=preview.kept,
        deleted=deleted,
        checkpoints=preview.checkpoints,
        message=(
            f"Pruned {deleted} saved checkpoint(s)."
            if deleted
            else "No checkpoints needed pruning."
        ),
    )
