from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias


PlanItemStatus: TypeAlias = Literal["pending", "in_progress", "completed"]


@dataclass(frozen=True)
class PlanItem:
    step: str
    status: PlanItemStatus


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
class FinishAction:
    type: Literal["finish"]
    message: str
