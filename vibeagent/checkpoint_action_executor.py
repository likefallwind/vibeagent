from __future__ import annotations

from .checkpoint_actions import (
    check_checkpoint_restore_observation,
    checkpoint_restore_observation,
    create_checkpoint_observation,
)
from .checkpoint_cleanup_actions import (
    check_checkpoint_delete_observation,
    check_checkpoint_prune_observation,
    checkpoint_delete_observation,
    checkpoint_prune_observation,
)
from .checkpoint_query_actions import (
    checkpoint_diff_observation,
    checkpoint_show_observation,
    checkpoint_status_observation,
    list_checkpoints_observation,
)
from .types import (
    CheckCheckpointDeleteAction,
    CheckCheckpointPruneAction,
    CheckCheckpointRestoreAction,
    CheckpointCreateAction,
    CheckpointDeleteAction,
    CheckpointDiffAction,
    CheckpointListAction,
    CheckpointPruneAction,
    CheckpointRestoreAction,
    CheckpointShowAction,
    CheckpointStatusAction,
    Observation,
)
from .workspace import RunWorkspace


def execute_checkpoint_action(workspace: RunWorkspace, action: object) -> Observation | None:
    if isinstance(action, CheckpointCreateAction):
        return create_checkpoint_observation(workspace, action.label)
    if isinstance(action, CheckpointListAction):
        return list_checkpoints_observation(workspace.root, action.max_entries)
    if isinstance(action, CheckpointShowAction):
        return checkpoint_show_observation(workspace.root, action.checkpoint_id)
    if isinstance(action, CheckpointDiffAction):
        return checkpoint_diff_observation(workspace.root, action.checkpoint_id, action.max_chars)
    if isinstance(action, CheckpointStatusAction):
        return checkpoint_status_observation(workspace, action.checkpoint_id)
    if isinstance(action, CheckCheckpointRestoreAction):
        return check_checkpoint_restore_observation(workspace, action.checkpoint_id)
    if isinstance(action, CheckpointRestoreAction):
        return checkpoint_restore_observation(workspace, action.checkpoint_id)
    if isinstance(action, CheckCheckpointDeleteAction):
        return check_checkpoint_delete_observation(workspace.root, action.checkpoint_id)
    if isinstance(action, CheckpointDeleteAction):
        return checkpoint_delete_observation(workspace.root, action.checkpoint_id)
    if isinstance(action, CheckCheckpointPruneAction):
        return check_checkpoint_prune_observation(workspace.root, action.keep_last)
    if isinstance(action, CheckpointPruneAction):
        return checkpoint_prune_observation(workspace.root, action.keep_last)
    return None
