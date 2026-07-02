from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .observation_git_types import GitChangeFile, GitDiffHunk, UntrackedFilePreview
from .observation_process_types import ProcessInfo
from .observation_project_types import SuggestedCheck
from .observation_read_types import ConfigCheckResult, PythonCheckResult


@dataclass(frozen=True)
class ReviewChangesObservation:
    kind: Literal["review_changes"]
    ok: bool
    changes_ok: bool
    diff_check_ok: bool
    staged_diff_check_ok: bool
    python_ok: bool
    config_ok: bool
    files: list[GitChangeFile]
    total_files: int
    python: list[PythonCheckResult]
    python_total: int
    python_truncated: bool
    config: list[ConfigCheckResult]
    config_total: int
    config_truncated: bool
    suggested_checks: list[SuggestedCheck]
    suggested_checks_total: int
    suggested_checks_truncated: bool
    diff_hunks: list[GitDiffHunk]
    diff_hunks_total: int
    diff_hunks_truncated: bool
    staged_diff_hunks: list[GitDiffHunk]
    staged_diff_hunks_total: int
    staged_diff_hunks_truncated: bool
    untracked_previews: list[UntrackedFilePreview]
    untracked_previews_total: int
    untracked_previews_truncated: bool
    diff_check: str
    staged_diff_check: str
    status: str
    message: str


@dataclass(frozen=True)
class FinalReviewObservation:
    kind: Literal["final_review"]
    ok: bool
    ready: bool
    blocking_issues: list[str]
    warnings: list[str]
    running_processes: list[ProcessInfo]
    files: list[GitChangeFile]
    total_files: int
    suggested_checks: list[SuggestedCheck]
    suggested_checks_total: int
    suggested_checks_truncated: bool
    diff_check: str
    staged_diff_check: str
    status: str
    message: str
    python: list[PythonCheckResult] = field(default_factory=list)
    python_total: int = 0
    python_truncated: bool = False
    config: list[ConfigCheckResult] = field(default_factory=list)
    config_total: int = 0
    config_truncated: bool = False
