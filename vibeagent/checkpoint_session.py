from __future__ import annotations

from pathlib import Path
import shutil

from .checkpoint_storage import (
    checkpoint_directory_for_deletion,
    read_checkpoint_infos,
    read_checkpoint_metadata,
)
from .session_store import read_session_events


SESSION_CHECKPOINT_LIMIT = 100


def checkpoint_session_metadata(project_root: Path, run_id: str | None) -> dict[str, object]:
    if run_id is None:
        return {}
    try:
        events = read_session_events(project_root, run_id)
    except (OSError, ValueError):
        return {}
    if not events:
        return {}
    return {
        "session_run_id": run_id,
        "session_event_line": max(event.line_number for event in events),
    }


def prune_session_checkpoints(
    project_root: Path,
    run_id: str,
    keep_last: int = SESSION_CHECKPOINT_LIMIT,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    root = project_root.resolve()
    matching: list[str] = []
    for info in read_checkpoint_infos(root):
        metadata, _ = read_checkpoint_metadata(root, info.checkpoint_id)
        if metadata is not None and metadata.get("session_run_id") == run_id:
            matching.append(info.checkpoint_id)

    deleted: list[str] = []
    warnings: list[str] = []
    for checkpoint_id in matching[max(keep_last, 0) :]:
        directory, message = checkpoint_directory_for_deletion(root, checkpoint_id)
        if directory is None:
            warnings.append(message)
            continue
        try:
            shutil.rmtree(directory)
        except OSError as error:
            warnings.append(f"Failed to prune checkpoint {checkpoint_id}: {error}")
            continue
        deleted.append(checkpoint_id)
    return tuple(deleted), tuple(warnings)


__all__ = [
    "SESSION_CHECKPOINT_LIMIT",
    "checkpoint_session_metadata",
    "prune_session_checkpoints",
]
