from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class SessionSummaryAction:
    type: Literal["session_summary"]
    run_id: str | None = None
    recent_limit: int = 5


@dataclass(frozen=True)
class SessionPlanAction:
    type: Literal["session_plan"]
    run_id: str | None = None


@dataclass(frozen=True)
class SessionTranscriptAction:
    type: Literal["session_transcript"]
    run_id: str | None = None
    max_events: int = 80
    max_text: int = 500


@dataclass(frozen=True)
class SessionSearchAction:
    type: Literal["session_search"]
    query: str
    run_id: str | None = None
    max_matches: int = 20
    max_text: int = 500
    case_sensitive: bool = False


@dataclass(frozen=True)
class SessionCommandsAction:
    type: Literal["session_commands"]
    run_id: str | None = None
    max_commands: int = 20
    max_output_chars: int = 2_000


@dataclass(frozen=True)
class SessionOutputContextsAction:
    type: Literal["session_output_contexts"]
    run_id: str | None = None
    max_commands: int = 20
    max_output_chars: int = 20_000
    context_lines: int = 5
    max_contexts: int = 20
    max_bytes_per_context: int = 20_000


@dataclass(frozen=True)
class SessionOutputDiagnosticsAction:
    type: Literal["session_output_diagnostics"]
    run_id: str | None = None
    max_commands: int = 20
    max_output_chars: int = 20_000
    context_lines: int = 2
    max_diagnostics: int = 50
    max_contexts: int = 20
    max_bytes_per_context: int = 20_000


@dataclass(frozen=True)
class SessionFilesAction:
    type: Literal["session_files"]
    run_id: str | None = None
    max_files: int = 100


@dataclass(frozen=True)
class SessionFailuresAction:
    type: Literal["session_failures"]
    run_id: str | None = None
    max_failures: int = 50
    max_text: int = 500


@dataclass(frozen=True)
class SessionVerificationAction:
    type: Literal["session_verification"]
    run_id: str | None = None
    max_checks: int = 50


@dataclass(frozen=True)
class SessionAuditAction:
    type: Literal["session_audit"]
    run_id: str | None = None
    max_failures: int = 10
    max_files: int = 20
    max_commands: int = 10
    max_checks: int = 50
    max_text: int = 300


@dataclass(frozen=True)
class SessionHandoffAction:
    type: Literal["session_handoff"]
    run_id: str | None = None
    max_failures: int = 20
    max_files: int = 50
    max_commands: int = 10
    max_checks: int = 50
    max_output_chars: int = 1_000
    max_text: int = 500
