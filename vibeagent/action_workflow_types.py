from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias


PlanItemStatus: TypeAlias = Literal["pending", "in_progress", "completed"]


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
class AskUserAction:
    type: Literal["ask_user"]
    question: str
    options: list[str]
    allow_free_text: bool = True


@dataclass(frozen=True)
class DelegateTaskAction:
    type: Literal["delegate_task"]
    task: str
    context: str | None = None
    max_iterations: int = 4
    mode: Literal["explore", "code"] = "explore"
    agent: str | None = None
    run_in_background: bool = False


@dataclass(frozen=True)
class SendMessageAction:
    type: Literal["send_message"]
    to: str
    message: str


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
