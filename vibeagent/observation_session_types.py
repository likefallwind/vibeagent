from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from .observation_process_types import CommandResult
from .observation_read_types import OutputContextResult, OutputDiagnostic


@dataclass(frozen=True)
class SessionSummaryObservation:
    kind: Literal["session_summary"]
    run_id: str
    ok: bool
    summary: str
    recent_sessions: list[str]
    message: str


@dataclass(frozen=True)
class SessionPlanObservation:
    kind: Literal["session_plan"]
    run_id: str
    ok: bool
    plan: str
    message: str


@dataclass(frozen=True)
class SessionTranscriptObservation:
    kind: Literal["session_transcript"]
    run_id: str
    ok: bool
    transcript: str
    message: str


@dataclass(frozen=True)
class SessionSearchObservation:
    kind: Literal["session_search"]
    run_id: str
    ok: bool
    query: str
    matches: str
    total_matches: int
    shown_matches: int
    message: str


@dataclass(frozen=True)
class SessionCommandsObservation:
    kind: Literal["session_commands"]
    run_id: str
    ok: bool
    commands: str
    command_count: int
    shown_commands: int
    message: str


@dataclass(frozen=True)
class SessionOutputContextsObservation:
    kind: Literal["session_output_contexts"]
    run_id: str
    ok: bool
    contexts: list[OutputContextResult]
    command_count: int
    shown_commands: int
    total_refs: int
    truncated: bool
    message: str


@dataclass(frozen=True)
class SessionOutputDiagnosticsObservation:
    kind: Literal["session_output_diagnostics"]
    run_id: str
    ok: bool
    diagnostics: list[OutputDiagnostic]
    contexts: list[OutputContextResult]
    command_count: int
    shown_commands: int
    total_diagnostics: int
    total_refs: int
    diagnostics_truncated: bool
    contexts_truncated: bool
    message: str


@dataclass(frozen=True)
class SessionFilesObservation:
    kind: Literal["session_files"]
    run_id: str
    ok: bool
    files: str
    file_count: int
    shown_files: int
    message: str
    file_references: list[dict[str, Any]] = field(default_factory=list)
    files_truncated: bool = False


@dataclass(frozen=True)
class SessionFailuresObservation:
    kind: Literal["session_failures"]
    run_id: str
    ok: bool
    failures: str
    failure_count: int
    shown_failures: int
    message: str


@dataclass(frozen=True)
class SessionVerificationObservation:
    kind: Literal["session_verification"]
    run_id: str
    ok: bool
    verification: str
    verified_commands: list[dict[str, Any]]
    pending_commands: list[dict[str, Any]]
    failed_commands: list[dict[str, Any]]
    verified_count: int
    pending_count: int
    failed_count: int
    verification_truncated: bool
    message: str


@dataclass(frozen=True)
class RunSessionVerificationObservation:
    kind: Literal["run_session_verification"]
    run_id: str
    ok: bool
    selected_commands: list[dict[str, Any]]
    selected_count: int
    pending_count: int
    failed_count: int
    results: list[CommandResult]
    stopped_early: bool
    message: str


@dataclass(frozen=True)
class SessionAuditProcess:
    process_id: str
    pid: int | None
    command: str
    cwd: str
    line_number: int


@dataclass(frozen=True)
class SessionAuditObservation:
    kind: Literal["session_audit"]
    run_id: str
    ok: bool
    audit: str
    ready: bool
    blockers: list[str]
    background_processes_started: int
    active_background_processes: list[SessionAuditProcess]
    message: str
    file_references: list[dict[str, Any]] = field(default_factory=list)
    file_count: int = 0
    shown_file_count: int = 0
    files_truncated: bool = False
    completion_ready: bool | None = None
    completion_blockers: list[str] = field(default_factory=list)
    latest_completion_blockers: list[str] = field(default_factory=list)
    latest_completion_pending_verification_checks: list[str] = field(default_factory=list)
    latest_completion_failed_verification_checks: list[str] = field(default_factory=list)
    latest_completion_final_review_issues: list[str] = field(default_factory=list)
    latest_completion_final_review_changed_files: list[str] = field(default_factory=list)
    latest_completion_tool_errors: list[str] = field(default_factory=list)
    latest_completion_checkpoint_failures: list[str] = field(default_factory=list)
    latest_completion_active_background_processes: list[str] = field(default_factory=list)
    latest_completion_denied_approvals: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SessionHandoffObservation:
    kind: Literal["session_handoff"]
    run_id: str
    ok: bool
    handoff: str
    message: str
    ready: bool | None = None
    status: str = ""
    blockers: list[str] = field(default_factory=list)
    background_processes_started: int = 0
    active_background_processes: list[SessionAuditProcess] = field(default_factory=list)
    verified_commands: list[dict[str, Any]] = field(default_factory=list)
    pending_commands: list[dict[str, Any]] = field(default_factory=list)
    failed_commands: list[dict[str, Any]] = field(default_factory=list)
    verified_count: int = 0
    pending_count: int = 0
    failed_count: int = 0
    pending_plan_items: list[dict[str, str]] = field(default_factory=list)
    pending_plan_count: int = 0
    plan_items_count: int = 0
    plan_in_progress: bool = False
    file_references: list[dict[str, Any]] = field(default_factory=list)
    file_count: int = 0
    shown_file_count: int = 0
    files_truncated: bool = False
    completion_ready: bool | None = None
    completion_blockers: list[str] = field(default_factory=list)
    latest_completion_blockers: list[str] = field(default_factory=list)
    latest_completion_pending_verification_checks: list[str] = field(default_factory=list)
    latest_completion_failed_verification_checks: list[str] = field(default_factory=list)
    latest_completion_final_review_issues: list[str] = field(default_factory=list)
    latest_completion_final_review_changed_files: list[str] = field(default_factory=list)
    latest_completion_tool_errors: list[str] = field(default_factory=list)
    latest_completion_checkpoint_failures: list[str] = field(default_factory=list)
    latest_completion_active_background_processes: list[str] = field(default_factory=list)
    latest_completion_denied_approvals: list[str] = field(default_factory=list)
