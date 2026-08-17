from __future__ import annotations

from .checkpoint_query_actions import checkpoint_status_observation
from .checkpoint_storage import (
    check_checkpoint_untracked_restore_files,
    checkpoint_untracked_paths,
    checkpoint_file_for_read,
    count_checkpoint_status_kinds,
    filter_checkpoint_status,
    read_checkpoint_git_head,
    read_checkpoint_metadata,
    read_checkpoint_untracked_paths,
    restore_checkpoint_untracked_files,
    run_checkpoint_git_command,
    short_checkpoint_head,
)
from .types import (
    CheckCheckpointRestoreObservation,
    CheckpointRestoreObservation,
)
from .workspace import (
    RunWorkspace,
    read_git_status,
)


def check_checkpoint_restore_observation(workspace: RunWorkspace, checkpoint_id: str) -> CheckCheckpointRestoreObservation:
    metadata, message = read_checkpoint_metadata(workspace.root, checkpoint_id)
    if metadata is None:
        return empty_check_checkpoint_restore(checkpoint_id, message)
    checkpoint_id = str(metadata.get("id") or checkpoint_id)
    status = read_git_status(workspace)
    if not status.ok:
        return empty_check_checkpoint_restore(checkpoint_id, status.stderr or "git status failed.")
    current_head = read_checkpoint_git_head(workspace.root)
    saved_head = metadata.get("head")
    current_counts = count_checkpoint_status_kinds(filter_checkpoint_status(status.stdout))
    saved_untracked = int(metadata.get("untracked_files") or 0)
    saved_untracked_paths = read_checkpoint_untracked_paths(workspace.root, checkpoint_id)
    current_untracked_paths = set(checkpoint_untracked_paths(filter_checkpoint_status(status.stdout)))
    staged_patch = checkpoint_file_for_read(workspace.root, checkpoint_id, "staged.patch")
    unstaged_patch = checkpoint_file_for_read(workspace.root, checkpoint_id, "unstaged.patch")
    can_restore = True
    restore_message = "Checkpoint can restore tracked staged/unstaged changes and saved untracked files."
    if not isinstance(saved_head, str) or not saved_head:
        can_restore = False
        restore_message = "Checkpoint does not record HEAD; create a new checkpoint before using restore."
    elif current_head != saved_head:
        can_restore = False
        restore_message = f"Checkpoint was created at HEAD {short_checkpoint_head(saved_head)}, but current HEAD is {short_checkpoint_head(current_head)}."
    elif staged_patch is None or unstaged_patch is None:
        can_restore = False
        restore_message = "Checkpoint patch files are missing or unsafe."
    elif saved_untracked and len(saved_untracked_paths) != saved_untracked:
        can_restore = False
        restore_message = "Checkpoint contains untracked files that were not fully saved."
    elif current_untracked_paths - saved_untracked_paths:
        can_restore = False
        restore_message = "Current worktree contains extra untracked files; move, delete, or commit them before checkpoint restore."
    else:
        untracked_restore_error = check_checkpoint_untracked_restore_files(workspace.root, checkpoint_id)
        if untracked_restore_error:
            can_restore = False
            restore_message = untracked_restore_error
    return CheckCheckpointRestoreObservation(
        kind="check_checkpoint_restore",
        ok=can_restore,
        checkpoint_id=checkpoint_id,
        can_restore=can_restore,
        saved_head=saved_head if isinstance(saved_head, str) else "",
        current_head=current_head,
        saved_untracked_files=saved_untracked,
        current_untracked_files=current_counts["untracked_files"],
        staged_patch_chars=int(metadata.get("staged_diff_chars") or 0),
        unstaged_patch_chars=int(metadata.get("unstaged_diff_chars") or 0),
        message=restore_message,
    )


def checkpoint_restore_observation(workspace: RunWorkspace, checkpoint_id: str) -> CheckpointRestoreObservation:
    restore_check = check_checkpoint_restore_observation(workspace, checkpoint_id)
    if not restore_check.ok:
        return CheckpointRestoreObservation(
            kind="checkpoint_restore",
            ok=False,
            checkpoint_id=restore_check.checkpoint_id,
            restored=False,
            matches=False,
            saved_head=restore_check.saved_head,
            current_head=restore_check.current_head,
            saved_untracked_files=restore_check.saved_untracked_files,
            current_untracked_files=restore_check.current_untracked_files,
            staged_patch_chars=restore_check.staged_patch_chars,
            unstaged_patch_chars=restore_check.unstaged_patch_chars,
            message=restore_check.message,
        )

    restored_id = restore_check.checkpoint_id
    staged_patch = checkpoint_file_for_read(workspace.root, restored_id, "staged.patch")
    unstaged_patch = checkpoint_file_for_read(workspace.root, restored_id, "unstaged.patch")
    if staged_patch is None or unstaged_patch is None:
        return CheckpointRestoreObservation(
            kind="checkpoint_restore",
            ok=False,
            checkpoint_id=restore_check.checkpoint_id,
            restored=False,
            matches=False,
            saved_head=restore_check.saved_head,
            current_head=restore_check.current_head,
            saved_untracked_files=restore_check.saved_untracked_files,
            current_untracked_files=restore_check.current_untracked_files,
            staged_patch_chars=restore_check.staged_patch_chars,
            unstaged_patch_chars=restore_check.unstaged_patch_chars,
            message="Checkpoint patch files are missing or unsafe.",
        )
    steps: list[list[str]] = [["restore", "--staged", "--worktree", "--", "."]]
    if staged_patch.stat().st_size:
        steps.extend(
            [
                ["apply", "--check", "--whitespace=nowarn", str(staged_patch)],
                ["apply", "--cached", "--check", "--whitespace=nowarn", str(staged_patch)],
                ["apply", "--whitespace=nowarn", str(staged_patch)],
                ["apply", "--cached", "--whitespace=nowarn", str(staged_patch)],
            ]
        )
    if unstaged_patch.stat().st_size:
        steps.extend(
            [
                ["apply", "--check", "--whitespace=nowarn", str(unstaged_patch)],
                ["apply", "--whitespace=nowarn", str(unstaged_patch)],
            ]
        )

    for args in steps:
        result = run_checkpoint_git_command(workspace.root, args)
        if result.returncode != 0:
            return CheckpointRestoreObservation(
                kind="checkpoint_restore",
                ok=False,
                checkpoint_id=restore_check.checkpoint_id,
                restored=False,
                matches=False,
                saved_head=restore_check.saved_head,
                current_head=restore_check.current_head,
                saved_untracked_files=restore_check.saved_untracked_files,
                current_untracked_files=restore_check.current_untracked_files,
                staged_patch_chars=restore_check.staged_patch_chars,
                unstaged_patch_chars=restore_check.unstaged_patch_chars,
                message=(
                    f"Failed to restore checkpoint while running git {' '.join(args)}: "
                    f"{result.stderr.strip() or result.stdout.strip() or 'unknown error'}"
                ),
            )

    restore_untracked_error = restore_checkpoint_untracked_files(workspace.root, restored_id)
    if restore_untracked_error:
        return CheckpointRestoreObservation(
            kind="checkpoint_restore",
            ok=False,
            checkpoint_id=restore_check.checkpoint_id,
            restored=False,
            matches=False,
            saved_head=restore_check.saved_head,
            current_head=restore_check.current_head,
            saved_untracked_files=restore_check.saved_untracked_files,
            current_untracked_files=restore_check.current_untracked_files,
            staged_patch_chars=restore_check.staged_patch_chars,
            unstaged_patch_chars=restore_check.unstaged_patch_chars,
            message=restore_untracked_error,
        )

    status = checkpoint_status_observation(workspace, restored_id)
    current_head = read_checkpoint_git_head(workspace.root)
    return CheckpointRestoreObservation(
        kind="checkpoint_restore",
        ok=status.ok and status.matches,
        checkpoint_id=restore_check.checkpoint_id,
        restored=status.ok and status.matches,
        matches=status.matches if status.ok else False,
        saved_head=restore_check.saved_head,
        current_head=current_head,
        saved_untracked_files=restore_check.saved_untracked_files,
        current_untracked_files=status.current_untracked_files if status.ok else restore_check.current_untracked_files,
        staged_patch_chars=restore_check.staged_patch_chars,
        unstaged_patch_chars=restore_check.unstaged_patch_chars,
        message=(
            "Restored tracked staged/unstaged changes and saved untracked files from checkpoint."
            if status.ok and status.matches
            else status.message
        ),
    )


def empty_check_checkpoint_restore(checkpoint_id: str, message: str) -> CheckCheckpointRestoreObservation:
    return CheckCheckpointRestoreObservation(
        kind="check_checkpoint_restore",
        ok=False,
        checkpoint_id=checkpoint_id,
        can_restore=False,
        saved_head="",
        current_head="",
        saved_untracked_files=0,
        current_untracked_files=0,
        staged_patch_chars=0,
        unstaged_patch_chars=0,
        message=message,
    )
