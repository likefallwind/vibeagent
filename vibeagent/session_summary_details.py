from __future__ import annotations

from dataclasses import dataclass

from .session_summary_helpers import parse_string_list


@dataclass(frozen=True)
class CompletionDetailLists:
    pending_verification_checks: list[str]
    failed_verification_checks: list[str]
    final_review_issues: list[str]
    final_review_changed_files: list[str]
    tool_errors: list[str]
    checkpoint_failures: list[str]
    active_background_processes: list[str]
    denied_approvals: list[str]
    next_actions: list[str]


def empty_completion_detail_lists() -> CompletionDetailLists:
    return CompletionDetailLists(
        pending_verification_checks=[],
        failed_verification_checks=[],
        final_review_issues=[],
        final_review_changed_files=[],
        tool_errors=[],
        checkpoint_failures=[],
        active_background_processes=[],
        denied_approvals=[],
        next_actions=[],
    )


def parse_completion_detail_lists(details: dict[object, object]) -> CompletionDetailLists:
    return CompletionDetailLists(
        pending_verification_checks=parse_string_list(details.get("pendingVerificationChecks")),
        failed_verification_checks=parse_string_list(details.get("failedVerificationChecks")),
        final_review_issues=parse_string_list(details.get("finalReviewBlockingIssues")),
        final_review_changed_files=parse_string_list(details.get("finalReviewChangedFiles")),
        tool_errors=parse_string_list(details.get("toolErrors")),
        checkpoint_failures=parse_string_list(details.get("checkpointFailures")),
        active_background_processes=parse_string_list(details.get("activeBackgroundProcesses")),
        denied_approvals=parse_string_list(details.get("deniedApprovals")),
        next_actions=parse_string_list(details.get("nextActions")),
    )


def merge_nonempty_completion_detail_lists(
    previous: CompletionDetailLists,
    updates: CompletionDetailLists,
) -> CompletionDetailLists:
    return CompletionDetailLists(
        pending_verification_checks=updates.pending_verification_checks or previous.pending_verification_checks,
        failed_verification_checks=updates.failed_verification_checks or previous.failed_verification_checks,
        final_review_issues=updates.final_review_issues or previous.final_review_issues,
        final_review_changed_files=updates.final_review_changed_files or previous.final_review_changed_files,
        tool_errors=updates.tool_errors or previous.tool_errors,
        checkpoint_failures=updates.checkpoint_failures or previous.checkpoint_failures,
        active_background_processes=updates.active_background_processes or previous.active_background_processes,
        denied_approvals=updates.denied_approvals or previous.denied_approvals,
        next_actions=updates.next_actions or previous.next_actions,
    )


def subagent_failure_label(result: dict[object, object]) -> str | None:
    parts: list[str] = []
    task = result.get("task")
    if isinstance(task, str) and task.strip():
        parts.append(f"task={task.strip()}")
    agent = result.get("agent")
    if isinstance(agent, str) and agent.strip():
        parts.append(f"agent={agent.strip()}")
    mode = result.get("mode")
    if isinstance(mode, str) and mode.strip():
        parts.append(f"mode={mode.strip()}")
    message = result.get("message")
    if isinstance(message, str) and message.strip():
        parts.append(f"message={message.strip()}")
    return "; ".join(parts) if parts else None
