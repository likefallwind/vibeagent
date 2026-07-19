from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class SessionPlanItem:
    step: str
    status: str


@dataclass(frozen=True)
class SessionProcessInfo:
    process_id: str
    pid: int | None
    command: str
    cwd: str
    line_number: int


@dataclass(frozen=True)
class SessionEvent:
    type: str
    payload: dict[str, Any]
    line_number: int
    raw: dict[str, Any] | None = None
    malformed: bool = False
    error: str | None = None


@dataclass(frozen=True)
class SessionInfo:
    run_id: str
    event_count: int
    malformed_count: int
    last_event_time: datetime | None


@dataclass(frozen=True)
class SessionSummary:
    run_id: str
    exists: bool
    event_count: int
    malformed_count: int
    iterations: int
    task: str | None
    tool_calls: list[str]
    approvals_requested: int
    approvals_approved: int
    approvals_denied: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    final_message: str | None
    latest_plan: list[SessionPlanItem]
    completed: bool
    failed: bool
    blocked: bool = False
    final_review_seen: bool = False
    final_review_ready: bool | None = None
    final_review_blocking_issues: int = 0
    final_review_warnings: int = 0
    final_review_files: int = 0
    final_review_changed_files: list[str] = field(default_factory=list)
    final_review_suggested_checks: int = 0
    final_review_message: str | None = None
    final_review_python_failures: list[str] = field(default_factory=list)
    final_review_config_failures: list[str] = field(default_factory=list)
    completion_ready: bool | None = None
    completion_blockers: list[str] = field(default_factory=list)
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
    completion_warnings: list[str] = field(default_factory=list)
    verification_checks: list[str] = field(default_factory=list)
    pending_verification_checks: list[str] = field(default_factory=list)
    failed_verification_checks: list[str] = field(default_factory=list)
    checkpoints_created: int = 0
    auto_checkpoints_created: int = 0
    latest_checkpoint_id: str | None = None
    latest_checkpoint_message: str | None = None
    model_errors: int = 0
    latest_model_error: str | None = None
    background_processes_started: int = 0
    active_background_processes: list[SessionProcessInfo] = field(default_factory=list)
    subagents_started: int = 0
    subagents_completed: int = 0
    subagents_failed: int = 0
    subagent_tool_calls: list[str] = field(default_factory=list)
    subagent_context_compacted_count: int = 0
