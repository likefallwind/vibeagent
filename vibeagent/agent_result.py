from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .types import ApprovalPolicy, ChatMessage, Observation, PlanItem, TaskStep


@dataclass(frozen=True)
class AgentResult:
    success: bool
    message: str
    run_dir: Path
    run_id: str
    iterations: int
    observations: list[Observation]
    steps: list[TaskStep]
    plan: list[PlanItem] = field(default_factory=list)
    status: str = ""
    completion_ready: bool = True
    completion_blockers: list[str] = field(default_factory=list)
    completion_warnings: list[str] = field(default_factory=list)
    verification_checks: list[str] = field(default_factory=list)
    pending_verification_checks: list[str] = field(default_factory=list)
    failed_verification_checks: list[str] = field(default_factory=list)
    completion_blocked_count: int = 0
    latest_completion_blockers: list[str] = field(default_factory=list)
    latest_completion_pending_verification_checks: list[str] = field(default_factory=list)
    latest_completion_failed_verification_checks: list[str] = field(default_factory=list)
    latest_completion_final_review_issues: list[str] = field(default_factory=list)
    latest_completion_final_review_changed_files: list[str] = field(default_factory=list)
    latest_completion_tool_errors: list[str] = field(default_factory=list)
    latest_completion_checkpoint_failures: list[str] = field(default_factory=list)
    latest_completion_active_background_processes: list[str] = field(default_factory=list)
    latest_completion_denied_approvals: list[str] = field(default_factory=list)
    latest_completion_next_actions: list[str] = field(default_factory=list)
    final_review_changed_files: list[str] = field(default_factory=list)
    approval_policy: ApprovalPolicy | None = None
    stop_reason: str | None = None
    deferred_tool_use: dict[str, object] | None = None
    is_error: bool = False
    hook_system_messages: list[str] = field(default_factory=list)
    conversation: list[ChatMessage] = field(default_factory=list, repr=False)
    display_message: str | None = None

    def __post_init__(self) -> None:
        if self.status:
            return
        status = "failed"
        if self.success:
            status = "completed" if self.completion_ready else "blocked"
        object.__setattr__(self, "status", status)

    @property
    def displayed_message(self) -> str:
        return self.message if self.display_message is None else self.display_message
