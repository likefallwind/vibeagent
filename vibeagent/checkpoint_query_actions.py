from __future__ import annotations

from pathlib import Path

from .checkpoint_storage import (
    checkpoint_info_from_metadata,
    checkpoint_untracked_files_match,
    clip_checkpoint_untracked_paths,
    clip_text_with_flag,
    count_checkpoint_status_kinds,
    filter_checkpoint_status,
    read_checkpoint_infos,
    read_checkpoint_metadata,
    read_checkpoint_patch,
    read_checkpoint_untracked_manifest,
)
from .types import (
    CheckpointDiffObservation,
    CheckpointListObservation,
    CheckpointShowObservation,
    CheckpointStatusObservation,
)
from .workspace import RunWorkspace, read_git_diff, read_git_status


def list_checkpoints_observation(root: Path, max_entries: int = 20) -> CheckpointListObservation:
    checkpoints = read_checkpoint_infos(root)
    shown = checkpoints[:max_entries]
    return CheckpointListObservation(
        kind="checkpoint_list",
        ok=True,
        checkpoints=shown,
        total=len(checkpoints),
        message=f"Found {len(checkpoints)} checkpoint(s).",
    )


def checkpoint_show_observation(root: Path, checkpoint_id: str) -> CheckpointShowObservation:
    metadata, message = read_checkpoint_metadata(root, checkpoint_id)
    if metadata is None:
        return CheckpointShowObservation(
            kind="checkpoint_show",
            ok=False,
            checkpoint=None,
            project_root="",
            git_status="",
            untracked_saved_files=0,
            untracked_skipped_files=0,
            saved_untracked_paths=[],
            saved_untracked_paths_truncated=False,
            staged_patch_chars=0,
            unstaged_patch_chars=0,
            message=message,
        )
    info = checkpoint_info_from_metadata(metadata)
    if info is None:
        return CheckpointShowObservation(
            kind="checkpoint_show",
            ok=False,
            checkpoint=None,
            project_root=str(metadata.get("project_root") or ""),
            git_status="",
            untracked_saved_files=0,
            untracked_skipped_files=0,
            saved_untracked_paths=[],
            saved_untracked_paths_truncated=False,
            staged_patch_chars=0,
            unstaged_patch_chars=0,
            message=f"Checkpoint metadata is invalid: {checkpoint_id}",
        )
    saved_untracked_paths, saved_untracked_paths_truncated = clip_checkpoint_untracked_paths(
        [item["path"] for item in read_checkpoint_untracked_manifest(root, info.checkpoint_id)],
    )
    return CheckpointShowObservation(
        kind="checkpoint_show",
        ok=True,
        checkpoint=info,
        project_root=str(metadata.get("project_root") or ""),
        git_status=str(metadata.get("git_status") or ""),
        untracked_saved_files=int(metadata.get("untracked_saved_files") or 0),
        untracked_skipped_files=int(metadata.get("untracked_skipped_files") or 0),
        saved_untracked_paths=saved_untracked_paths,
        saved_untracked_paths_truncated=saved_untracked_paths_truncated,
        staged_patch_chars=int(metadata.get("staged_diff_chars") or 0),
        unstaged_patch_chars=int(metadata.get("unstaged_diff_chars") or 0),
        message=f"Read checkpoint {info.checkpoint_id}.",
    )


def checkpoint_diff_observation(root: Path, checkpoint_id: str, max_chars: int = 40_000) -> CheckpointDiffObservation:
    metadata, message = read_checkpoint_metadata(root, checkpoint_id)
    if metadata is None:
        return CheckpointDiffObservation(
            kind="checkpoint_diff",
            ok=False,
            checkpoint_id=checkpoint_id,
            label="",
            created_at="",
            staged_patch="",
            staged_patch_chars=0,
            staged_patch_truncated=False,
            unstaged_patch="",
            unstaged_patch_chars=0,
            unstaged_patch_truncated=False,
            max_chars=max_chars,
            message=message,
        )
    checkpoint_id = str(metadata.get("id") or checkpoint_id)
    staged_patch = read_checkpoint_patch(root, checkpoint_id, "staged.patch")
    unstaged_patch = read_checkpoint_patch(root, checkpoint_id, "unstaged.patch")
    staged_text, staged_truncated = clip_text_with_flag(staged_patch, max_chars)
    unstaged_text, unstaged_truncated = clip_text_with_flag(unstaged_patch, max_chars)
    return CheckpointDiffObservation(
        kind="checkpoint_diff",
        ok=True,
        checkpoint_id=checkpoint_id,
        label=str(metadata.get("label") or ""),
        created_at=str(metadata.get("created_at") or ""),
        staged_patch=staged_text,
        staged_patch_chars=len(staged_patch),
        staged_patch_truncated=staged_truncated,
        unstaged_patch=unstaged_text,
        unstaged_patch_chars=len(unstaged_patch),
        unstaged_patch_truncated=unstaged_truncated,
        max_chars=max_chars,
        message=f"Read checkpoint diff {checkpoint_id}.",
    )


def checkpoint_status_observation(workspace: RunWorkspace, checkpoint_id: str) -> CheckpointStatusObservation:
    metadata, message = read_checkpoint_metadata(workspace.root, checkpoint_id)
    if metadata is None:
        return empty_checkpoint_status(checkpoint_id, message)
    checkpoint_id = str(metadata.get("id") or checkpoint_id)
    status = read_git_status(workspace)
    staged = read_git_diff(workspace, staged=True)
    unstaged = read_git_diff(workspace, staged=False)
    if not status.ok or not staged.ok or not unstaged.ok:
        return empty_checkpoint_status(
            checkpoint_id,
            status.stderr or staged.stderr or unstaged.stderr or "git status/diff failed.",
        )
    saved_status = str(metadata.get("git_status") or "")
    saved_staged = read_checkpoint_patch(workspace.root, checkpoint_id, "staged.patch")
    saved_unstaged = read_checkpoint_patch(workspace.root, checkpoint_id, "unstaged.patch")
    untracked_matches = checkpoint_untracked_files_match(workspace.root, checkpoint_id, int(metadata.get("untracked_files") or 0))
    current_status = filter_checkpoint_status(status.stdout)
    current_counts = count_checkpoint_status_kinds(current_status)
    status_matches = current_status == saved_status
    staged_matches = staged.stdout == saved_staged
    unstaged_matches = unstaged.stdout == saved_unstaged
    matches = status_matches and staged_matches and unstaged_matches and untracked_matches
    return CheckpointStatusObservation(
        kind="checkpoint_status",
        ok=True,
        checkpoint_id=checkpoint_id,
        matches=matches,
        status_matches=status_matches,
        staged_patch_matches=staged_matches,
        unstaged_patch_matches=unstaged_matches,
        untracked_file_matches=untracked_matches,
        saved_changed_files=int(metadata.get("changed_files") or 0),
        saved_staged_files=int(metadata.get("staged_files") or 0),
        saved_unstaged_files=int(metadata.get("unstaged_files") or 0),
        saved_untracked_files=int(metadata.get("untracked_files") or 0),
        current_changed_files=current_counts["changed_files"],
        current_staged_files=current_counts["staged_files"],
        current_unstaged_files=current_counts["unstaged_files"],
        current_untracked_files=current_counts["untracked_files"],
        message="Current worktree matches checkpoint." if matches else "Current worktree differs from checkpoint.",
    )


def empty_checkpoint_status(checkpoint_id: str, message: str) -> CheckpointStatusObservation:
    return CheckpointStatusObservation(
        kind="checkpoint_status",
        ok=False,
        checkpoint_id=checkpoint_id,
        matches=False,
        status_matches=False,
        staged_patch_matches=False,
        unstaged_patch_matches=False,
        untracked_file_matches=False,
        saved_changed_files=0,
        saved_staged_files=0,
        saved_unstaged_files=0,
        saved_untracked_files=0,
        current_changed_files=0,
        current_staged_files=0,
        current_unstaged_files=0,
        current_untracked_files=0,
        message=message,
    )
