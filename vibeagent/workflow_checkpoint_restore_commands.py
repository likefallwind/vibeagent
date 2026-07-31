from __future__ import annotations

from pathlib import Path

from .actions import execute_action
from .local_command_workspace import local_command_workspace
from .types import CheckCheckpointRestoreAction, CheckpointRestoreAction

CHECKPOINT_RESTORE_USAGE = "Usage: /checkpoint-restore <id>"


def get_check_checkpoint_restore_report(checkpoint_id: str | None, project_root: str | Path = ".") -> dict[str, object]:
    root = Path(project_root).resolve()
    if not checkpoint_id or not checkpoint_id.strip():
        return {
            "projectRoot": str(root),
            "ok": False,
            "canRestore": False,
            "id": "",
            "label": "",
            "createdAt": "",
            "savedHead": "",
            "currentHead": "",
            "saved": {"changedFiles": 0, "stagedFiles": 0, "unstagedFiles": 0, "untrackedFiles": 0, "stagedPatchChars": 0, "unstagedPatchChars": 0},
            "current": {"changedFiles": 0, "stagedFiles": 0, "unstagedFiles": 0, "untrackedFiles": 0},
            "message": CHECKPOINT_RESTORE_USAGE,
        }
    workspace = local_command_workspace(root, "local-check-checkpoint-restore")
    observation = execute_action(workspace, CheckCheckpointRestoreAction(type="check_checkpoint_restore", checkpoint_id=checkpoint_id))
    return {
        "projectRoot": str(root),
        "ok": bool(observation.ok),
        "canRestore": bool(observation.can_restore),
        "id": observation.checkpoint_id,
        "label": "",
        "createdAt": "",
        "savedHead": observation.saved_head,
        "currentHead": observation.current_head,
        "saved": {
            "changedFiles": 0,
            "stagedFiles": 0,
            "unstagedFiles": 0,
            "untrackedFiles": observation.saved_untracked_files,
            "stagedPatchChars": observation.staged_patch_chars,
            "unstagedPatchChars": observation.unstaged_patch_chars,
        },
        "current": {
            "changedFiles": 0,
            "stagedFiles": 0,
            "unstagedFiles": 0,
            "untrackedFiles": observation.current_untracked_files,
        },
        "message": observation.message,
    }


def get_checkpoint_restore_report(checkpoint_id: str | None, project_root: str | Path = ".") -> dict[str, object]:
    root = Path(project_root).resolve()
    if not checkpoint_id or not checkpoint_id.strip():
        return {
            "projectRoot": str(root),
            "ok": False,
            "restored": False,
            "matches": False,
            "id": "",
            "savedHead": "",
            "currentHead": "",
            "saved": {"untrackedFiles": 0, "stagedPatchChars": 0, "unstagedPatchChars": 0},
            "current": {"untrackedFiles": 0},
            "message": CHECKPOINT_RESTORE_USAGE,
        }
    workspace = local_command_workspace(root, "local-checkpoint-restore")
    observation = execute_action(workspace, CheckpointRestoreAction(type="checkpoint_restore", checkpoint_id=checkpoint_id))
    return {
        "projectRoot": str(root),
        "ok": bool(observation.ok),
        "restored": bool(observation.restored),
        "matches": bool(observation.matches),
        "id": observation.checkpoint_id,
        "savedHead": observation.saved_head,
        "currentHead": observation.current_head,
        "saved": {
            "untrackedFiles": observation.saved_untracked_files,
            "stagedPatchChars": observation.staged_patch_chars,
            "unstagedPatchChars": observation.unstaged_patch_chars,
        },
        "current": {
            "untrackedFiles": observation.current_untracked_files,
        },
        "message": observation.message,
    }
