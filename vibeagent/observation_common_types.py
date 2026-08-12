from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .action_types import DeepReviewPerspective, PlanItem
from .peer_types import PeerSession
from .runtime_types import ApprovalPolicy


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
class PlanModeObservation:
    kind: Literal["enter_plan_mode", "exit_plan_mode", "plan_mode_feedback"]
    plan: list[PlanItem] = field(default_factory=list)
    message: str = ""
    next_policy: ApprovalPolicy | None = None


@dataclass(frozen=True)
class UserInputObservation:
    kind: Literal["ask_user"]
    question: str
    options: list[str]
    answer: str | None
    cancelled: bool
    message: str
    questions: list[dict[str, object]] = field(default_factory=list)
    answers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class UserMessageObservation:
    kind: Literal["send_user_message"]
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
    depth: int = 1
    parent_id: str | None = None
    teammate_name: str | None = None
    color: str | None = None


@dataclass(frozen=True)
class DeepReviewResult:
    perspective: DeepReviewPerspective
    ok: bool
    summary: str
    iterations: int
    tool_calls: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DeepReviewObservation:
    kind: Literal["deep_review"]
    ok: bool
    results: list[DeepReviewResult]
    verification_ok: bool
    summary: str
    base_ref: str | None
    target: str | None
    instructions_path: str | None
    message: str
    review_kind: Literal["defects", "cleanup", "security"] = "defects"


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
    depth: int = 1
    parent_id: str | None = None
    teammate_name: str | None = None
    color: str | None = None


@dataclass(frozen=True)
class ListAgentsObservation:
    kind: Literal["list_agents"]
    ok: bool
    agents: list[SubagentInstance]
    total: int
    truncated: bool
    invalid: int
    message: str
    peers: list[PeerSession] = field(default_factory=list)


@dataclass(frozen=True)
class PeerMessageObservation:
    kind: Literal["peer_message"]
    ok: bool
    to: str
    peer_id: str | None
    status: Literal["delivered", "held", "refused", "error"]
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
