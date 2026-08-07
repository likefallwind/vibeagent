from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .observation_process_types import CommandCheckObservation, CommandResult


@dataclass(frozen=True)
class RelatedTestCandidate:
    source_path: str
    test_path: str
    score: int
    reason: str


@dataclass(frozen=True)
class RelatedTestsObservation:
    kind: Literal["related_tests"]
    ok: bool
    target_paths: list[str]
    candidates: list[RelatedTestCandidate]
    total: int
    truncated: bool
    test_files_total: int
    message: str


@dataclass(frozen=True)
class FocusedTestCommand:
    command: str
    cwd: str
    test_path: str
    source: str
    reason: str
    available: bool = True
    missing_tool: str | None = None


@dataclass(frozen=True)
class FocusedTestCommandsObservation:
    kind: Literal["focused_test_commands"]
    ok: bool
    target_paths: list[str]
    commands: list[FocusedTestCommand]
    total: int
    truncated: bool
    related_tests_total: int
    message: str


@dataclass(frozen=True)
class CheckFocusedTestCommandsObservation:
    kind: Literal["check_focused_test_commands"]
    ok: bool
    checks: list[CommandCheckObservation]
    focused_commands: list[FocusedTestCommand]
    target_paths: list[str]
    total: int
    truncated: bool
    max_commands: int
    related_tests_total: int
    message: str
    max_paths: int = 100
    max_candidates: int = 200
    requested_paths: list[str] | None = None


@dataclass(frozen=True)
class RunFocusedTestCommandsObservation:
    kind: Literal["run_focused_test_commands"]
    ok: bool
    results: list[CommandResult]
    focused_commands: list[FocusedTestCommand]
    target_paths: list[str]
    total: int
    truncated: bool
    max_commands: int
    related_tests_total: int
    stopped_early: bool
    skipped_unavailable: int
    message: str
    max_paths: int = 100
    max_candidates: int = 200
    requested_paths: list[str] | None = None
