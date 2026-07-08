from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .final_review_actions import (
    FINAL_REVIEW_LARGE_FILE_BYTES,
    FINAL_REVIEW_SECRET_SCAN_BYTES,
    final_review_scan_file_items,
    find_large_changed_files,
)
from .final_review_git_safety import (
    find_changed_gitlinks,
    find_hidden_tracked_git_changes,
    find_nested_git_repositories,
    find_unsafe_changed_symlinks,
    read_git_operation_state,
)
from .final_review_secret_scan import find_secret_like_changed_files, find_secret_like_git_diff_additions
from .workspace import read_git_conflicts, read_git_info
from .workspace_core import RunWorkspace


@dataclass(frozen=True)
class FinalReviewSafetyScan:
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


def collect_final_review_safety_scan(
    workspace: RunWorkspace,
    review_files: list[dict[str, object]],
    *,
    large_file_bytes: int = FINAL_REVIEW_LARGE_FILE_BYTES,
    secret_scan_bytes: int = FINAL_REVIEW_SECRET_SCAN_BYTES,
) -> FinalReviewSafetyScan:
    conflict_scan = read_git_conflicts(workspace, max_markers=20, max_files=5000)
    review_scan_files = final_review_scan_file_items(workspace, review_files)
    large_files, large_files_total = find_large_changed_files(
        workspace,
        review_scan_files,
        max_bytes=large_file_bytes,
    )
    secret_findings, secret_findings_total, secret_scan_truncated = find_secret_like_changed_files(
        workspace,
        review_scan_files,
        max_bytes=secret_scan_bytes,
    )
    (
        secret_diff_findings,
        secret_diff_findings_total,
        secret_diff_truncated,
        secret_diff_warnings,
    ) = find_secret_like_git_diff_additions(
        workspace,
        max_bytes=secret_scan_bytes,
    )
    nested_git_repos, nested_git_repo_total = find_nested_git_repositories(workspace)
    changed_gitlinks, changed_gitlink_total, changed_gitlink_warnings = find_changed_gitlinks(workspace)
    hidden_git_changes, hidden_git_change_total, hidden_git_change_warnings = find_hidden_tracked_git_changes(workspace)
    unsafe_symlinks, unsafe_symlink_total, unsafe_symlink_warnings, unsafe_symlink_reasons = find_unsafe_changed_symlinks(
        workspace,
        review_files,
    )
    git_operation = read_git_operation_state(workspace)
    git_info = read_git_info(workspace)
    return FinalReviewSafetyScan(
        conflict_scan=conflict_scan,
        large_files=large_files,
        large_files_total=large_files_total,
        secret_findings=secret_findings,
        secret_findings_total=secret_findings_total,
        secret_scan_truncated=secret_scan_truncated,
        secret_diff_findings=secret_diff_findings,
        secret_diff_findings_total=secret_diff_findings_total,
        secret_diff_truncated=secret_diff_truncated,
        secret_diff_warnings=secret_diff_warnings,
        nested_git_repos=nested_git_repos,
        nested_git_repo_total=nested_git_repo_total,
        changed_gitlinks=changed_gitlinks,
        changed_gitlink_total=changed_gitlink_total,
        changed_gitlink_warnings=changed_gitlink_warnings,
        hidden_git_changes=hidden_git_changes,
        hidden_git_change_total=hidden_git_change_total,
        hidden_git_change_warnings=hidden_git_change_warnings,
        unsafe_symlinks=unsafe_symlinks,
        unsafe_symlink_total=unsafe_symlink_total,
        unsafe_symlink_warnings=unsafe_symlink_warnings,
        unsafe_symlink_reasons=unsafe_symlink_reasons,
        git_operation=git_operation,
        git_info=git_info,
    )


__all__ = ["FinalReviewSafetyScan", "collect_final_review_safety_scan"]
