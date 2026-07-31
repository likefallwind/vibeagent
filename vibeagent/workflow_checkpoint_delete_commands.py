from __future__ import annotations

import json
from pathlib import Path
import shutil

from .actions import execute_action
from .local_command_workspace import local_command_workspace
from .types import CheckCheckpointDeleteAction, CheckpointDeleteAction
from .workflow_checkpoint_utils import resolve_checkpoint_dir

CHECK_CHECKPOINT_DELETE_USAGE = "Usage: /check-checkpoint-delete <id>"
CHECKPOINT_DELETE_USAGE = "Usage: /checkpoint-delete <id>"


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
