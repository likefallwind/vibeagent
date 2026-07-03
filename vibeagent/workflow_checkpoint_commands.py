from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import shutil

from .actions import execute_action
from .types import (
    CheckCheckpointDeleteAction,
    CheckCheckpointPruneAction,
    CheckCheckpointRestoreAction,
    CheckpointDeleteAction,
    CheckpointPruneAction,
    CheckpointRestoreAction,
)
from .workflow_checkpoint_formatting import (
    format_checkpoint_create_report_text,
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
    checkpoint_root,
    count_status_kinds,
    normalize_checkpoint_label,
    parse_checkpoint_keep_last,
    read_git_head,
    resolve_checkpoint_dir,
    save_local_checkpoint_untracked_files,
)
from .workflow_review_formatting import filter_handoff_status
from .workspace import make_run_id, read_git_diff, read_git_status
from .workspace_core import RunWorkspace


def get_checkpoint_report(project_root: str | Path = ".", label: str | None = None) -> dict[str, object]:
    return build_checkpoint_create_report(project_root, label=label)


def build_checkpoint_create_report(project_root: str | Path = ".", label: str | None = None) -> dict[str, object]:
    root = Path(project_root).resolve()
    metadata, message = create_local_checkpoint_metadata(root, label)
    if metadata is None:
        return {
            "projectRoot": str(root),
            "ok": False,
            "created": False,
            "checkpoint": None,
            "patches": {"stagedChars": 0, "unstagedChars": 0},
            "message": message,
        }
    return {
        "projectRoot": str(root),
        "ok": True,
        "created": True,
        "checkpoint": serialize_checkpoint_metadata(metadata),
        "patches": {
            "stagedChars": int(metadata.get("staged_diff_chars") or 0),
            "unstagedChars": int(metadata.get("unstaged_diff_chars") or 0),
        },
        "message": "Saved checkpoint metadata, patch files, and ordinary untracked files under .vibeagent/checkpoints.",
    }


def get_checkpoint_text(project_root: str | Path = ".", label: str | None = None) -> str:
    return format_checkpoint_create_report_text(get_checkpoint_report(project_root, label=label))


def create_local_checkpoint_metadata(root: Path, label: str | None = None) -> tuple[dict[str, object] | None, str]:
    workspace = RunWorkspace(root=root, run_id="local-checkpoint", session_dir=root / ".vibeagent" / "sessions" / "local-checkpoint")
    status = read_git_status(workspace)
    if not status.ok:
        return None, status.stderr or "git status failed."

    unstaged = read_git_diff(workspace, staged=False)
    staged = read_git_diff(workspace, staged=True)
    if not unstaged.ok:
        return None, unstaged.stderr or "git diff failed."
    if not staged.ok:
        return None, staged.stderr or "git diff --staged failed."
    head = read_git_head(root)
    if not head:
        return None, "git rev-parse HEAD failed."

    checkpoint_id = make_run_id()
    checkpoint_dir = checkpoint_root(root) / checkpoint_id
    checkpoint_dir.mkdir(parents=True, exist_ok=False)
    filtered_status = filter_handoff_status(status.stdout)
    counts = count_status_kinds(filtered_status)
    metadata = {
        "id": checkpoint_id,
        "label": normalize_checkpoint_label(label),
        "created_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "project_root": str(root),
        "head": head,
        "git_status": filtered_status,
        "changed_files": counts["changed_files"],
        "staged_files": counts["staged_files"],
        "unstaged_files": counts["unstaged_files"],
        "untracked_files": counts["untracked_files"],
        "unstaged_diff_chars": len(unstaged.stdout),
        "staged_diff_chars": len(staged.stdout),
    }
    saved_untracked, skipped_untracked = save_local_checkpoint_untracked_files(root, checkpoint_dir, filtered_status)
    metadata["untracked_saved_files"] = saved_untracked
    metadata["untracked_skipped_files"] = skipped_untracked
    (checkpoint_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (checkpoint_dir / "unstaged.patch").write_text(unstaged.stdout, encoding="utf-8")
    (checkpoint_dir / "staged.patch").write_text(staged.stdout, encoding="utf-8")
    return metadata, "Saved checkpoint metadata, patch files, and ordinary untracked files under .vibeagent/checkpoints."


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
            "message": "Usage: /checkpoint-restore <id>",
        }
    workspace = RunWorkspace(root=root, run_id="local-check-checkpoint-restore", session_dir=root / ".vibeagent" / "sessions" / "local-check-checkpoint-restore")
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
            "message": "Usage: /checkpoint-restore <id>",
        }
    workspace = RunWorkspace(root=root, run_id="local-checkpoint-restore", session_dir=root / ".vibeagent" / "sessions" / "local-checkpoint-restore")
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
            "message": "Usage: /check-checkpoint-delete <id>",
        }
    workspace = RunWorkspace(root=root, run_id="local-check-checkpoint-delete", session_dir=root / ".vibeagent" / "sessions" / "local-check-checkpoint-delete")
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
        return "Usage: /checkpoint-delete <id>"
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
            "message": "Usage: /checkpoint-delete <id>",
        }
    workspace = RunWorkspace(root=root, run_id="local-checkpoint-delete", session_dir=root / ".vibeagent" / "sessions" / "local-checkpoint-delete")
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
    workspace = RunWorkspace(root=root, run_id="local-check-checkpoint-prune", session_dir=root / ".vibeagent" / "sessions" / "local-check-checkpoint-prune")
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
    workspace = RunWorkspace(root=root, run_id="local-checkpoint-prune", session_dir=root / ".vibeagent" / "sessions" / "local-checkpoint-prune")
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
