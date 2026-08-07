from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .observation_process_types import CommandCheckObservation, CommandResult


@dataclass(frozen=True)
class SuggestedCheck:
    command: str
    cwd: str
    source: str
    reason: str
    available: bool = True
    missing_tool: str | None = None


@dataclass(frozen=True)
class SuggestChecksObservation:
    kind: Literal["suggest_checks"]
    ok: bool
    checks: list[SuggestedCheck]
    total: int
    truncated: bool
    changed_files: list[str]
    message: str


@dataclass(frozen=True)
class CheckSuggestedChecksObservation:
    kind: Literal["check_suggested_checks"]
    ok: bool
    checks: list[CommandCheckObservation]
    suggested_checks: list[SuggestedCheck]
    total: int
    truncated: bool
    max_commands: int
    message: str


@dataclass(frozen=True)
class RunSuggestedChecksObservation:
    kind: Literal["run_suggested_checks"]
    ok: bool
    results: list[CommandResult]
    suggested_checks: list[SuggestedCheck]
    total: int
    truncated: bool
    max_commands: int
    stopped_early: bool
    skipped_unavailable: int
    message: str
