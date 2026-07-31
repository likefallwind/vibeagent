from __future__ import annotations

from .agent_observation_utils import observation_failed, summarize
from .agent_completion_details import (
    build_active_background_process_details,
    build_checkpoint_failure_details,
    build_denied_approval_details,
    build_final_review_blocking_issue_details,
    build_final_review_changed_file_details,
    build_tool_error_details,
    final_review_running_process_count,
)
from .agent_completion_feedback import completion_blocked_next_actions, format_completion_blocked_feedback
from .agent_completion_kinds import (
    FINITE_COMMAND_OBSERVATION_KINDS,
    MULTISTEP_CODING_FOLLOWUP_KINDS,
    PROJECT_CHANGE_OBSERVATION_KINDS,
)
from .agent_completion_recovery import (
    build_session_recovery_completion_blockers,
    build_session_recovery_completion_details,
)
from .agent_completion_verification import (
    build_failed_verification_checks,
    build_pending_verification_checks,
    build_verification_checks,
    command_result_failed_suggested_check_labels,
    command_result_failed_suggested_check_result,
    command_result_matches_successful_suggested_check,
    command_result_suggested_check_commands,
    failed_suggested_check_labels,
    failed_suggested_check_results,
    final_review_focused_test_commands,
    final_review_suggested_commands,
    final_review_verification_commands,
    latest_successful_auto_final_review_change_index,
    latest_successful_project_change_index,
    observation_runs_suggested_check_successfully,
    successful_suggested_check_commands,
    successful_suggested_check_labels,
    suggested_check_label,
    suggested_check_statuses_after_latest_change,
)
from .types import Observation, PlanItem


IGNORED_COMPLETION_FINAL_REVIEW_WARNINGS = frozenset({"No changed files detected."})
MAX_COMPLETION_FINAL_REVIEW_WARNINGS = 5
VerificationStatus = tuple[list[str], list[str], list[str]]


def auto_final_review_reason(success: bool, observations: list[Observation]) -> str | None:
    if not success:
        return None
    final_review_index = latest_observation_index(observations, {"final_review"})
    project_change_index = latest_successful_auto_final_review_change_index(observations)
    if project_change_index is not None:
        if final_review_index is None:
            return "Project changes completed without final_review"
        if project_change_index > final_review_index:
            return "Project changes completed after final_review"
    process_start_index = latest_successful_process_start_index(observations)
    if process_start_index is not None:
        if final_review_index is None:
            return "Background command started without final_review"
        if process_start_index > final_review_index:
            return "Background command started after final_review"
    command_index = latest_successful_finite_command_index(observations)
    if command_index is not None:
        if final_review_index is None:
            return "Command execution completed without final_review"
        if command_index > final_review_index:
            command_matches_review_check = finite_command_matches_final_review_check(
                observations[command_index],
                observations[final_review_index],
            )
            if not command_matches_review_check:
                return "Command execution completed after final_review"
            if getattr(observations[final_review_index], "ready", None) is False:
                return "Final review refreshed after verification"
    return None

def should_auto_run_final_review(success: bool, observations: list[Observation]) -> bool:
    return auto_final_review_reason(success, observations) is not None

def latest_observation_index(observations: list[Observation], kinds: set[str]) -> int | None:
    for index in range(len(observations) - 1, -1, -1):
        if observations[index].kind in kinds:
            return index
    return None

def latest_successful_process_start_index(observations: list[Observation]) -> int | None:
    for index in range(len(observations) - 1, -1, -1):
        observation = observations[index]
        if observation.kind == "start_command" and bool(getattr(observation, "ok", False)):
            return index
    return None

def latest_successful_finite_command_index(observations: list[Observation]) -> int | None:
    for index in range(len(observations) - 1, -1, -1):
        observation = observations[index]
        if observation.kind in FINITE_COMMAND_OBSERVATION_KINDS:
            if not observation_failed(observation):
                return index
    return None

def finite_command_matches_final_review_check(command_observation: Observation, final_review: Observation) -> bool:
    check_commands = final_review_suggested_commands(final_review) | final_review_focused_test_commands(final_review)
    if not check_commands:
        return False
    return bool(
        successful_suggested_check_commands(command_observation, check_commands)
        or failed_suggested_check_results(command_observation, check_commands)
    )

def build_completion_blocker_details(
    success: bool,
    observations: list[Observation],
    verification_status: VerificationStatus | None = None,
    blockers: list[str] | None = None,
) -> dict[str, list[str]]:
    details: dict[str, list[str]] = {}
    _, pending_verification_checks, failed_verification_checks = resolve_completion_verification_status(
        success,
        observations,
        verification_status,
    )
    if failed_verification_checks:
        details["failedVerificationChecks"] = failed_verification_checks
    if pending_verification_checks:
        details["pendingVerificationChecks"] = pending_verification_checks
    final_review_blocking_issues = build_final_review_blocking_issue_details(observations)
    if final_review_blocking_issues:
        details["finalReviewBlockingIssues"] = final_review_blocking_issues
    final_review_changed_files = build_final_review_changed_file_details(observations)
    if final_review_changed_files:
        details["finalReviewChangedFiles"] = final_review_changed_files
    tool_errors = build_tool_error_details(observations)
    if tool_errors:
        details["toolErrors"] = tool_errors
    checkpoint_failures = build_checkpoint_failure_details(observations)
    if checkpoint_failures:
        details["checkpointFailures"] = checkpoint_failures
    active_background_processes = build_active_background_process_details(observations)
    if active_background_processes:
        details["activeBackgroundProcesses"] = active_background_processes
    denied_approvals = build_denied_approval_details(observations)
    if denied_approvals:
        details["deniedApprovals"] = denied_approvals
    for key, values in build_session_recovery_completion_details(observations).items():
        if values and key not in details:
            details[key] = values
    blocker_values = blockers if blockers is not None else build_completion_blockers(success, observations, [], verification_status)
    next_actions = completion_blocked_next_actions(blocker_values, details) if blocker_values else []
    if next_actions:
        details["nextActions"] = merge_completion_next_actions(details.get("nextActions", []), next_actions)
    return details

def merge_completion_next_actions(existing: list[str], generated: list[str]) -> list[str]:
    actions: list[str] = []
    seen: set[str] = set()
    for action in [*existing, *generated]:
        if not isinstance(action, str):
            continue
        label = action.strip()
        if not label or label in seen:
            continue
        actions.append(label)
        seen.add(label)
    return actions

def build_completion_warnings(
    success: bool,
    observations: list[Observation],
    plan: list[PlanItem] | None = None,
    verification_status: VerificationStatus | None = None,
) -> list[str]:
    if not success:
        return []
    warnings: list[str] = []
    unfinished_plan_warning = build_unfinished_plan_warning(plan or [])
    if unfinished_plan_warning is not None:
        warnings.append(unfinished_plan_warning)
    missing_plan_warning = build_missing_plan_warning(success, observations, plan or [])
    if missing_plan_warning is not None:
        warnings.append(missing_plan_warning)
    reason = auto_final_review_reason(success, observations)
    if reason is not None:
        warnings.append(f"{reason} observation.")
    final_review = next((observation for observation in reversed(observations) if observation.kind == "final_review"), None)
    _, pending_verification_checks, failed_verification_checks = resolve_completion_verification_status(
        success,
        observations,
        verification_status,
    )
    if final_review_has_active_completion_blocker(final_review, failed_verification_checks, pending_verification_checks):
        warnings.append("Final review did not report ready.")
    warnings.extend(build_final_review_completion_warnings(final_review))
    tool_error_count = sum(1 for observation in observations if observation.kind == "tool_error")
    if tool_error_count:
        warnings.append("Tool execution error(s) occurred.")
    if any(observation.kind == "checkpoint_create" and observation_failed(observation) for observation in observations):
        warnings.append("Checkpoint creation failed; restore point may be unavailable.")
    running_process_count = final_review_running_process_count(final_review)
    if running_process_count:
        warnings.append(
            f"Final review reported {running_process_count} running background process(es). "
            "Stop them before finishing if they are no longer needed."
        )
    if failed_verification_checks:
        warnings.append("Suggested verification checks failed after the latest project change.")
    if pending_verification_checks:
        warnings.append("Suggested verification checks are still pending after the latest project change.")
    return warnings

def build_completion_blockers(
    success: bool,
    observations: list[Observation],
    plan: list[PlanItem],
    verification_status: VerificationStatus | None = None,
) -> list[str]:
    blockers: list[str] = []
    if not success:
        blockers.append("Run did not complete successfully.")
    unfinished_plan_warning = build_unfinished_plan_warning(plan)
    if unfinished_plan_warning is not None:
        blockers.append(unfinished_plan_warning)
    missing_plan_warning = build_missing_plan_warning(success, observations, plan)
    if missing_plan_warning is not None:
        blockers.append(missing_plan_warning)
    reason = auto_final_review_reason(success, observations)
    if reason is not None:
        blockers.append(f"{reason} observation.")
    final_review = next((observation for observation in reversed(observations) if observation.kind == "final_review"), None)
    _, pending_verification_checks, failed_verification_checks = resolve_completion_verification_status(
        success,
        observations,
        verification_status,
    )
    if final_review_has_active_completion_blocker(final_review, failed_verification_checks, pending_verification_checks):
        blockers.append("Final review did not report ready.")
    tool_error_count = sum(1 for observation in observations if observation.kind == "tool_error")
    if tool_error_count:
        blockers.append(f"{tool_error_count} tool error(s) occurred.")
    denied_approvals = build_denied_approval_details(observations)
    if denied_approvals:
        blockers.append(f"{len(denied_approvals)} approval request(s) were denied.")
    if any(observation.kind == "checkpoint_create" and observation_failed(observation) for observation in observations):
        blockers.append("Checkpoint creation failed; restore point may be unavailable.")
    running_process_count = final_review_running_process_count(final_review)
    if running_process_count:
        blockers.append(f"Final review reported {running_process_count} running background process(es).")
    if failed_verification_checks:
        blockers.append(f"{len(failed_verification_checks)} suggested verification check(s) failed after the latest project change.")
    if pending_verification_checks:
        blockers.append(f"{len(pending_verification_checks)} suggested verification check(s) are still pending after the latest project change.")
    blockers.extend(build_session_recovery_completion_blockers(observations))
    return blockers

def resolve_completion_verification_status(
    success: bool,
    observations: list[Observation],
    verification_status: VerificationStatus | None = None,
) -> VerificationStatus:
    if verification_status is not None and any(verification_status):
        return verification_status
    return (
        build_verification_checks(success, observations),
        build_pending_verification_checks(success, observations),
        build_failed_verification_checks(success, observations),
    )

def build_final_review_completion_warnings(final_review: Observation | None) -> list[str]:
    if final_review is None or getattr(final_review, "ready", None) is not True:
        return []
    raw_warnings = getattr(final_review, "warnings", None)
    if not isinstance(raw_warnings, list):
        return []
    review_warnings = [
        text
        for warning in raw_warnings
        if (text := str(warning).strip()) and text not in IGNORED_COMPLETION_FINAL_REVIEW_WARNINGS
    ]
    if not review_warnings:
        return []
    limited = review_warnings[:MAX_COMPLETION_FINAL_REVIEW_WARNINGS]
    completion_warnings = [f"Final review warning: {warning}" for warning in limited]
    omitted = len(review_warnings) - len(limited)
    if omitted > 0:
        completion_warnings.append(f"Final review warning: {omitted} additional warning(s) omitted.")
    return completion_warnings

def final_review_has_active_completion_blocker(
    final_review: Observation | None,
    failed_verification_checks: list[str],
    pending_verification_checks: list[str],
) -> bool:
    if final_review is None or getattr(final_review, "ready", None) is True:
        return False
    if failed_verification_checks or pending_verification_checks:
        return True
    blocking_issues = getattr(final_review, "blocking_issues", None)
    if not isinstance(blocking_issues, list) or not blocking_issues:
        return True
    return any(not final_review_issue_is_verification_only(str(issue)) for issue in blocking_issues)

def final_review_issue_is_verification_only(issue: str) -> bool:
    normalized = issue.casefold()
    return "suggested verification check" in normalized

def build_unfinished_plan_warning(plan: list[PlanItem]) -> str | None:
    unfinished = [item for item in plan if item.status != "completed"]
    if not unfinished:
        return None
    in_progress = [item for item in unfinished if item.status == "in_progress"]
    pending = [item for item in unfinished if item.status == "pending"]
    labels = [f"{item.status}: {summarize(item.step, 80)}" for item in unfinished[:3]]
    suffix = f"; {'; '.join(labels)}" if labels else ""
    status_parts: list[str] = []
    if in_progress:
        status_parts.append(f"{len(in_progress)} in_progress")
    if pending:
        status_parts.append(f"{len(pending)} pending")
    status_text = ", ".join(status_parts) if status_parts else f"{len(unfinished)} unfinished"
    return f"Task plan still has unfinished item(s): {status_text}{suffix}."

def build_missing_plan_warning(success: bool, observations: list[Observation], plan: list[PlanItem]) -> str | None:
    if not success or plan:
        return None
    if not observations_show_multistep_coding_work(observations):
        return None
    return "Task plan is missing for multi-step coding work; call update_plan with a short checklist before finishing."

def observations_show_multistep_coding_work(observations: list[Observation]) -> bool:
    successful_project_changes = [
        observation
        for observation in observations
        if observation.kind in PROJECT_CHANGE_OBSERVATION_KINDS and not observation_failed(observation)
    ]
    if not successful_project_changes:
        return False
    if len(successful_project_changes) >= 2:
        return True
    first_change_index = next(
        index
        for index, observation in enumerate(observations)
        if observation.kind in PROJECT_CHANGE_OBSERVATION_KINDS and not observation_failed(observation)
    )
    return any(observation.kind in MULTISTEP_CODING_FOLLOWUP_KINDS for observation in observations[first_change_index + 1 :])
