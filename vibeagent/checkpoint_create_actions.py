from __future__ import annotations

import json
from datetime import UTC, datetime

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
    read_git_diff,
    read_git_status,
)


def create_checkpoint_observation(workspace: RunWorkspace, label: str | None = None) -> CheckpointCreateObservation:
    status = read_git_status(workspace)
    if not status.ok:
        return CheckpointCreateObservation(
            kind="checkpoint_create",
            ok=False,
            checkpoint=None,
            staged_patch_chars=0,
            unstaged_patch_chars=0,
            message=status.stderr or "git status failed.",
        )
    staged = read_git_diff(workspace, staged=True)
    unstaged = read_git_diff(workspace, staged=False)
    if not staged.ok or not unstaged.ok:
        return CheckpointCreateObservation(
            kind="checkpoint_create",
            ok=False,
            checkpoint=None,
            staged_patch_chars=0,
            unstaged_patch_chars=0,
            message=staged.stderr or unstaged.stderr or "git diff failed.",
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
    metadata = checkpoint_info_to_metadata(info, str(workspace.root), filtered_status, len(staged.stdout), len(unstaged.stdout))
    metadata.update(checkpoint_session_metadata(workspace.root, workspace.run_id))
    saved_untracked, skipped_untracked = save_checkpoint_untracked_files(workspace.root, checkpoint_dir, filtered_status)
    metadata["untracked_saved_files"] = saved_untracked
    metadata["untracked_skipped_files"] = skipped_untracked
    (checkpoint_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (checkpoint_dir / "staged.patch").write_text(staged.stdout, encoding="utf-8")
    (checkpoint_dir / "unstaged.patch").write_text(unstaged.stdout, encoding="utf-8")
    return CheckpointCreateObservation(
        kind="checkpoint_create",
        ok=True,
        checkpoint=info,
        staged_patch_chars=len(staged.stdout),
        unstaged_patch_chars=len(unstaged.stdout),
        message=f"Saved checkpoint {checkpoint_id}.",
    )
