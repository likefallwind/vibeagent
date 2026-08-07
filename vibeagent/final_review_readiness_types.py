from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .types import FocusedTestCommand, SuggestedCheck


@dataclass
class FinalReviewReadinessInputs:
    review: Mapping[str, object]
    large_file_bytes: int
    secret_scan_bytes: int
    files_shown: int
    all_suggested_checks: list[SuggestedCheck]
    suggested_checks: list[SuggestedCheck]
    suggested_checks_total: int
    all_suggested_checks_truncated: bool
    suggested_checks_truncated: bool
    focused_test_commands: list[FocusedTestCommand]
    focused_test_commands_total: int
    focused_test_commands_truncated: bool
    focused_test_warning: str
    running_processes: list[object]
    conflict_scan: Mapping[str, object]
    large_files: list[dict[str, object]]
    large_files_total: int
    secret_findings: list[dict[str, object]]
    secret_findings_total: int
    secret_scan_truncated: bool
    secret_diff_findings: list[dict[str, object]]
    secret_diff_findings_total: int
    secret_diff_truncated: bool
    secret_diff_warnings: list[str]
    nested_git_repos: list[str]
    nested_git_repo_total: int
    changed_gitlinks: list[str]
    changed_gitlink_total: int
    changed_gitlink_warnings: list[str]
    hidden_git_changes: list[dict[str, str]]
    hidden_git_change_total: int
    hidden_git_change_warnings: list[str]
    unsafe_symlinks: list[dict[str, str]]
    unsafe_symlink_total: int
    unsafe_symlink_warnings: list[str]
    unsafe_symlink_reasons: set[str]
    git_operation: Mapping[str, object]
    git_info: Mapping[str, object]


@dataclass
class FinalReviewReadiness:
    blocking_issues: list[str]
    warnings: list[str]
