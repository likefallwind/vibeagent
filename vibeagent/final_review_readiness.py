from __future__ import annotations

from .final_review_session_verification import final_review_session_verification_issues
from .final_review_readiness_reports import (
    append_changed_file_warnings,
    append_conflict_blockers,
    append_file_scan_warnings,
    append_git_structure_warnings,
    append_git_sync_warnings,
    append_runtime_warnings,
    append_secret_scan_warnings,
    append_suggested_check_warnings,
    build_final_review_blocking_issues,
    build_final_review_warnings,
    git_operation_items,
)
from .final_review_readiness_types import FinalReviewReadiness, FinalReviewReadinessInputs
from .workspace_core import RunWorkspace


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
