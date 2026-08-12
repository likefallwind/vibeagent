from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal
from uuid import uuid4

from .background_delegate_runtime import (
    execute_background_task_action,
    start_background_delegate_task,
)
from .agent_delegate_profile import resolve_profile_action
from .agent_team_runtime import TEAM_COORDINATION_TOOL_NAMES, execute_teammate_coordination_action
from .subagent_listing import execute_list_agents_action
from .types import (
    DelegateTaskAction,
    Observation,
    ToolErrorObservation,
)
from .workspace_core import RunWorkspace


MAX_SUBAGENT_DEPTH = 3

NestedDelegateExecutor = Callable[
    [
        DelegateTaskAction,
        str,
        int,
        str,
        int,
        str | None,
        Callable[[], bool] | None,
        Callable[[bool], list[str]] | None,
    ],
    Observation,
]


@dataclass(frozen=True)
class NestedDelegateRuntime:
    workspace: RunWorkspace
    subagent_id: str
    depth: int
    mode: Literal["explore", "code", "plan"]
    cancel_requested: Callable[[], bool] | None
    execute_child: NestedDelegateExecutor
    team_member_name: str | None = None

    @property
    def can_delegate(self) -> bool:
        return self.depth < MAX_SUBAGENT_DEPTH

    @property
    def coordination_tool_names(self) -> frozenset[str]:
        return TEAM_COORDINATION_TOOL_NAMES if self.team_member_name is not None else frozenset()

    def execute(
        self,
        action: object,
        child_iteration: int,
        parent_tool_use_id: str | None = None,
    ) -> Observation | None:
        if self.team_member_name is not None:
            coordinated = execute_teammate_coordination_action(
                self.workspace,
                action,
                self.team_member_name,
            )
            if coordinated is not None:
                return coordinated
        listed = execute_list_agents_action(self.workspace, action)
        if listed is not None:
            return listed
        background = execute_background_task_action(self.workspace, action)
        if background is not None:
            return background
        if not isinstance(action, DelegateTaskAction):
            return None
        action = resolve_profile_action(self.workspace, action)
        if action.teammate_name is not None:
            return ToolErrorObservation(
                kind="tool_error",
                tool="Agent",
                message="Only the lead agent can spawn teammates.",
            )
        if self.team_member_name is not None and action.run_in_background:
            return ToolErrorObservation(
                kind="tool_error",
                tool="Agent",
                message="Teammates may only run their own subagents in the foreground.",
            )
        if self.mode in {"explore", "plan"} and action.mode == "code":
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
                    parent_tool_use_id,
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
            parent_tool_use_id,
            self.cancel_requested,
            None,
        )


def _combined_cancel(
    parent: Callable[[], bool] | None,
    child: Callable[[], bool],
) -> Callable[[], bool]:
    return lambda: child() or (parent is not None and parent())


__all__ = ["MAX_SUBAGENT_DEPTH", "NestedDelegateRuntime"]
