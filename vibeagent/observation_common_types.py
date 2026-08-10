from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .action_types import PlanItem


@dataclass(frozen=True)
class FinishObservation:
    kind: Literal["finish"]
    message: str


@dataclass(frozen=True)
class UpdatePlanObservation:
    kind: Literal["update_plan"]
    plan: list[PlanItem] = field(default_factory=list)
    message: str = "Plan updated."


@dataclass(frozen=True)
class UserInputObservation:
    kind: Literal["ask_user"]
    question: str
    options: list[str]
    answer: str | None
    cancelled: bool
    message: str


@dataclass(frozen=True)
class DelegateTaskObservation:
    kind: Literal["delegate_task"]
    ok: bool
    task: str
    summary: str
    iterations: int
    tool_calls: list[str]
    message: str
    mode: Literal["explore", "code"] = "explore"
    agent: str | None = None
    task_id: str | None = None
    background: bool = False
    running: bool = False
    cancelled: bool = False
    isolation: Literal["worktree"] | None = None
    worktree_path: str | None = None
    worktree_branch: str | None = None
    worktree_preserved: bool = False


@dataclass(frozen=True)
class SubagentInstance:
    id: str
    task: str
    status: Literal["running", "completed", "failed", "cancelled"]
    mode: Literal["explore", "code"]
    agent: str | None
    background: bool
    runs: int
    resumable: bool
    isolation: Literal["worktree"] | None = None
    worktree_path: str | None = None
    worktree_branch: str | None = None
    worktree_preserved: bool = False


@dataclass(frozen=True)
class ListAgentsObservation:
    kind: Literal["list_agents"]
    ok: bool
    agents: list[SubagentInstance]
    total: int
    truncated: bool
    invalid: int
    message: str


@dataclass(frozen=True)
class TaskOutputObservation:
    kind: Literal["task_output"]
    ok: bool
    task_id: str
    running: bool
    completed: bool
    result: DelegateTaskObservation | None
    message: str


@dataclass(frozen=True)
class TaskStopObservation:
    kind: Literal["task_stop"]
    ok: bool
    task_id: str
    running: bool
    stopped: bool
    message: str


@dataclass(frozen=True)
class ToolErrorObservation:
    kind: Literal["tool_error"]
    tool: str
    message: str


@dataclass(frozen=True)
class ApprovalDeniedObservation:
    kind: Literal["approval_denied"]
    action_type: str
    target: str
    message: str
