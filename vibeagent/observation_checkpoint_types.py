from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class CheckpointInfo:
    checkpoint_id: str
    label: str
    created_at: str
    head: str
    changed_files: int
    staged_files: int
    unstaged_files: int
    untracked_files: int


@dataclass(frozen=True)
class CheckpointCreateObservation:
    kind: Literal["checkpoint_create"]
    ok: bool
    checkpoint: CheckpointInfo | None
    staged_patch_chars: int
    unstaged_patch_chars: int
    message: str


@dataclass(frozen=True)
class CheckpointListObservation:
    kind: Literal["checkpoint_list"]
    ok: bool
    checkpoints: list[CheckpointInfo]
    total: int
    message: str


@dataclass(frozen=True)
class CheckpointShowObservation:
    kind: Literal["checkpoint_show"]
    ok: bool
    checkpoint: CheckpointInfo | None
    project_root: str
    git_status: str
    untracked_saved_files: int
    untracked_skipped_files: int
    saved_untracked_paths: list[str]
    saved_untracked_paths_truncated: bool
    staged_patch_chars: int
    unstaged_patch_chars: int
    message: str


@dataclass(frozen=True)
class CheckpointDiffObservation:
    kind: Literal["checkpoint_diff"]
    ok: bool
    checkpoint_id: str
    label: str
    created_at: str
    staged_patch: str
    staged_patch_chars: int
    staged_patch_truncated: bool
    unstaged_patch: str
    unstaged_patch_chars: int
    unstaged_patch_truncated: bool
    max_chars: int
    message: str


@dataclass(frozen=True)
class CheckpointStatusObservation:
    kind: Literal["checkpoint_status"]
    ok: bool
    checkpoint_id: str
    matches: bool
    status_matches: bool
    staged_patch_matches: bool
    unstaged_patch_matches: bool
    untracked_file_matches: bool
    saved_changed_files: int
    saved_staged_files: int
    saved_unstaged_files: int
    saved_untracked_files: int
    current_changed_files: int
    current_staged_files: int
    current_unstaged_files: int
    current_untracked_files: int
    message: str


@dataclass(frozen=True)
class CheckCheckpointRestoreObservation:
    kind: Literal["check_checkpoint_restore"]
    ok: bool
    checkpoint_id: str
    can_restore: bool
    saved_head: str
    current_head: str
    saved_untracked_files: int
    current_untracked_files: int
    staged_patch_chars: int
    unstaged_patch_chars: int
    message: str


@dataclass(frozen=True)
class CheckpointRestoreObservation:
    kind: Literal["checkpoint_restore"]
    ok: bool
    checkpoint_id: str
    restored: bool
    matches: bool
    saved_head: str
    current_head: str
    saved_untracked_files: int
    current_untracked_files: int
    staged_patch_chars: int
    unstaged_patch_chars: int
    message: str


@dataclass(frozen=True)
class CheckCheckpointDeleteObservation:
    kind: Literal["check_checkpoint_delete"]
    ok: bool
    checkpoint_id: str
    can_delete: bool
    label: str
    created_at: str
    message: str


@dataclass(frozen=True)
class CheckpointDeleteObservation:
    kind: Literal["checkpoint_delete"]
    ok: bool
    checkpoint_id: str
    deleted: bool
    message: str


@dataclass(frozen=True)
class CheckCheckpointPruneObservation:
    kind: Literal["check_checkpoint_prune"]
    ok: bool
    keep_last: int
    total: int
    kept: int
    delete_count: int
    checkpoints: list[CheckpointInfo]
    message: str


@dataclass(frozen=True)
class CheckpointPruneObservation:
    kind: Literal["checkpoint_prune"]
    ok: bool
    keep_last: int
    total: int
    kept: int
    deleted: int
    checkpoints: list[CheckpointInfo]
    message: str
