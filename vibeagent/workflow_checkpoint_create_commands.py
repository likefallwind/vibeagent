from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

from .local_command_workspace import local_command_workspace
from .workflow_checkpoint_formatting import format_checkpoint_create_report_text
from .workflow_checkpoint_query_commands import serialize_checkpoint_metadata
from .workflow_checkpoint_utils import (
    checkpoint_root,
    count_status_kinds,
    normalize_checkpoint_label,
    read_git_head,
    save_local_checkpoint_untracked_files,
)
from .workflow_review_formatting import filter_handoff_status
from .workspace import make_run_id, read_git_diff, read_git_status


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
    workspace = local_command_workspace(root, "local-checkpoint")
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
