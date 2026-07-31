from __future__ import annotations

from pathlib import Path

from .actions import execute_action
from .local_command_workspace import local_command_workspace
from .types import (
    CheckCheckpointPruneAction,
    CheckpointPruneAction,
)
from .workflow_checkpoint_create_commands import (
    build_checkpoint_create_report,
    create_local_checkpoint_metadata,
    get_checkpoint_report,
    get_checkpoint_text,
)
from .workflow_checkpoint_delete_commands import (
    CHECK_CHECKPOINT_DELETE_USAGE,
    CHECKPOINT_DELETE_USAGE,
    get_check_checkpoint_delete_report,
    get_checkpoint_delete_report,
    get_checkpoint_delete_text,
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
from .workflow_checkpoint_restore_commands import (
    CHECKPOINT_RESTORE_USAGE,
    get_check_checkpoint_restore_report,
    get_checkpoint_restore_report,
)
from .workflow_checkpoint_utils import (
    parse_checkpoint_keep_last,
)


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
