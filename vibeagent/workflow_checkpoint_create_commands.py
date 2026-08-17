from __future__ import annotations

from pathlib import Path

from .checkpoint_create_actions import create_checkpoint_observation
from .checkpoint_storage import read_checkpoint_metadata
from .local_command_workspace import local_command_workspace
from .workflow_checkpoint_formatting import format_checkpoint_create_report_text
from .workflow_checkpoint_query_commands import serialize_checkpoint_metadata


def get_checkpoint_report(
    project_root: str | Path = ".",
    label: str | None = None,
    session_run_id: str | None = None,
) -> dict[str, object]:
    return build_checkpoint_create_report(project_root, label=label, session_run_id=session_run_id)


def build_checkpoint_create_report(
    project_root: str | Path = ".",
    label: str | None = None,
    session_run_id: str | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    metadata, message = create_local_checkpoint_metadata(root, label, session_run_id=session_run_id)
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


def get_checkpoint_text(
    project_root: str | Path = ".",
    label: str | None = None,
    session_run_id: str | None = None,
) -> str:
    return format_checkpoint_create_report_text(
        get_checkpoint_report(project_root, label=label, session_run_id=session_run_id)
    )


def create_local_checkpoint_metadata(
    root: Path,
    label: str | None = None,
    session_run_id: str | None = None,
) -> tuple[dict[str, object] | None, str]:
    workspace = local_command_workspace(root, session_run_id or "local-checkpoint")
    observation = create_checkpoint_observation(workspace, label)
    if not observation.ok or observation.checkpoint is None:
        return None, observation.message
    metadata, message = read_checkpoint_metadata(root, observation.checkpoint.checkpoint_id)
    if metadata is None:
        return None, message
    return metadata, "Saved checkpoint metadata, patch files, and ordinary untracked files under .vibeagent/checkpoints."
