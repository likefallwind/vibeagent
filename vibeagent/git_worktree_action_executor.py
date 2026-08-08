from __future__ import annotations

from .types import (
    EnterWorktreeAction,
    EnterWorktreeObservation,
    ExitWorktreeAction,
    ExitWorktreeObservation,
    Observation,
)
from .workspace_core import RunWorkspace
from .workspace_git_worktree_ops import enter_git_worktree, exit_git_worktree


def execute_git_worktree_action(workspace: RunWorkspace, action: object) -> Observation | None:
    if isinstance(action, EnterWorktreeAction):
        return EnterWorktreeObservation(
            kind="enter_worktree",
            **enter_git_worktree(workspace, name=action.name, path=action.path),
        )
    if isinstance(action, ExitWorktreeAction):
        return ExitWorktreeObservation(kind="exit_worktree", **exit_git_worktree(workspace))
    return None
