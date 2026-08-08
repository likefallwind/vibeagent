from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from .agent_runtime_utils import append_session_event
from .types import EnterWorktreeObservation, ExitWorktreeObservation, Observation
from .workspace_core import RunWorkspace


def apply_workspace_transition(
    workspace: RunWorkspace,
    observation: Observation,
    *,
    iteration: int,
) -> RunWorkspace:
    if not isinstance(observation, (EnterWorktreeObservation, ExitWorktreeObservation)) or not observation.ok:
        return workspace
    new_root = Path(observation.path).resolve()
    if not new_root.is_dir():
        return workspace
    history = (
        (*workspace.root_history, workspace.root)
        if isinstance(observation, EnterWorktreeObservation)
        else workspace.root_history[:-1]
    )
    transitioned = replace(workspace, root=new_root, root_history=history)
    append_session_event(
        workspace.session_dir,
        "workspace_changed",
        {
            "iteration": iteration,
            "kind": observation.kind,
            "previousRoot": str(workspace.root),
            "root": str(new_root),
        },
    )
    return transitioned
