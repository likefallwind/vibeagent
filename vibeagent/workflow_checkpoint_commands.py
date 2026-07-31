from __future__ import annotations

import json
from pathlib import Path
import shutil

from .actions import execute_action
from .local_command_workspace import local_command_workspace
from .types import (
    CheckCheckpointDeleteAction,
    CheckCheckpointPruneAction,
    CheckCheckpointRestoreAction,
    CheckpointDeleteAction,
    CheckpointPruneAction,
    CheckpointRestoreAction,
)
from .workflow_checkpoint_create_commands import (
    build_checkpoint_create_report,
    create_local_checkpoint_metadata,
    get_checkpoint_report,
    get_checkpoint_text,
)
from .workflow_checkpoint_query_commands import (
    checkpoint_status_error_report,
    get_checkpoint_diff_report,
    get_checkpoint_diff_text,
    get_checkpoint_show_report,
    get_checkpoint_show_text,
    get_checkpoint_status_report,
    get_checkpoint_status_text,
    get_checkpoints_report,
    get_checkpoints_text,
    read_local_checkpoint_metadata,
    serialize_checkpoint_info,
    serialize_checkpoint_metadata,
)
from .workflow_checkpoint_utils import (
    parse_checkpoint_keep_last,
    resolve_checkpoint_dir,
)

CHECKPOINT_RESTORE_USAGE = "Usage: /checkpoint-restore <id>"
CHECK_CHECKPOINT_DELETE_USAGE = "Usage: /check-checkpoint-delete <id>"
CHECKPOINT_DELETE_USAGE = "Usage: /checkpoint-delete <id>"


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


def get_check_checkpoint_delete_report(checkpoint_id: str | None, project_root: str | Path = ".") -> dict[str, object]:
    root = Path(project_root).resolve()
    if not checkpoint_id or not checkpoint_id.strip():
        return {
            "projectRoot": str(root),
            "ok": False,
            "canDelete": False,
            "id": "",
            "label": "",
            "createdAt": "",
            "message": CHECK_CHECKPOINT_DELETE_USAGE,
        }
    workspace = local_command_workspace(root, "local-check-checkpoint-delete")
    observation = execute_action(workspace, CheckCheckpointDeleteAction(type="check_checkpoint_delete", checkpoint_id=checkpoint_id))
    return {
        "projectRoot": str(root),
        "ok": bool(observation.ok),
        "canDelete": bool(observation.can_delete),
        "id": observation.checkpoint_id,
        "label": observation.label,
        "createdAt": observation.created_at,
        "message": observation.message,
    }


def get_checkpoint_delete_text(checkpoint_id: str | None, project_root: str | Path = ".") -> str:
    if not checkpoint_id or not checkpoint_id.strip():
        return CHECKPOINT_DELETE_USAGE
    root = Path(project_root).resolve()
    try:
        checkpoint_dir = resolve_checkpoint_dir(root, checkpoint_id)
    except ValueError as error:
        return "\n".join(
            [
                "Checkpoint delete:",
                f"  projectRoot: {root}",
                "  deleted: no",
                f"  id: {checkpoint_id}",
                f"  message: {error}",
            ]
        )
    metadata_path = checkpoint_dir / "metadata.json"
    if not metadata_path.is_file():
        return "\n".join(
            [
                "Checkpoint delete:",
                f"  projectRoot: {root}",
                "  deleted: no",
                f"  id: {checkpoint_id}",
                f"  message: Checkpoint not found: {checkpoint_id}",
            ]
        )
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "\n".join(
            [
                "Checkpoint delete:",
                f"  projectRoot: {root}",
                "  deleted: no",
                f"  id: {checkpoint_id}",
                f"  message: Checkpoint metadata is unreadable: {checkpoint_id}",
            ]
        )
    if not isinstance(metadata, dict):
        return "\n".join(
            [
                "Checkpoint delete:",
                f"  projectRoot: {root}",
                "  deleted: no",
                f"  id: {checkpoint_id}",
                f"  message: Checkpoint metadata is invalid: {checkpoint_id}",
            ]
        )
    display_id = str(metadata.get("id") or checkpoint_id)
    label = str(metadata.get("label") or "")
    try:
        shutil.rmtree(checkpoint_dir)
    except OSError as error:
        deleted = False
        message = f"Failed to delete checkpoint {display_id}: {error}"
    else:
        deleted = True
        message = f"Deleted checkpoint {display_id}."
    lines = [
        "Checkpoint delete:",
        f"  projectRoot: {root}",
        f"  deleted: {'yes' if deleted else 'no'}",
        f"  id: {display_id}",
    ]
    if label or metadata.get("created_at"):
        lines.append(f"  label: {label}")
        lines.append(f"  createdAt: {metadata.get('created_at') or ''}")
    lines.append(f"  message: {message}")
    return "\n".join(lines)


def get_checkpoint_delete_report(checkpoint_id: str | None, project_root: str | Path = ".") -> dict[str, object]:
    root = Path(project_root).resolve()
    if not checkpoint_id or not checkpoint_id.strip():
        return {
            "projectRoot": str(root),
            "ok": False,
            "deleted": False,
            "id": "",
            "message": CHECKPOINT_DELETE_USAGE,
        }
    workspace = local_command_workspace(root, "local-checkpoint-delete")
    observation = execute_action(workspace, CheckpointDeleteAction(type="checkpoint_delete", checkpoint_id=checkpoint_id))
    return {
        "projectRoot": str(root),
        "ok": bool(observation.ok),
        "deleted": bool(observation.deleted),
        "id": observation.checkpoint_id,
        "message": observation.message,
    }


def get_check_checkpoint_prune_report(keep_last: str | int | None, project_root: str | Path = ".") -> dict[str, object]:
    parsed, error = parse_checkpoint_keep_last(keep_last, "/check-checkpoint-prune <keep-last>")
    root = Path(project_root).resolve()
    if error:
        return {
            "projectRoot": str(root),
            "ok": False,
            "keepLast": None,
            "total": 0,
            "kept": 0,
            "deleteCount": 0,
            "checkpoints": [],
            "message": error,
        }
    workspace = local_command_workspace(root, "local-check-checkpoint-prune")
    observation = execute_action(workspace, CheckCheckpointPruneAction(type="check_checkpoint_prune", keep_last=parsed))
    return {
        "projectRoot": str(root),
        "ok": bool(observation.ok),
        "keepLast": observation.keep_last,
        "total": observation.total,
        "kept": observation.kept,
        "deleteCount": observation.delete_count,
        "checkpoints": [serialize_checkpoint_info(checkpoint) for checkpoint in observation.checkpoints],
        "message": observation.message,
    }


def get_checkpoint_prune_report(keep_last: str | int | None, project_root: str | Path = ".") -> dict[str, object]:
    parsed, error = parse_checkpoint_keep_last(keep_last, "/checkpoint-prune <keep-last>")
    root = Path(project_root).resolve()
    if error:
        return {
            "projectRoot": str(root),
            "ok": False,
            "keepLast": None,
            "total": 0,
            "kept": 0,
            "deleted": 0,
            "checkpoints": [],
            "message": error,
        }
    workspace = local_command_workspace(root, "local-checkpoint-prune")
    observation = execute_action(workspace, CheckpointPruneAction(type="checkpoint_prune", keep_last=parsed))
    return {
        "projectRoot": str(root),
        "ok": bool(observation.ok),
        "keepLast": observation.keep_last,
        "total": observation.total,
        "kept": observation.kept,
        "deleted": observation.deleted,
        "checkpoints": [serialize_checkpoint_info(checkpoint) for checkpoint in observation.checkpoints],
        "message": observation.message,
    }
