from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal, TypeAlias


WorkflowStatus: TypeAlias = Literal[
    "running",
    "completed",
    "failed",
    "stopped",
    "interrupted",
]


@dataclass(frozen=True)
class WorkflowAgentRequest:
    call_id: str
    task: str
    workflow_id: str | None = None
    context: str | None = None
    mode: Literal["explore", "code"] = "explore"
    agent: str | None = None
    max_iterations: int = 4
    isolation: Literal["worktree"] | None = None


@dataclass(frozen=True)
class WorkflowRunSummary:
    id: str
    script: str
    session_id: str
    status: WorkflowStatus
    total_calls: int
    cached_calls: int
    started_at: str
    updated_at: str
    error: str | None = None
    result: object = None


WorkflowAgentExecutor: TypeAlias = Callable[[WorkflowAgentRequest, Callable[[], bool]], dict[str, object]]


__all__ = [
    "WorkflowAgentExecutor",
    "WorkflowAgentRequest",
    "WorkflowRunSummary",
    "WorkflowStatus",
]
