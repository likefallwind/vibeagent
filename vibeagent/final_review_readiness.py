from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .final_review_session_verification import final_review_session_verification_issues
from .types import FocusedTestCommand, SuggestedCheck
from .workspace_core import RunWorkspace


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


def build_final_review_readiness(
    workspace: RunWorkspace,
    inputs: FinalReviewReadinessInputs,
) -> FinalReviewReadiness:
    blocking_issues = build_final_review_blocking_issues(inputs)
    conflict_warnings = append_conflict_blockers(blocking_issues, inputs.conflict_scan)
    verification_blockers, verification_warnings = final_review_session_verification_issues(
        workspace,
        inputs.all_suggested_checks,
        inputs.focused_test_commands,
    )
    blocking_issues.extend(verification_blockers)

    warnings = build_final_review_warnings(inputs, conflict_warnings)
    warnings.extend(verification_warnings)
    return FinalReviewReadiness(blocking_issues=blocking_issues, warnings=warnings)


def build_final_review_blocking_issues(inputs: FinalReviewReadinessInputs) -> list[str]:
    review = inputs.review
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
    if inputs.all_suggested_checks_truncated:
        blocking_issues.append("Suggested verification checks exceed the maximum readiness scan.")
    unavailable = [item for item in inputs.all_suggested_checks if not item.available]
    if unavailable:
        blocking_issues.append("Suggested verification checks have missing executables.")
    if int(review["total_files"]) > inputs.files_shown:
        blocking_issues.append("Changed file review was incomplete.")
    if bool(review["python_truncated"]):
        blocking_issues.append("Python syntax check was incomplete.")
    if bool(review["config_truncated"]):
        blocking_issues.append("Config syntax check was incomplete.")
    if inputs.large_files_total:
        blocking_issues.append("Changed files include large artifacts.")
    if inputs.secret_findings_total or inputs.secret_diff_findings_total:
        blocking_issues.append("Changed files include secret-like values.")
    if inputs.secret_diff_warnings:
        blocking_issues.append("Secret-like diff scan was incomplete.")
    if inputs.nested_git_repo_total:
        blocking_issues.append("Project contains nested git repositories.")
    if inputs.changed_gitlink_total:
        blocking_issues.append("Changed files include git submodule links.")
    if inputs.changed_gitlink_warnings:
        blocking_issues.append("Git submodule link scan was incomplete.")
    if inputs.hidden_git_change_total:
        blocking_issues.append("Tracked changes are hidden by project safety filters.")
    if inputs.hidden_git_change_warnings:
        blocking_issues.append("Hidden tracked change scan was incomplete.")
    if inputs.unsafe_symlink_total:
        if "points outside project" in inputs.unsafe_symlink_reasons:
            blocking_issues.append("Changed symlinks point outside the project.")
        if "points into protected project path" in inputs.unsafe_symlink_reasons:
            blocking_issues.append("Changed symlinks point into protected project paths.")
        if "points into ignored project path" in inputs.unsafe_symlink_reasons:
            blocking_issues.append("Changed symlinks point into ignored project paths.")
    if inputs.unsafe_symlink_warnings:
        blocking_issues.append("Changed symlink scan was incomplete.")

    git_operations = git_operation_items(inputs.git_operation)
    if git_operations:
        blocking_issues.append("Git operation is still in progress.")
    elif not bool(inputs.git_operation.get("ok")):
        blocking_issues.append("Could not inspect git operation state.")
    if inputs.running_processes:
        blocking_issues.append("Background processes are still running.")
    if inputs.focused_test_commands_truncated:
        blocking_issues.append("Focused test suggestions exceed the maximum readiness scan.")
    return blocking_issues


def append_conflict_blockers(
    blocking_issues: list[str],
    conflict_scan: Mapping[str, object],
) -> list[str]:
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
    return conflict_warnings


def build_final_review_warnings(
    inputs: FinalReviewReadinessInputs,
    conflict_warnings: list[str],
) -> list[str]:
    warnings: list[str] = []
    warnings.extend(conflict_warnings)
    append_file_scan_warnings(warnings, inputs)
    append_secret_scan_warnings(warnings, inputs)
    append_git_structure_warnings(warnings, inputs)
    append_changed_file_warnings(warnings, inputs)
    append_suggested_check_warnings(warnings, inputs)
    append_runtime_warnings(warnings, inputs)
    return warnings


def append_file_scan_warnings(warnings: list[str], inputs: FinalReviewReadinessInputs) -> None:
    if inputs.large_files:
        large_preview = ", ".join(
            f"{item['path']} ({int(item['size_bytes'])} bytes)" for item in inputs.large_files[:5]
        )
        warnings.append(f"Large changed file(s) over {inputs.large_file_bytes} bytes: {large_preview}.")
    if inputs.large_files_total > len(inputs.large_files):
        warnings.append(f"Large changed file list truncated at {len(inputs.large_files)}/{inputs.large_files_total}.")


def append_secret_scan_warnings(warnings: list[str], inputs: FinalReviewReadinessInputs) -> None:
    if inputs.secret_findings:
        secret_preview = ", ".join(
            f"{item['path']}:{item['line']} {item['label']}" for item in inputs.secret_findings[:5]
        )
        warnings.append(f"Secret-like changed file value(s): {secret_preview}.")
    if inputs.secret_findings_total > len(inputs.secret_findings):
        warnings.append(
            f"Secret-like finding list truncated at {len(inputs.secret_findings)}/{inputs.secret_findings_total}."
        )
    if inputs.secret_scan_truncated:
        warnings.append(f"Secret scan inspected the first {inputs.secret_scan_bytes} bytes of some file(s).")
    if inputs.secret_diff_findings:
        secret_diff_preview = ", ".join(
            f"{item['path']}:{item['line']} {item['label']} ({item['source']})"
            for item in inputs.secret_diff_findings[:5]
        )
        warnings.append(f"Secret-like added diff value(s): {secret_diff_preview}.")
    if inputs.secret_diff_findings_total > len(inputs.secret_diff_findings):
        warnings.append(
            "Secret-like diff finding list truncated at "
            f"{len(inputs.secret_diff_findings)}/{inputs.secret_diff_findings_total}."
        )
    if inputs.secret_diff_truncated:
        warnings.append(f"Secret diff scan inspected the first {inputs.secret_scan_bytes} bytes of some diff output.")
    for warning in inputs.secret_diff_warnings[:2]:
        warnings.append(f"Could not inspect secret-like diff values: {warning}.")


def append_git_structure_warnings(warnings: list[str], inputs: FinalReviewReadinessInputs) -> None:
    if inputs.nested_git_repos:
        warnings.append(f"Nested git repos: {', '.join(inputs.nested_git_repos[:5])}.")
    if inputs.nested_git_repo_total > len(inputs.nested_git_repos):
        warnings.append(
            f"Nested git repo list truncated at {len(inputs.nested_git_repos)}/{inputs.nested_git_repo_total}."
        )
    if inputs.changed_gitlinks:
        warnings.append(f"Git submodule links: {', '.join(inputs.changed_gitlinks[:5])}.")
    if inputs.changed_gitlink_total > len(inputs.changed_gitlinks):
        warnings.append(
            f"Git submodule link list truncated at {len(inputs.changed_gitlinks)}/{inputs.changed_gitlink_total}."
        )
    for warning in inputs.changed_gitlink_warnings[:2]:
        warnings.append(f"Could not inspect git submodule links: {warning}.")
    if inputs.hidden_git_changes:
        hidden_preview = ", ".join(
            f"{item['status']} {item['path']}" for item in inputs.hidden_git_changes[:5]
        )
        warnings.append(f"Hidden tracked change(s): {hidden_preview}.")
    if inputs.hidden_git_change_total > len(inputs.hidden_git_changes):
        warnings.append(
            "Hidden tracked change list truncated at "
            f"{len(inputs.hidden_git_changes)}/{inputs.hidden_git_change_total}."
        )
    for warning in inputs.hidden_git_change_warnings[:2]:
        warnings.append(f"Could not inspect hidden tracked changes: {warning}.")
    if inputs.unsafe_symlinks:
        symlink_preview = ", ".join(
            f"{item['path']} -> {item['target']} ({item['reason']})" for item in inputs.unsafe_symlinks[:5]
        )
        warnings.append(f"Unsafe changed symlink(s): {symlink_preview}.")
    if inputs.unsafe_symlink_total > len(inputs.unsafe_symlinks):
        warnings.append(
            f"Unsafe symlink list truncated at {len(inputs.unsafe_symlinks)}/{inputs.unsafe_symlink_total}."
        )
    for warning in inputs.unsafe_symlink_warnings[:2]:
        warnings.append(f"Could not inspect changed symlinks: {warning}.")


def append_changed_file_warnings(warnings: list[str], inputs: FinalReviewReadinessInputs) -> None:
    review = inputs.review
    total_files = int(review["total_files"])
    if total_files == 0:
        warnings.append("No changed files detected.")
    if total_files > inputs.files_shown:
        warnings.append(f"Changed file list truncated at {inputs.files_shown}/{total_files}.")
    if bool(review["python_truncated"]):
        warnings.append(f"Python syntax checks truncated at {len(review['python'])}/{int(review['python_total'])}.")
    if bool(review["config_truncated"]):
        warnings.append(f"Config syntax checks truncated at {len(review['config'])}/{int(review['config_total'])}.")


def append_suggested_check_warnings(warnings: list[str], inputs: FinalReviewReadinessInputs) -> None:
    if inputs.suggested_checks_truncated:
        warnings.append(f"Suggested checks truncated at {len(inputs.suggested_checks)}/{inputs.suggested_checks_total}.")
    if inputs.focused_test_commands_truncated:
        warnings.append(
            f"Focused test suggestions truncated at {len(inputs.focused_test_commands)}/{inputs.focused_test_commands_total}."
        )
    if inputs.focused_test_warning:
        warnings.append(inputs.focused_test_warning)
    unavailable = [item for item in inputs.all_suggested_checks if not item.available]
    if unavailable:
        missing = ", ".join(sorted({item.missing_tool or item.command.split()[0] for item in unavailable})[:5])
        warnings.append(f"Some suggested checks have missing executables: {missing}.")


def append_runtime_warnings(warnings: list[str], inputs: FinalReviewReadinessInputs) -> None:
    append_git_sync_warnings(warnings, inputs.git_info)
    git_operations = git_operation_items(inputs.git_operation)
    if git_operations:
        operations_preview = ", ".join(
            str(item.get("operation", "unknown")) for item in git_operations[:5] if isinstance(item, dict)
        )
        warnings.append(f"Git operation in progress: {operations_preview}.")
    elif not bool(inputs.git_operation.get("ok")):
        warnings.append(f"Could not inspect git operation state: {inputs.git_operation.get('message') or 'unknown error'}.")
    if inputs.running_processes:
        warnings.append(
            f"{len(inputs.running_processes)} background process(es) still running; stop them before finishing if no longer needed."
        )


def append_git_sync_warnings(warnings: list[str], git_info: Mapping[str, object]) -> None:
    if not bool(git_info.get("ok")):
        return
    upstream = str(git_info.get("upstream") or "")
    if not upstream:
        return
    branch = str(git_info.get("branch") or "detached HEAD")
    ahead = int(git_info.get("ahead", 0) or 0)
    behind = int(git_info.get("behind", 0) or 0)
    if ahead > 0 and behind > 0:
        warnings.append(
            f"Branch {branch} has diverged from {upstream}: ahead {ahead}, behind {behind} based on cached refs."
        )
    elif ahead > 0:
        warnings.append(f"Branch {branch} is ahead of {upstream} by {ahead} commit(s).")
    elif behind > 0:
        warnings.append(f"Branch {branch} is behind {upstream} by {behind} commit(s) based on cached refs.")


def git_operation_items(git_operation: Mapping[str, object]) -> list[object]:
    return list(git_operation.get("operations", [])) if bool(git_operation.get("ok")) else []
