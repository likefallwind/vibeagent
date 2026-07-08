from __future__ import annotations

from .final_review_actions import (
    FINAL_REVIEW_LARGE_FILE_BYTES,
    FINAL_REVIEW_SECRET_SCAN_BYTES,
    final_review_scan_file_items,
    find_large_changed_files,
    find_secret_like_changed_files,
    find_secret_like_git_diff_additions,
)
from .final_review_git_safety import (
    find_changed_gitlinks,
    find_hidden_tracked_git_changes,
    find_nested_git_repositories,
    find_unsafe_changed_symlinks,
    read_git_operation_state,
)
from .final_review_readiness import FinalReviewReadinessInputs, build_final_review_readiness
from .process_runtime import list_background_processes
from .types import (
    AgentAction,
    ConfigCheckResult,
    FinalReviewAction,
    FinalReviewObservation,
    FocusedTestCommand,
    GitChangeFile,
    GitDiffHunk,
    Observation,
    PythonCheckResult,
    ReviewChangesAction,
    ReviewChangesObservation,
    SuggestedCheck,
    UntrackedFilePreview,
)
from .workspace import RunWorkspace, read_git_conflicts, review_project_changes, suggest_focused_test_commands, suggest_project_checks


def execute_final_review_action(workspace: RunWorkspace, action: AgentAction) -> Observation | None:
    if isinstance(action, ReviewChangesAction):
        return review_changes_observation(workspace, action)
    if isinstance(action, FinalReviewAction):
        return final_review_observation(workspace, action)
    return None


def review_changes_observation(workspace: RunWorkspace, action: ReviewChangesAction) -> ReviewChangesObservation:
    try:
        review = review_project_changes(workspace, max_files=action.max_files)
    except ValueError as error:
        return ReviewChangesObservation(
            kind="review_changes",
            ok=False,
            changes_ok=False,
            diff_check_ok=False,
            staged_diff_check_ok=False,
            python_ok=False,
            config_ok=False,
            files=[],
            total_files=0,
            python=[],
            python_total=0,
            python_truncated=False,
            config=[],
            config_total=0,
            config_truncated=False,
            suggested_checks=[],
            suggested_checks_total=0,
            suggested_checks_truncated=False,
            diff_hunks=[],
            diff_hunks_total=0,
            diff_hunks_truncated=False,
            staged_diff_hunks=[],
            staged_diff_hunks_total=0,
            staged_diff_hunks_truncated=False,
            untracked_previews=[],
            untracked_previews_total=0,
            untracked_previews_truncated=False,
            diff_check="",
            staged_diff_check="",
            status="",
            message=str(error),
        )
    files = [GitChangeFile(**item) for item in review["files"]]
    python = [PythonCheckResult(**item) for item in review["python"]]
    config = [ConfigCheckResult(**item) for item in review["config"]]
    suggested_checks = [SuggestedCheck(**item) for item in review["suggested_checks"]]
    diff_hunks = [GitDiffHunk(**item) for item in review["diff_hunks"]]
    staged_diff_hunks = [GitDiffHunk(**item) for item in review["staged_diff_hunks"]]
    untracked_previews = [UntrackedFilePreview(**item) for item in review["untracked_previews"]]
    return ReviewChangesObservation(
        kind="review_changes",
        ok=bool(review["ok"]),
        changes_ok=bool(review["changes_ok"]),
        diff_check_ok=bool(review["diff_check_ok"]),
        staged_diff_check_ok=bool(review["staged_diff_check_ok"]),
        python_ok=bool(review["python_ok"]),
        config_ok=bool(review["config_ok"]),
        files=files,
        total_files=int(review["total_files"]),
        python=python,
        python_total=int(review["python_total"]),
        python_truncated=bool(review["python_truncated"]),
        config=config,
        config_total=int(review["config_total"]),
        config_truncated=bool(review["config_truncated"]),
        suggested_checks=suggested_checks,
        suggested_checks_total=int(review["suggested_checks_total"]),
        suggested_checks_truncated=bool(review["suggested_checks_truncated"]),
        diff_hunks=diff_hunks,
        diff_hunks_total=int(review["diff_hunks_total"]),
        diff_hunks_truncated=bool(review["diff_hunks_truncated"]),
        staged_diff_hunks=staged_diff_hunks,
        staged_diff_hunks_total=int(review["staged_diff_hunks_total"]),
        staged_diff_hunks_truncated=bool(review["staged_diff_hunks_truncated"]),
        untracked_previews=untracked_previews,
        untracked_previews_total=int(review["untracked_previews_total"]),
        untracked_previews_truncated=bool(review["untracked_previews_truncated"]),
        diff_check=str(review["diff_check"]),
        staged_diff_check=str(review["staged_diff_check"]),
        status=str(review["status"]),
        message=str(review["message"]),
    )


def final_review_observation(workspace: RunWorkspace, action: FinalReviewAction) -> FinalReviewObservation:
    try:
        if action.max_checks < 1:
            raise ValueError("max_checks must be at least 1.")
        if action.max_checks > 50:
            raise ValueError("max_checks must be at most 50.")
        review = review_project_changes(workspace, max_files=action.max_files)
    except ValueError as error:
        return FinalReviewObservation(
            kind="final_review",
            ok=False,
            ready=False,
            blocking_issues=[str(error)],
            warnings=[],
            running_processes=[],
            files=[],
            total_files=0,
            suggested_checks=[],
            suggested_checks_total=0,
            suggested_checks_truncated=False,
            diff_check="",
            staged_diff_check="",
            status="",
            message=str(error),
        )
    files = [GitChangeFile(**item) for item in review["files"]]
    python = [PythonCheckResult(**item) for item in review["python"]]
    config = [ConfigCheckResult(**item) for item in review["config"]]
    all_suggestions = suggest_project_checks(workspace, max_commands=100)
    all_suggested_checks = [SuggestedCheck(**item) for item in all_suggestions["checks"]]
    suggested_checks = all_suggested_checks[: action.max_checks]
    suggested_checks_total = int(all_suggestions["total"])
    all_suggested_checks_truncated = bool(all_suggestions["truncated"])
    suggested_checks_truncated = (
        all_suggested_checks_truncated
        or len(all_suggested_checks) > len(suggested_checks)
        or suggested_checks_total > len(suggested_checks)
    )
    focused_test_commands: list[FocusedTestCommand] = []
    focused_test_commands_total = 0
    focused_test_commands_truncated = False
    focused_test_related_tests_total = 0
    changed_paths = [item.path for item in files]
    if changed_paths:
        try:
            focused_metadata = suggest_focused_test_commands(
                workspace,
                paths=changed_paths,
                max_paths=action.max_files,
                max_candidates=200,
                max_commands=action.max_checks,
            )
            focused_test_commands = [FocusedTestCommand(**item) for item in focused_metadata["commands"]]
            focused_test_commands_total = int(focused_metadata["total"])
            focused_test_commands_truncated = bool(focused_metadata["truncated"])
            focused_test_related_tests_total = int(focused_metadata["related_tests_total"])
        except ValueError as error:
            focused_test_commands = []
            focused_test_commands_total = 0
            focused_test_commands_truncated = False
            focused_test_related_tests_total = 0
            focused_test_warning = f"Could not suggest focused tests: {error}."
        else:
            focused_test_warning = ""
    else:
        focused_test_warning = ""
    running_processes = [process for process in list_background_processes(workspace.root).processes if process.running]
    conflict_scan = read_git_conflicts(workspace, max_markers=20, max_files=5000)
    review_scan_files = final_review_scan_file_items(workspace, list(review["files"]))
    large_files, large_files_total = find_large_changed_files(
        workspace,
        review_scan_files,
        max_bytes=FINAL_REVIEW_LARGE_FILE_BYTES,
    )
    secret_findings, secret_findings_total, secret_scan_truncated = find_secret_like_changed_files(
        workspace,
        review_scan_files,
        max_bytes=FINAL_REVIEW_SECRET_SCAN_BYTES,
    )
    secret_diff_findings, secret_diff_findings_total, secret_diff_truncated, secret_diff_warnings = find_secret_like_git_diff_additions(
        workspace,
        max_bytes=FINAL_REVIEW_SECRET_SCAN_BYTES,
    )
    nested_git_repos, nested_git_repo_total = find_nested_git_repositories(workspace)
    changed_gitlinks, changed_gitlink_total, changed_gitlink_warnings = find_changed_gitlinks(workspace)
    hidden_git_changes, hidden_git_change_total, hidden_git_change_warnings = find_hidden_tracked_git_changes(workspace)
    unsafe_symlinks, unsafe_symlink_total, unsafe_symlink_warnings, unsafe_symlink_reasons = find_unsafe_changed_symlinks(
        workspace,
        list(review["files"]),
    )
    git_operation = read_git_operation_state(workspace)
    total_files = int(review["total_files"])
    readiness = build_final_review_readiness(
        workspace,
        FinalReviewReadinessInputs(
            review=review,
            large_file_bytes=FINAL_REVIEW_LARGE_FILE_BYTES,
            secret_scan_bytes=FINAL_REVIEW_SECRET_SCAN_BYTES,
            files_shown=len(files),
            all_suggested_checks=all_suggested_checks,
            suggested_checks=suggested_checks,
            suggested_checks_total=suggested_checks_total,
            all_suggested_checks_truncated=all_suggested_checks_truncated,
            suggested_checks_truncated=suggested_checks_truncated,
            focused_test_commands=focused_test_commands,
            focused_test_commands_total=focused_test_commands_total,
            focused_test_commands_truncated=focused_test_commands_truncated,
            focused_test_warning=focused_test_warning,
            running_processes=running_processes,
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
        ),
    )
    blocking_issues = readiness.blocking_issues
    warnings = readiness.warnings

    ready = bool(review["ok"]) and not blocking_issues
    if ready:
        message = f"Final review ready: {total_files} changed file(s), {suggested_checks_total} suggested check(s)."
    else:
        message = f"Final review found {len(blocking_issues)} blocking issue(s)."
    return FinalReviewObservation(
        kind="final_review",
        ok=bool(review["ok"]),
        ready=ready,
        blocking_issues=blocking_issues,
        warnings=warnings,
        running_processes=running_processes,
        files=files,
        total_files=total_files,
        python=python,
        python_total=int(review["python_total"]),
        python_truncated=bool(review["python_truncated"]),
        config=config,
        config_total=int(review["config_total"]),
        config_truncated=bool(review["config_truncated"]),
        focused_test_commands=focused_test_commands,
        focused_test_commands_total=focused_test_commands_total,
        focused_test_commands_truncated=focused_test_commands_truncated,
        focused_test_related_tests_total=focused_test_related_tests_total,
        suggested_checks=suggested_checks,
        suggested_checks_total=suggested_checks_total,
        suggested_checks_truncated=suggested_checks_truncated,
        diff_check=str(review["diff_check"]),
        staged_diff_check=str(review["staged_diff_check"]),
        status=str(review["status"]),
        message=message,
    )


__all__ = ["execute_final_review_action", "final_review_observation", "review_changes_observation"]
