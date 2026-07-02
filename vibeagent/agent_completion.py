from __future__ import annotations

from .agent_observation_utils import observation_failed, summarize
from .types import Observation, PlanItem


PROJECT_CHANGE_OBSERVATION_KINDS = {
    "write_file",
    "write_files",
    "edit_file",
    "multi_edit_file",
    "replace_python_definition",
    "code_rename",
    "python_rename",
    "replace_lines",
    "insert_lines",
    "append_file",
    "regex_replace",
    "json_set",
    "json_remove",
    "json_patch",
    "patch_file",
    "patch_files",
    "delete_file",
    "delete_files",
    "move_file",
    "move_files",
    "copy_file",
    "copy_files",
    "move_dir",
    "move_dirs",
    "copy_dir",
    "copy_dirs",
    "create_dir",
    "create_dirs",
    "delete_empty_dir",
    "delete_empty_dirs",
    "set_executable",
    "git_stage",
    "git_unstage",
    "git_commit",
    "git_restore",
    "checkpoint_restore",
}

MULTISTEP_CODING_FOLLOWUP_KINDS = {
    "run_command",
    "run_commands",
    "run_suggested_checks",
    "run_focused_test_commands",
    "python_check",
    "config_check",
    "command_check",
    "check_run_commands",
    "check_suggested_checks",
    "check_focused_test_commands",
}

def auto_final_review_reason(success: bool, observations: list[Observation]) -> str | None:
    if not success:
        return None
    final_review_index = latest_observation_index(observations, {"final_review"})
    project_change_index = latest_successful_project_change_index(observations)
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

def build_completion_blocker_details(success: bool, observations: list[Observation]) -> dict[str, list[str]]:
    details: dict[str, list[str]] = {}
    failed_verification_checks = build_failed_verification_checks(success, observations)
    if failed_verification_checks:
        details["failedVerificationChecks"] = failed_verification_checks
    pending_verification_checks = build_pending_verification_checks(success, observations)
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
    return details

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
    lines.append("When the blockers are resolved, finish with a concise final answer.")
    return "\n".join(lines)

def build_completion_warnings(
    success: bool,
    observations: list[Observation],
    plan: list[PlanItem] | None = None,
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
    failed_verification_checks = build_failed_verification_checks(success, observations)
    pending_verification_checks = build_pending_verification_checks(success, observations)
    if final_review_has_active_completion_blocker(final_review, failed_verification_checks, pending_verification_checks):
        warnings.append("Final review did not report ready.")
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

def build_completion_blockers(success: bool, observations: list[Observation], plan: list[PlanItem]) -> list[str]:
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
    failed_verification_checks = build_failed_verification_checks(success, observations)
    pending_verification_checks = build_pending_verification_checks(success, observations)
    if final_review_has_active_completion_blocker(final_review, failed_verification_checks, pending_verification_checks):
        blockers.append("Final review did not report ready.")
    tool_error_count = sum(1 for observation in observations if observation.kind == "tool_error")
    if tool_error_count:
        blockers.append(f"{tool_error_count} tool error(s) occurred.")
    denied_approvals = sum(1 for observation in observations if observation.kind == "approval_denied")
    if denied_approvals:
        blockers.append(f"{denied_approvals} approval request(s) were denied.")
    if any(observation.kind == "checkpoint_create" and observation_failed(observation) for observation in observations):
        blockers.append("Checkpoint creation failed; restore point may be unavailable.")
    running_process_count = final_review_running_process_count(final_review)
    if running_process_count:
        blockers.append(f"Final review reported {running_process_count} running background process(es).")
    if failed_verification_checks:
        blockers.append(f"{len(failed_verification_checks)} suggested verification check(s) failed after the latest project change.")
    if pending_verification_checks:
        blockers.append(f"{len(pending_verification_checks)} suggested verification check(s) are still pending after the latest project change.")
    return blockers

def final_review_has_active_completion_blocker(
    final_review: Observation | None,
    failed_verification_checks: list[str],
    pending_verification_checks: list[str],
) -> bool:
    if final_review is None or getattr(final_review, "ready", None) is not False:
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

def final_review_running_process_count(final_review: Observation | None) -> int:
    if final_review is None:
        return 0
    running_processes = getattr(final_review, "running_processes", [])
    return sum(1 for process in running_processes if getattr(process, "running", False))

def build_active_background_process_details(observations: list[Observation]) -> list[str]:
    final_review = next((observation for observation in reversed(observations) if observation.kind == "final_review"), None)
    if final_review is None:
        return []
    running_processes = getattr(final_review, "running_processes", [])
    details: list[str] = []
    for process in running_processes:
        if not getattr(process, "running", False):
            continue
        process_id = str(getattr(process, "process_id", "unknown") or "unknown")
        pid = getattr(process, "pid", None)
        cwd = str(getattr(process, "cwd", ".") or ".")
        command = str(getattr(process, "command", "") or "")
        details.append(f"{process_id}: pid={pid if pid is not None else 'unknown'}, cwd={cwd}, command={command}")
    return details

def build_final_review_blocking_issue_details(observations: list[Observation]) -> list[str]:
    final_review = next((observation for observation in reversed(observations) if observation.kind == "final_review"), None)
    if final_review is None:
        return []
    issues = getattr(final_review, "blocking_issues", [])
    if not isinstance(issues, list):
        return []
    return [str(issue) for issue in issues if str(issue).strip()]

def build_final_review_changed_file_details(observations: list[Observation]) -> list[str]:
    final_review = next((observation for observation in reversed(observations) if observation.kind == "final_review"), None)
    if final_review is None:
        return []
    files = getattr(final_review, "files", [])
    if not isinstance(files, list):
        return []
    details: list[str] = []
    for file in files:
        path = str(getattr(file, "path", "") or "").strip()
        if not path:
            continue
        status = str(getattr(file, "status", "") or "?").strip() or "?"
        details.append(f"{status} {path}")
    return details

def build_tool_error_details(observations: list[Observation]) -> list[str]:
    details: list[str] = []
    for observation in observations:
        if observation.kind != "tool_error":
            continue
        tool = str(getattr(observation, "tool", "unknown") or "unknown")
        message = str(getattr(observation, "message", "") or "tool execution failed")
        details.append(f"{tool}: {message}")
    return details

def build_checkpoint_failure_details(observations: list[Observation]) -> list[str]:
    details: list[str] = []
    for observation in observations:
        if observation.kind != "checkpoint_create" or not observation_failed(observation):
            continue
        message = str(getattr(observation, "message", "") or "checkpoint creation failed")
        details.append(f"checkpoint_create: {message}")
    return details

def build_denied_approval_details(observations: list[Observation]) -> list[str]:
    details: list[str] = []
    for observation in observations:
        if observation.kind != "approval_denied":
            continue
        action_type = str(getattr(observation, "action_type", "unknown") or "unknown")
        target = str(getattr(observation, "target", "") or "")
        message = str(getattr(observation, "message", "") or "")
        detail = action_type
        if target:
            detail += f" {target}"
        if message:
            detail += f": {message}"
        details.append(detail)
    return details

def build_verification_checks(success: bool, observations: list[Observation]) -> list[str]:
    if not success:
        return []
    final_review = next((observation for observation in reversed(observations) if observation.kind == "final_review"), None)
    if final_review is None:
        return []
    verification_commands = final_review_verification_commands(final_review)
    if not verification_commands:
        return []
    last_change_index = latest_successful_project_change_index(observations)
    if last_change_index is None:
        return []

    checks: list[str] = []
    seen: set[str] = set()
    for observation in observations[last_change_index + 1 :]:
        for label in successful_suggested_check_labels(observation, verification_commands):
            if label not in seen:
                checks.append(label)
                seen.add(label)
    return checks

def build_pending_verification_checks(success: bool, observations: list[Observation]) -> list[str]:
    verification_commands, statuses = suggested_check_statuses_after_latest_change(success, observations)
    if not verification_commands:
        return []
    completed_commands = set(statuses)
    return [suggested_check_label(command, cwd) for command, cwd in sorted(verification_commands - completed_commands)]

def build_failed_verification_checks(success: bool, observations: list[Observation]) -> list[str]:
    _, statuses = suggested_check_statuses_after_latest_change(success, observations)
    return [label for _, (passed, label) in sorted(statuses.items()) if not passed]

def suggested_check_statuses_after_latest_change(
    success: bool,
    observations: list[Observation],
) -> tuple[set[tuple[str, str]], dict[tuple[str, str], tuple[bool, str]]]:
    if not success:
        return set(), {}
    final_review = next((observation for observation in reversed(observations) if observation.kind == "final_review"), None)
    if final_review is None:
        return set(), {}
    verification_commands = final_review_verification_commands(final_review)
    if not verification_commands:
        return set(), {}
    last_change_index = latest_successful_project_change_index(observations)
    if last_change_index is None:
        return verification_commands, {}

    statuses: dict[tuple[str, str], tuple[bool, str]] = {}
    for observation in observations[last_change_index + 1 :]:
        for command, cwd in successful_suggested_check_commands(observation, verification_commands):
            statuses[(command, cwd)] = (True, suggested_check_label(command, cwd))
        for command, cwd, label in failed_suggested_check_results(observation, verification_commands):
            statuses[(command, cwd)] = (False, label)
    return verification_commands, statuses

def final_review_verification_commands(final_review: Observation) -> set[tuple[str, str]]:
    suggested_commands = final_review_suggested_commands(final_review)
    if suggested_commands:
        return suggested_commands
    return final_review_focused_test_commands(final_review)

def final_review_suggested_commands(final_review: Observation) -> set[tuple[str, str]]:
    return {
        (str(getattr(check, "command", "")), str(getattr(check, "cwd", ".") or "."))
        for check in getattr(final_review, "suggested_checks", [])
        if getattr(check, "command", None)
    }

def final_review_focused_test_commands(final_review: Observation) -> set[tuple[str, str]]:
    return {
        (str(getattr(command, "command", "")), str(getattr(command, "cwd", ".") or "."))
        for command in getattr(final_review, "focused_test_commands", [])
        if getattr(command, "command", None)
    }

def latest_successful_project_change_index(observations: list[Observation]) -> int | None:
    for index in range(len(observations) - 1, -1, -1):
        observation = observations[index]
        if observation.kind in PROJECT_CHANGE_OBSERVATION_KINDS and not observation_failed(observation):
            return index
    return None

def observation_runs_suggested_check_successfully(
    observation: Observation,
    suggested_commands: set[tuple[str, str]],
) -> bool:
    return bool(successful_suggested_check_commands(observation, suggested_commands))

def successful_suggested_check_commands(
    observation: Observation,
    suggested_commands: set[tuple[str, str]],
) -> set[tuple[str, str]]:
    if observation.kind == "run_command":
        return command_result_suggested_check_commands(observation.result, suggested_commands)
    if observation.kind in {"run_commands", "run_suggested_checks", "run_focused_test_commands"}:
        commands: set[tuple[str, str]] = set()
        for result in observation.results:
            commands.update(command_result_suggested_check_commands(result, suggested_commands))
        return commands
    return set()

def successful_suggested_check_labels(
    observation: Observation,
    suggested_commands: set[tuple[str, str]],
) -> list[str]:
    return [suggested_check_label(command, cwd) for command, cwd in successful_suggested_check_commands(observation, suggested_commands)]

def failed_suggested_check_labels(
    observation: Observation,
    suggested_commands: set[tuple[str, str]],
) -> list[str]:
    return [label for _, _, label in failed_suggested_check_results(observation, suggested_commands)]

def failed_suggested_check_results(
    observation: Observation,
    suggested_commands: set[tuple[str, str]],
) -> list[tuple[str, str, str]]:
    if observation.kind == "run_command":
        result = command_result_failed_suggested_check_result(observation.result, suggested_commands)
        return [result] if result is not None else []
    if observation.kind in {"run_commands", "run_suggested_checks", "run_focused_test_commands"}:
        failures: list[tuple[str, str, str]] = []
        for result in observation.results:
            failure = command_result_failed_suggested_check_result(result, suggested_commands)
            if failure is not None:
                failures.append(failure)
        return failures
    return []

def command_result_suggested_check_commands(
    result: object,
    suggested_commands: set[tuple[str, str]],
) -> set[tuple[str, str]]:
    if not command_result_matches_successful_suggested_check(result, suggested_commands):
        return set()
    command = str(getattr(result, "command", ""))
    cwd = str(getattr(result, "cwd", ".") or ".")
    return {(command, cwd)}

def command_result_failed_suggested_check_labels(
    result: object,
    suggested_commands: set[tuple[str, str]],
) -> list[str]:
    failure = command_result_failed_suggested_check_result(result, suggested_commands)
    return [failure[2]] if failure is not None else []

def command_result_failed_suggested_check_result(
    result: object,
    suggested_commands: set[tuple[str, str]],
) -> tuple[str, str, str] | None:
    command = str(getattr(result, "command", ""))
    cwd = str(getattr(result, "cwd", ".") or ".")
    if (command, cwd) not in suggested_commands:
        return None
    if getattr(result, "exit_code", None) == 0 and not getattr(result, "timed_out", False):
        return None
    if getattr(result, "timed_out", False):
        reason = "timed out"
    else:
        exit_code = getattr(result, "exit_code", None)
        reason = f"exit={exit_code}" if exit_code is not None else "no exit code"
    return command, cwd, f"{suggested_check_label(command, cwd)} ({reason})"

def suggested_check_label(command: str, cwd: str) -> str:
    if cwd == ".":
        return command
    return f"{command} (cwd: {cwd})"

def command_result_matches_successful_suggested_check(
    result: object,
    suggested_commands: set[tuple[str, str]],
) -> bool:
    if getattr(result, "exit_code", None) != 0 or getattr(result, "timed_out", False):
        return False
    command = str(getattr(result, "command", ""))
    cwd = str(getattr(result, "cwd", ".") or ".")
    return (command, cwd) in suggested_commands
