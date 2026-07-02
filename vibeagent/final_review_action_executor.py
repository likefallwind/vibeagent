from __future__ import annotations

from .final_review_actions import (
    FINAL_REVIEW_LARGE_FILE_BYTES,
    FINAL_REVIEW_SECRET_SCAN_BYTES,
    final_review_scan_file_items,
    final_review_session_verification_issues,
    find_changed_gitlinks,
    find_hidden_tracked_git_changes,
    find_large_changed_files,
    find_nested_git_repositories,
    find_secret_like_changed_files,
    find_secret_like_git_diff_additions,
    find_unsafe_changed_symlinks,
    read_git_operation_state,
)
from .process_runtime import list_background_processes
from .types import (
    AgentAction,
    ConfigCheckResult,
    FinalReviewAction,
    FinalReviewObservation,
    GitChangeFile,
    GitDiffHunk,
    Observation,
    PythonCheckResult,
    ReviewChangesAction,
    ReviewChangesObservation,
    SuggestedCheck,
    UntrackedFilePreview,
)
from .workspace import RunWorkspace, read_git_conflicts, review_project_changes, suggest_project_checks


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
    blocking_issues: list[str] = []
    if not bool(review["changes_ok"]):
        blocking_issues.append("Could not read git changes.")
    if not bool(review["diff_check_ok"]):
        blocking_issues.append("Unstaged diff whitespace check failed.")
    if not bool(review["staged_diff_check_ok"]):
        blocking_issues.append("Staged diff whitespace check failed.")
    if not bool(review["python_ok"]):
        blocking_issues.append("Changed Python files have syntax errors.")
    if not bool(review["config_ok"]):
        blocking_issues.append("Changed config files have syntax errors.")
    if all_suggested_checks_truncated:
        blocking_issues.append("Suggested verification checks exceed the maximum readiness scan.")
    unavailable = [item for item in all_suggested_checks if not item.available]
    if unavailable:
        blocking_issues.append("Suggested verification checks have missing executables.")
    if int(review["total_files"]) > len(files):
        blocking_issues.append("Changed file review was incomplete.")
    if bool(review["python_truncated"]):
        blocking_issues.append("Python syntax check was incomplete.")
    if bool(review["config_truncated"]):
        blocking_issues.append("Config syntax check was incomplete.")
    if large_files_total:
        blocking_issues.append("Changed files include large artifacts.")
    if secret_findings_total or secret_diff_findings_total:
        blocking_issues.append("Changed files include secret-like values.")
    if secret_diff_warnings:
        blocking_issues.append("Secret-like diff scan was incomplete.")
    if nested_git_repo_total:
        blocking_issues.append("Project contains nested git repositories.")
    if changed_gitlink_total:
        blocking_issues.append("Changed files include git submodule links.")
    if changed_gitlink_warnings:
        blocking_issues.append("Git submodule link scan was incomplete.")
    if hidden_git_change_total:
        blocking_issues.append("Tracked changes are hidden by project safety filters.")
    if hidden_git_change_warnings:
        blocking_issues.append("Hidden tracked change scan was incomplete.")
    if unsafe_symlink_total:
        if "points outside project" in unsafe_symlink_reasons:
            blocking_issues.append("Changed symlinks point outside the project.")
        if "points into protected project path" in unsafe_symlink_reasons:
            blocking_issues.append("Changed symlinks point into protected project paths.")
        if "points into ignored project path" in unsafe_symlink_reasons:
            blocking_issues.append("Changed symlinks point into ignored project paths.")
    if unsafe_symlink_warnings:
        blocking_issues.append("Changed symlink scan was incomplete.")
    git_operations = list(git_operation.get("operations", [])) if bool(git_operation.get("ok")) else []
    if git_operations:
        blocking_issues.append("Git operation is still in progress.")
    elif not bool(git_operation.get("ok")):
        blocking_issues.append("Could not inspect git operation state.")
    conflict_warnings: list[str] = []
    if bool(conflict_scan.get("ok")):
        if int(conflict_scan.get("unmerged_total", 0) or 0) > 0:
            blocking_issues.append("Unmerged git files are present.")
        if int(conflict_scan.get("markers_total", 0) or 0) > 0:
            blocking_issues.append("Unresolved merge conflict markers are present.")
        marker_items = list(conflict_scan.get("markers", []))
        if marker_items:
            marker_preview = ", ".join(
                f"{item['path']}:{item['line']} {item['marker']}" for item in marker_items[:5]
            )
            conflict_warnings.append(f"Conflict markers: {marker_preview}.")
        if bool(conflict_scan.get("truncated")):
            blocking_issues.append("Conflict marker scan was incomplete.")
            conflict_warnings.append("Conflict marker scan was truncated.")
    else:
        blocking_issues.append("Could not scan merge conflicts.")
        conflict_warnings.append(
            f"Could not scan merge conflicts: {conflict_scan.get('message') or 'unknown error'}."
        )
    verification_blockers, verification_warnings = final_review_session_verification_issues(
        workspace,
        all_suggested_checks,
    )
    blocking_issues.extend(verification_blockers)

    warnings: list[str] = []
    warnings.extend(conflict_warnings)
    if large_files:
        large_preview = ", ".join(
            f"{item['path']} ({int(item['size_bytes'])} bytes)" for item in large_files[:5]
        )
        warnings.append(f"Large changed file(s) over {FINAL_REVIEW_LARGE_FILE_BYTES} bytes: {large_preview}.")
    if large_files_total > len(large_files):
        warnings.append(f"Large changed file list truncated at {len(large_files)}/{large_files_total}.")
    if secret_findings:
        secret_preview = ", ".join(
            f"{item['path']}:{item['line']} {item['label']}" for item in secret_findings[:5]
        )
        warnings.append(f"Secret-like changed file value(s): {secret_preview}.")
    if secret_findings_total > len(secret_findings):
        warnings.append(f"Secret-like finding list truncated at {len(secret_findings)}/{secret_findings_total}.")
    if secret_scan_truncated:
        warnings.append(f"Secret scan inspected the first {FINAL_REVIEW_SECRET_SCAN_BYTES} bytes of some file(s).")
    if secret_diff_findings:
        secret_diff_preview = ", ".join(
            f"{item['path']}:{item['line']} {item['label']} ({item['source']})" for item in secret_diff_findings[:5]
        )
        warnings.append(f"Secret-like added diff value(s): {secret_diff_preview}.")
    if secret_diff_findings_total > len(secret_diff_findings):
        warnings.append(f"Secret-like diff finding list truncated at {len(secret_diff_findings)}/{secret_diff_findings_total}.")
    if secret_diff_truncated:
        warnings.append(f"Secret diff scan inspected the first {FINAL_REVIEW_SECRET_SCAN_BYTES} bytes of some diff output.")
    for warning in secret_diff_warnings[:2]:
        warnings.append(f"Could not inspect secret-like diff values: {warning}.")
    if nested_git_repos:
        warnings.append(f"Nested git repos: {', '.join(nested_git_repos[:5])}.")
    if nested_git_repo_total > len(nested_git_repos):
        warnings.append(f"Nested git repo list truncated at {len(nested_git_repos)}/{nested_git_repo_total}.")
    if changed_gitlinks:
        warnings.append(f"Git submodule links: {', '.join(changed_gitlinks[:5])}.")
    if changed_gitlink_total > len(changed_gitlinks):
        warnings.append(f"Git submodule link list truncated at {len(changed_gitlinks)}/{changed_gitlink_total}.")
    for warning in changed_gitlink_warnings[:2]:
        warnings.append(f"Could not inspect git submodule links: {warning}.")
    if hidden_git_changes:
        hidden_preview = ", ".join(
            f"{item['status']} {item['path']}" for item in hidden_git_changes[:5]
        )
        warnings.append(f"Hidden tracked change(s): {hidden_preview}.")
    if hidden_git_change_total > len(hidden_git_changes):
        warnings.append(f"Hidden tracked change list truncated at {len(hidden_git_changes)}/{hidden_git_change_total}.")
    for warning in hidden_git_change_warnings[:2]:
        warnings.append(f"Could not inspect hidden tracked changes: {warning}.")
    if unsafe_symlinks:
        symlink_preview = ", ".join(
            f"{item['path']} -> {item['target']} ({item['reason']})" for item in unsafe_symlinks[:5]
        )
        warnings.append(f"Unsafe changed symlink(s): {symlink_preview}.")
    if unsafe_symlink_total > len(unsafe_symlinks):
        warnings.append(f"Unsafe symlink list truncated at {len(unsafe_symlinks)}/{unsafe_symlink_total}.")
    for warning in unsafe_symlink_warnings[:2]:
        warnings.append(f"Could not inspect changed symlinks: {warning}.")
    if git_operations:
        operations_preview = ", ".join(str(item.get("operation", "unknown")) for item in git_operations[:5] if isinstance(item, dict))
        warnings.append(f"Git operation in progress: {operations_preview}.")
    elif not bool(git_operation.get("ok")):
        warnings.append(f"Could not inspect git operation state: {git_operation.get('message') or 'unknown error'}.")
    total_files = int(review["total_files"])
    if total_files == 0:
        warnings.append("No changed files detected.")
    if total_files > len(files):
        warnings.append(f"Changed file list truncated at {len(files)}/{total_files}.")
    if bool(review["python_truncated"]):
        warnings.append(f"Python syntax checks truncated at {len(review['python'])}/{int(review['python_total'])}.")
    if bool(review["config_truncated"]):
        warnings.append(f"Config syntax checks truncated at {len(review['config'])}/{int(review['config_total'])}.")
    if suggested_checks_truncated:
        warnings.append(f"Suggested checks truncated at {len(suggested_checks)}/{suggested_checks_total}.")
    if unavailable:
        missing = ", ".join(sorted({item.missing_tool or item.command.split()[0] for item in unavailable})[:5])
        warnings.append(f"Some suggested checks have missing executables: {missing}.")
    if running_processes:
        warnings.append(
            f"{len(running_processes)} background process(es) still running; stop them before finishing if no longer needed."
        )
    warnings.extend(verification_warnings)

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
        suggested_checks=suggested_checks,
        suggested_checks_total=suggested_checks_total,
        suggested_checks_truncated=suggested_checks_truncated,
        diff_check=str(review["diff_check"]),
        staged_diff_check=str(review["staged_diff_check"]),
        status=str(review["status"]),
        message=message,
    )


__all__ = ["execute_final_review_action", "final_review_observation", "review_changes_observation"]
