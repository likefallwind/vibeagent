from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal
from uuid import uuid4

from .background_delegate_runtime import (
    execute_background_task_action,
    start_background_delegate_task,
)
from .subagent_listing import execute_list_agents_action
from .types import (
    DelegateTaskAction,
    Observation,
    ToolErrorObservation,
)
from .workspace_core import RunWorkspace


MAX_SUBAGENT_DEPTH = 3

NestedDelegateExecutor = Callable[
    [DelegateTaskAction, str, int, str, int, Callable[[], bool] | None, Callable[[bool], list[str]] | None],
    Observation,
]


@dataclass(frozen=True)
class NestedDelegateRuntime:
    workspace: RunWorkspace
    subagent_id: str
    depth: int
    mode: Literal["explore", "code"]
    cancel_requested: Callable[[], bool] | None
    execute_child: NestedDelegateExecutor

    @property
    def can_delegate(self) -> bool:
        return self.depth < MAX_SUBAGENT_DEPTH

    def execute(self, action: object, child_iteration: int) -> Observation | None:
        listed = execute_list_agents_action(self.workspace, action)
        if listed is not None:
            return listed
        background = execute_background_task_action(self.workspace, action)
        if background is not None:
            return background
        if not isinstance(action, DelegateTaskAction):
            return None
        if self.mode == "explore" and action.mode == "code":
            return ToolErrorObservation(
                kind="tool_error",
                tool="delegate_task",
                message="Read-only subagents may only delegate explore-mode tasks.",
            )
        if not self.can_delegate:
            return ToolErrorObservation(
                kind="tool_error",
                tool="delegate_task",
                message=f"Subagent nesting limit reached at depth {MAX_SUBAGENT_DEPTH}.",
            )

        child_depth = self.depth + 1
        if action.run_in_background:
            return start_background_delegate_task(
                self.workspace,
                action,
                lambda task_id, child_cancelled, inbound: self.execute_child(
                    action,
                    task_id,
                    child_depth,
                    self.subagent_id,
                    child_iteration,
                    _combined_cancel(self.cancel_requested, child_cancelled),
                    inbound,
                ),
                depth=child_depth,
                parent_id=self.subagent_id,
            )
        child_id = f"agent-{uuid4().hex[:12]}"
        return self.execute_child(
            action,
            child_id,
            child_depth,
            self.subagent_id,
            child_iteration,
            self.cancel_requested,
            None,
        )


def _combined_cancel(
    parent: Callable[[], bool] | None,
    child: Callable[[], bool],
) -> Callable[[], bool]:
    return lambda: child() or (parent is not None and parent())


__all__ = ["MAX_SUBAGENT_DEPTH", "NestedDelegateRuntime"]
