from __future__ import annotations

import json
from datetime import UTC, datetime
import shutil

from .checkpoint_patch_io import MAX_CHECKPOINT_STATUS_CHARS, capture_checkpoint_patches

from .checkpoint_storage import (
    checkpoint_info_to_metadata,
    checkpoint_root,
    checkpoint_root_safety_error,
    count_checkpoint_status_kinds,
    filter_checkpoint_status,
    make_checkpoint_id,
    normalize_checkpoint_label,
    read_checkpoint_git_head,
    save_checkpoint_untracked_files,
)
from .checkpoint_session import checkpoint_session_metadata
from .types import (
    CheckpointCreateObservation,
    CheckpointInfo,
)
from .workspace import (
    RunWorkspace,
    read_git_status,
)


def create_checkpoint_observation(workspace: RunWorkspace, label: str | None = None) -> CheckpointCreateObservation:
    status = read_git_status(workspace, max_output_chars=MAX_CHECKPOINT_STATUS_CHARS)
    if not status.ok:
        return CheckpointCreateObservation(
            kind="checkpoint_create",
            ok=False,
            checkpoint=None,
            staged_patch_chars=0,
            unstaged_patch_chars=0,
            message=status.stderr or "git status failed.",
        )
    if status.stdout_truncated:
        return CheckpointCreateObservation(
            kind="checkpoint_create",
            ok=False,
            checkpoint=None,
            staged_patch_chars=0,
            unstaged_patch_chars=0,
            message=f"git status output exceeded {MAX_CHECKPOINT_STATUS_CHARS} characters.",
        )
    head = read_checkpoint_git_head(workspace.root)
    if not head:
        return CheckpointCreateObservation(
            kind="checkpoint_create",
            ok=False,
            checkpoint=None,
            staged_patch_chars=0,
            unstaged_patch_chars=0,
            message="git rev-parse HEAD failed.",
        )

    filtered_status = filter_checkpoint_status(status.stdout)
    counts = count_checkpoint_status_kinds(filtered_status)
    checkpoint_id = make_checkpoint_id()
    created_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    info = CheckpointInfo(
        checkpoint_id=checkpoint_id,
        label=normalize_checkpoint_label(label),
        created_at=created_at,
        head=head,
        changed_files=counts["changed_files"],
        staged_files=counts["staged_files"],
        unstaged_files=counts["unstaged_files"],
        untracked_files=counts["untracked_files"],
    )
    root_error = checkpoint_root_safety_error(workspace.root)
    if root_error:
        return CheckpointCreateObservation(
            kind="checkpoint_create",
            ok=False,
            checkpoint=None,
            staged_patch_chars=0,
            unstaged_patch_chars=0,
            message=root_error,
        )
    checkpoint_base = checkpoint_root(workspace.root)
    try:
        checkpoint_base.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        return CheckpointCreateObservation(
            kind="checkpoint_create",
            ok=False,
            checkpoint=None,
            staged_patch_chars=0,
            unstaged_patch_chars=0,
            message=f"Failed to create checkpoint root: {error}",
        )
    root_error = checkpoint_root_safety_error(workspace.root)
    if root_error:
        return CheckpointCreateObservation(
            kind="checkpoint_create",
            ok=False,
            checkpoint=None,
            staged_patch_chars=0,
            unstaged_patch_chars=0,
            message=root_error,
        )
    checkpoint_dir = checkpoint_base / checkpoint_id
    try:
        checkpoint_dir.mkdir(exist_ok=False)
    except OSError as error:
        return CheckpointCreateObservation(
            kind="checkpoint_create",
            ok=False,
            checkpoint=None,
            staged_patch_chars=0,
            unstaged_patch_chars=0,
            message=f"Failed to create checkpoint directory: {error}",
        )
    patches = capture_checkpoint_patches(workspace.root, checkpoint_dir)
    if not patches.ok:
        shutil.rmtree(checkpoint_dir, ignore_errors=True)
        return CheckpointCreateObservation(
            kind="checkpoint_create",
            ok=False,
            checkpoint=None,
            staged_patch_chars=0,
            unstaged_patch_chars=0,
            message=patches.error,
        )
    try:
        metadata = checkpoint_info_to_metadata(
            info,
            str(workspace.root),
            filtered_status,
            patches.staged_chars,
            patches.unstaged_chars,
        )
        metadata.update(checkpoint_session_metadata(workspace.root, workspace.run_id))
        saved_untracked, skipped_untracked = save_checkpoint_untracked_files(
            workspace.root,
            checkpoint_dir,
            filtered_status,
        )
        metadata["untracked_saved_files"] = saved_untracked
        metadata["untracked_skipped_files"] = skipped_untracked
        (checkpoint_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as error:
        shutil.rmtree(checkpoint_dir, ignore_errors=True)
        return CheckpointCreateObservation(
            kind="checkpoint_create",
            ok=False,
            checkpoint=None,
            staged_patch_chars=0,
            unstaged_patch_chars=0,
            message=f"Failed to save checkpoint: {error}",
        )
    return CheckpointCreateObservation(
        kind="checkpoint_create",
        ok=True,
        checkpoint=info,
        staged_patch_chars=patches.staged_chars,
        unstaged_patch_chars=patches.unstaged_chars,
        message=f"Saved checkpoint {checkpoint_id}.",
    )
