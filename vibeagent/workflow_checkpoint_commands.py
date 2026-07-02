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
    CheckpointInfo,
    CheckpointPruneAction,
    CheckpointRestoreAction,
)
from .workflow_checkpoint_formatting import (
    format_checkpoint_create_report_text,
    format_checkpoint_diff_report_text,
    format_checkpoint_show_report_text,
    format_checkpoint_status_report_text,
    format_checkpoints_report_text,
)
from .workflow_checkpoint_utils import (
    checkpoint_root,
    clip_local_checkpoint_untracked_paths,
    count_status_kinds,
    display_checkpoint_file,
    local_checkpoint_untracked_files_match,
    normalize_checkpoint_label,
    parse_checkpoint_keep_last,
    read_checkpoint_patch,
    read_checkpoints,
    read_git_head,
    read_local_checkpoint_untracked_manifest,
    resolve_checkpoint_dir,
    save_local_checkpoint_untracked_files,
    short_head,
)
from .workflow_diff_commands import clip_with_flag
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


def serialize_checkpoint_metadata(metadata: dict[str, object]) -> dict[str, object]:
    return {
        "id": str(metadata.get("id") or ""),
        "label": str(metadata.get("label") or ""),
        "createdAt": str(metadata.get("created_at") or ""),
        "projectRoot": str(metadata.get("project_root") or ""),
        "head": str(metadata.get("head") or ""),
        "shortHead": short_head(str(metadata.get("head") or "")),
        "changedFiles": int(metadata.get("changed_files") or 0),
        "stagedFiles": int(metadata.get("staged_files") or 0),
        "unstagedFiles": int(metadata.get("unstaged_files") or 0),
        "untrackedFiles": int(metadata.get("untracked_files") or 0),
        "untrackedSavedFiles": int(metadata.get("untracked_saved_files") or 0),
        "untrackedSkippedFiles": int(metadata.get("untracked_skipped_files") or 0),
        "stagedPatchChars": int(metadata.get("staged_diff_chars") or 0),
        "unstagedPatchChars": int(metadata.get("unstaged_diff_chars") or 0),
    }


def serialize_checkpoint_info(info: CheckpointInfo) -> dict[str, object]:
    return {
        "id": info.checkpoint_id,
        "label": info.label,
        "createdAt": info.created_at,
        "head": info.head,
        "shortHead": short_head(info.head),
        "changedFiles": info.changed_files,
        "stagedFiles": info.staged_files,
        "unstagedFiles": info.unstaged_files,
        "untrackedFiles": info.untracked_files,
    }


def get_checkpoints_report(project_root: str | Path = ".") -> dict[str, object]:
    root = Path(project_root).resolve()
    checkpoints = read_checkpoints(root)
    return {
        "projectRoot": str(root),
        "ok": True,
        "total": len(checkpoints),
        "checkpoints": [serialize_checkpoint_metadata(metadata) for metadata in checkpoints],
        "message": f"Found {len(checkpoints)} checkpoint(s).",
    }


def get_checkpoints_text(project_root: str | Path = ".") -> str:
    return format_checkpoints_report_text(get_checkpoints_report(project_root))


def read_local_checkpoint_metadata(root: Path, checkpoint_id: str | None, usage: str) -> tuple[Path | None, dict[str, object] | None, str]:
    if not checkpoint_id or not checkpoint_id.strip():
        return None, None, f"Usage: {usage}"
    try:
        checkpoint_dir = resolve_checkpoint_dir(root, checkpoint_id)
    except ValueError as error:
        return None, None, str(error)
    metadata_path = checkpoint_dir / "metadata.json"
    if not metadata_path.is_file():
        return checkpoint_dir, None, f"Checkpoint not found: {checkpoint_id}"
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return checkpoint_dir, None, f"Checkpoint metadata is unreadable: {checkpoint_id}"
    if not isinstance(metadata, dict):
        return checkpoint_dir, None, f"Checkpoint metadata is invalid: {checkpoint_id}"
    return checkpoint_dir, metadata, ""


def get_checkpoint_show_report(checkpoint_id: str | None, project_root: str | Path = ".") -> dict[str, object]:
    root = Path(project_root).resolve()
    checkpoint_dir, metadata, error = read_local_checkpoint_metadata(root, checkpoint_id, "/checkpoint-show <id>")
    if metadata is None:
        return {
            "projectRoot": str(root),
            "ok": False,
            "exists": False,
            "checkpoint": None,
            "gitStatus": "",
            "savedUntrackedPaths": {"shown": [], "truncated": False},
            "message": error,
        }
    status = str(metadata.get("git_status") or "")
    saved_untracked_paths, saved_untracked_paths_truncated = clip_local_checkpoint_untracked_paths(
        [item["path"] for item in read_local_checkpoint_untracked_manifest(checkpoint_dir or root)],
    )
    return {
        "projectRoot": str(root),
        "ok": True,
        "exists": True,
        "checkpoint": serialize_checkpoint_metadata(metadata),
        "patches": {
            "unstagedPath": display_checkpoint_file(root, (checkpoint_dir or root) / "unstaged.patch"),
            "stagedPath": display_checkpoint_file(root, (checkpoint_dir or root) / "staged.patch"),
            "unstagedChars": int(metadata.get("unstaged_diff_chars") or 0),
            "stagedChars": int(metadata.get("staged_diff_chars") or 0),
        },
        "gitStatus": status,
        "savedUntrackedPaths": {
            "shown": saved_untracked_paths,
            "truncated": saved_untracked_paths_truncated,
        },
        "message": f"Read checkpoint {metadata.get('id') or checkpoint_id}.",
    }


def get_checkpoint_show_text(checkpoint_id: str | None, project_root: str | Path = ".") -> str:
    return format_checkpoint_show_report_text(get_checkpoint_show_report(checkpoint_id, project_root))


def get_checkpoint_diff_report(
    checkpoint_id: str | None,
    project_root: str | Path = ".",
    max_chars: int = 40_000,
) -> dict[str, object]:
    if max_chars < 100:
        raise ValueError("max_chars must be at least 100.")
    if max_chars > 200_000:
        raise ValueError("max_chars must be at most 200000.")
    root = Path(project_root).resolve()
    checkpoint_dir, metadata, error = read_local_checkpoint_metadata(root, checkpoint_id, "/checkpoint-diff <id>")
    if metadata is None:
        return {
            "projectRoot": str(root),
            "ok": False,
            "exists": False,
            "id": checkpoint_id or "",
            "diff": None,
            "message": error,
        }
    staged = read_checkpoint_patch((checkpoint_dir or root) / "staged.patch")
    unstaged = read_checkpoint_patch((checkpoint_dir or root) / "unstaged.patch")
    staged_text, staged_truncated = clip_with_flag(staged, max_chars)
    unstaged_text, unstaged_truncated = clip_with_flag(unstaged, max_chars)
    return {
        "projectRoot": str(root),
        "ok": True,
        "exists": True,
        "checkpoint": serialize_checkpoint_metadata(metadata),
        "diff": {
            "maxChars": max_chars,
            "stagedPatch": staged_text,
            "stagedChars": len(staged),
            "stagedTruncated": staged_truncated,
            "unstagedPatch": unstaged_text,
            "unstagedChars": len(unstaged),
            "unstagedTruncated": unstaged_truncated,
        },
        "message": f"Read checkpoint diff {metadata.get('id') or checkpoint_id}.",
    }


def get_checkpoint_diff_text(checkpoint_id: str | None, project_root: str | Path = ".", max_chars: int = 40_000) -> str:
    return format_checkpoint_diff_report_text(get_checkpoint_diff_report(checkpoint_id, project_root, max_chars=max_chars))


def get_checkpoint_status_report(checkpoint_id: str | None, project_root: str | Path = ".") -> dict[str, object]:
    root = Path(project_root).resolve()
    checkpoint_dir, metadata, error = read_local_checkpoint_metadata(root, checkpoint_id, "/checkpoint-status <id>")
    if metadata is None:
        return {
            "projectRoot": str(root),
            "ok": False,
            "exists": False,
            "id": checkpoint_id or "",
            "matches": False,
            "message": error,
        }
    workspace = RunWorkspace(root=root, run_id="local-checkpoint-status", session_dir=root / ".vibeagent" / "sessions" / "local-checkpoint-status")
    status = read_git_status(workspace)
    if not status.ok:
        return checkpoint_status_error_report(root, metadata, status.stderr or "git status failed.")
    staged = read_git_diff(workspace, staged=True)
    if not staged.ok:
        return checkpoint_status_error_report(root, metadata, staged.stderr or "git diff --staged failed.")
    unstaged = read_git_diff(workspace, staged=False)
    if not unstaged.ok:
        return checkpoint_status_error_report(root, metadata, unstaged.stderr or "git diff failed.")

    saved_status = str(metadata.get("git_status") or "")
    saved_staged = read_checkpoint_patch((checkpoint_dir or root) / "staged.patch")
    saved_unstaged = read_checkpoint_patch((checkpoint_dir or root) / "unstaged.patch")
    current_status = filter_handoff_status(status.stdout)
    current_counts = count_status_kinds(current_status)
    status_matches = current_status == saved_status
    staged_matches = staged.stdout == saved_staged
    unstaged_matches = unstaged.stdout == saved_unstaged
    untracked_matches = local_checkpoint_untracked_files_match(root, checkpoint_dir or root, int(metadata.get("untracked_files") or 0))
    matches = status_matches and staged_matches and unstaged_matches and untracked_matches
    return {
        "projectRoot": str(root),
        "ok": True,
        "exists": True,
        "checkpoint": serialize_checkpoint_metadata(metadata),
        "matches": matches,
        "checks": {
            "statusMatches": status_matches,
            "stagedPatchMatches": staged_matches,
            "unstagedPatchMatches": unstaged_matches,
            "untrackedFileMatches": untracked_matches,
        },
        "saved": {
            "changedFiles": int(metadata.get("changed_files") or 0),
            "stagedFiles": int(metadata.get("staged_files") or 0),
            "unstagedFiles": int(metadata.get("unstaged_files") or 0),
            "untrackedFiles": int(metadata.get("untracked_files") or 0),
            "stagedPatchChars": len(saved_staged),
            "unstagedPatchChars": len(saved_unstaged),
        },
        "current": {
            "changedFiles": current_counts["changed_files"],
            "stagedFiles": current_counts["staged_files"],
            "unstagedFiles": current_counts["unstaged_files"],
            "untrackedFiles": current_counts["untracked_files"],
            "stagedPatchChars": len(staged.stdout),
            "unstagedPatchChars": len(unstaged.stdout),
        },
        "message": "Current worktree matches checkpoint." if matches else "Current worktree differs from checkpoint.",
    }


def checkpoint_status_error_report(root: Path, metadata: dict[str, object], message: str) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "exists": True,
        "checkpoint": serialize_checkpoint_metadata(metadata),
        "matches": False,
        "checks": {
            "statusMatches": False,
            "stagedPatchMatches": False,
            "unstagedPatchMatches": False,
            "untrackedFileMatches": False,
        },
        "saved": {},
        "current": {},
        "message": message,
    }


def get_checkpoint_status_text(checkpoint_id: str | None, project_root: str | Path = ".") -> str:
    return format_checkpoint_status_report_text(get_checkpoint_status_report(checkpoint_id, project_root))


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
