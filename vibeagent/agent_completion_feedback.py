from __future__ import annotations


def format_completion_blocked_feedback(blockers: list[str], details: dict[str, list[str]] | None = None) -> str:
    lines = [
        "Completion is not ready. Continue working before giving a final answer.",
        "Resolve these blockers first:",
    ]
    lines.extend(f"- {blocker}" for blocker in blockers)
    details = details or {}
    failed_verification_checks = details.get("failedVerificationChecks", [])
    if failed_verification_checks:
        lines.append("Failed verification checks:")
        lines.extend(f"- {check}" for check in failed_verification_checks)
    pending_verification_checks = details.get("pendingVerificationChecks", [])
    if pending_verification_checks:
        lines.append("Pending verification checks:")
        lines.extend(f"- {check}" for check in pending_verification_checks)
    final_review_blocking_issues = details.get("finalReviewBlockingIssues", [])
    if final_review_blocking_issues:
        lines.append("Final review blocking issues:")
        lines.extend(f"- {issue}" for issue in final_review_blocking_issues)
    final_review_changed_files = details.get("finalReviewChangedFiles", [])
    if final_review_changed_files:
        lines.append("Final review changed files:")
        lines.extend(f"- {path}" for path in final_review_changed_files)
    tool_errors = details.get("toolErrors", [])
    if tool_errors:
        lines.append("Tool errors:")
        lines.extend(f"- {error}" for error in tool_errors)
    checkpoint_failures = details.get("checkpointFailures", [])
    if checkpoint_failures:
        lines.append("Checkpoint failures:")
        lines.extend(f"- {failure}" for failure in checkpoint_failures)
    active_background_processes = details.get("activeBackgroundProcesses", [])
    if active_background_processes:
        lines.append("Active background processes:")
        lines.extend(f"- {process}" for process in active_background_processes)
    denied_approvals = details.get("deniedApprovals", [])
    if denied_approvals:
        lines.append("Denied approvals:")
        lines.extend(f"- {approval}" for approval in denied_approvals)
    next_actions = details.get("nextActions", []) or completion_blocked_next_actions(blockers, details)
    if next_actions:
        lines.append("Next actions:")
        lines.extend(f"- {action}" for action in next_actions)
    lines.append("When the blockers are resolved, finish with a concise final answer.")
    return "\n".join(lines)


def completion_blocked_next_actions(blockers: list[str], details: dict[str, list[str]]) -> list[str]:
    actions: list[str] = []
    blockers_text = "\n".join(blockers).casefold()
    if "task plan" in blockers_text:
        actions.append("Use update_plan to mark completed items and keep exactly one active in_progress item while work remains.")
    if details.get("failedVerificationChecks"):
        actions.append("Use run_session_verification to rerun failed recorded checks, then session_output_diagnostics or session_output_contexts if failures remain.")
    if details.get("pendingVerificationChecks"):
        actions.append("Use run_session_verification to run pending recorded checks before trying to finish again.")
    if details.get("finalReviewBlockingIssues") or details.get("finalReviewChangedFiles"):
        actions.append("Inspect changed or failing files with read_file_context or git_diff_contexts, fix blockers, then rerun final_review.")
    if details.get("toolErrors"):
        actions.append("Retry or replace the failed tool call after correcting its input; inspect the error message before continuing.")
    if details.get("checkpointFailures"):
        actions.append("Continue carefully without assuming a restore point exists, or fix checkpoint creation before risky edits.")
    if details.get("activeBackgroundProcesses"):
        actions.append("Use list_processes and read_process to inspect active background processes; stop_process any process no longer needed before final_review.")
    if details.get("deniedApprovals"):
        actions.append("Choose an allowed alternative for denied approval requests, or ask the user before retrying the same protected action.")
    return actions
