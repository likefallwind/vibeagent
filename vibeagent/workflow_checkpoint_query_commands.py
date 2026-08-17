from __future__ import annotations

import json
from pathlib import Path

from .checkpoint_patch_io import (
    MAX_CHECKPOINT_STATUS_CHARS,
    compare_checkpoint_patches,
    read_checkpoint_patch_excerpt,
)
from .local_command_workspace import local_command_workspace
from .types import CheckpointInfo
from .workflow_checkpoint_formatting import (
    format_checkpoint_diff_report_text,
    format_checkpoint_show_report_text,
    format_checkpoint_status_report_text,
    format_checkpoints_report_text,
)
from .workflow_checkpoint_utils import (
    clip_local_checkpoint_untracked_paths,
    count_status_kinds,
    display_checkpoint_file,
    local_checkpoint_untracked_files_match,
    read_checkpoints,
    read_local_checkpoint_untracked_manifest,
    resolve_checkpoint_dir,
    short_head,
)
from .workflow_review_formatting import filter_handoff_status
from .workspace import read_git_status


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
        "sessionRunId": str(metadata.get("session_run_id") or ""),
        "sessionEventLine": int(metadata.get("session_event_line") or 0),
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
    staged_text, staged_chars, staged_truncated = read_checkpoint_patch_excerpt(
        (checkpoint_dir or root) / "staged.patch",
        max_chars,
    )
    unstaged_text, unstaged_chars, unstaged_truncated = read_checkpoint_patch_excerpt(
        (checkpoint_dir or root) / "unstaged.patch",
        max_chars,
    )
    return {
        "projectRoot": str(root),
        "ok": True,
        "exists": True,
        "checkpoint": serialize_checkpoint_metadata(metadata),
        "diff": {
            "maxChars": max_chars,
            "stagedPatch": staged_text,
            "stagedChars": staged_chars,
            "stagedTruncated": staged_truncated,
            "unstagedPatch": unstaged_text,
            "unstagedChars": unstaged_chars,
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
    workspace = local_command_workspace(root, "local-checkpoint-status")
    status = read_git_status(workspace, max_output_chars=MAX_CHECKPOINT_STATUS_CHARS)
    if not status.ok or status.stdout_truncated:
        message = status.stderr or (
            f"git status output exceeded {MAX_CHECKPOINT_STATUS_CHARS} characters."
            if status.stdout_truncated
            else "git status failed."
        )
        return checkpoint_status_error_report(root, metadata, message)

    saved_status = str(metadata.get("git_status") or "")
    saved_staged = (checkpoint_dir or root) / "staged.patch"
    saved_unstaged = (checkpoint_dir or root) / "unstaged.patch"
    comparison = compare_checkpoint_patches(root, saved_staged, saved_unstaged)
    if not comparison.ok:
        return checkpoint_status_error_report(root, metadata, comparison.error)
    current_status = filter_handoff_status(status.stdout)
    current_counts = count_status_kinds(current_status)
    status_matches = current_status == saved_status
    untracked_matches = local_checkpoint_untracked_files_match(
        root,
        checkpoint_dir or root,
        int(metadata.get("untracked_files") or 0),
    )
    matches = (
        status_matches
        and comparison.staged_matches
        and comparison.unstaged_matches
        and untracked_matches
    )
    return {
        "projectRoot": str(root),
        "ok": True,
        "exists": True,
        "checkpoint": serialize_checkpoint_metadata(metadata),
        "matches": matches,
        "checks": {
            "statusMatches": status_matches,
            "stagedPatchMatches": comparison.staged_matches,
            "unstagedPatchMatches": comparison.unstaged_matches,
            "untrackedFileMatches": untracked_matches,
        },
        "saved": {
            "changedFiles": int(metadata.get("changed_files") or 0),
            "stagedFiles": int(metadata.get("staged_files") or 0),
            "unstagedFiles": int(metadata.get("unstaged_files") or 0),
            "untrackedFiles": int(metadata.get("untracked_files") or 0),
            "stagedPatchChars": int(metadata.get("staged_diff_chars") or 0),
            "unstagedPatchChars": int(metadata.get("unstaged_diff_chars") or 0),
        },
        "current": {
            "changedFiles": current_counts["changed_files"],
            "stagedFiles": current_counts["staged_files"],
            "unstagedFiles": current_counts["unstaged_files"],
            "untrackedFiles": current_counts["untracked_files"],
            "stagedPatchChars": comparison.staged_chars,
            "unstagedPatchChars": comparison.unstaged_chars,
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
