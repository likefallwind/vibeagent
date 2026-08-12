from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, TypeAlias


PlanItemStatus: TypeAlias = Literal["pending", "in_progress", "completed"]
DeepReviewKind: TypeAlias = Literal["defects", "cleanup", "security"]
DeepReviewPerspective: TypeAlias = Literal[
    "correctness",
    "security",
    "tests",
    "reuse",
    "simplicity",
    "efficiency",
    "abstraction",
    "access_control",
    "injection",
    "data_exposure",
    "supply_chain",
]


@dataclass(frozen=True)
class PlanItem:
    step: str
    status: PlanItemStatus
    active_form: str | None = None


@dataclass(frozen=True)
class UpdatePlanAction:
    type: Literal["update_plan"]
    plan: list[PlanItem]
    explanation: str | None = None


@dataclass(frozen=True)
class EnterPlanModeAction:
    type: Literal["enter_plan_mode"]


@dataclass(frozen=True)
class ExitPlanModeAction:
    type: Literal["exit_plan_mode"]
    plan: list[PlanItem]
    allowed_prompts: list[dict[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class AskUserOption:
    label: str
    description: str


@dataclass(frozen=True)
class AskUserQuestion:
    question: str
    header: str
    options: list[AskUserOption]
    multi_select: bool = False


@dataclass(frozen=True)
class AskUserAction:
    type: Literal["ask_user"]
    question: str = ""
    options: list[str] = field(default_factory=list)
    allow_free_text: bool = True
    questions: list[AskUserQuestion] = field(default_factory=list)
    answers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class SendUserMessageAction:
    type: Literal["send_user_message"]
    message: str


@dataclass(frozen=True)
class DelegateTaskAction:
    type: Literal["delegate_task"]
    task: str
    context: str | None = None
    max_iterations: int = 4
    mode: Literal["explore", "code", "plan"] = "explore"
    agent: str | None = None
    run_in_background: bool = False
    isolation: Literal["worktree"] | None = None
    teammate_name: str | None = None
    color: str | None = None


@dataclass(frozen=True)
class DeepReviewAction:
    type: Literal["deep_review"]
    review_kind: DeepReviewKind = "defects"
    perspectives: list[DeepReviewPerspective] = field(
        default_factory=lambda: ["correctness", "security", "tests"]
    )
    max_iterations: int = 4
    base_ref: str | None = None
    target: str | None = None


@dataclass(frozen=True)
class SendMessageAction:
    type: Literal["send_message"]
    to: str
    message: str
    approve_plan: bool = False


@dataclass(frozen=True)
class ListAgentsAction:
    type: Literal["list_agents"]
    max_agents: int = 100


@dataclass(frozen=True)
class TaskOutputAction:
    type: Literal["task_output"]
    task_id: str
    block: bool = True
    timeout_ms: int = 30_000


@dataclass(frozen=True)
class TaskStopAction:
    type: Literal["task_stop"]
    task_id: str


@dataclass(frozen=True)
class FinishAction:
    type: Literal["finish"]
    message: str
