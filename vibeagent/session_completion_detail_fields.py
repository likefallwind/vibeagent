from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SessionCompletionDetailField:
    attr: str
    report_key: str
    prompt_label: str
    blocker_signal: bool = True


SESSION_COMPLETION_DETAIL_FIELDS = (
    SessionCompletionDetailField(
        attr="latest_completion_pending_verification_checks",
        report_key="latestPendingVerificationChecks",
        prompt_label="latestCompletionPendingCheck",
    ),
    SessionCompletionDetailField(
        attr="latest_completion_failed_verification_checks",
        report_key="latestFailedVerificationChecks",
        prompt_label="latestCompletionFailedCheck",
    ),
    SessionCompletionDetailField(
        attr="latest_completion_final_review_issues",
        report_key="latestFinalReviewBlockingIssues",
        prompt_label="latestCompletionFinalReviewIssue",
    ),
    SessionCompletionDetailField(
        attr="latest_completion_final_review_changed_files",
        report_key="latestFinalReviewChangedFiles",
        prompt_label="latestCompletionFinalReviewChangedFile",
        blocker_signal=False,
    ),
    SessionCompletionDetailField(
        attr="latest_completion_tool_errors",
        report_key="latestToolErrors",
        prompt_label="latestCompletionToolError",
    ),
    SessionCompletionDetailField(
        attr="latest_completion_checkpoint_failures",
        report_key="latestCheckpointFailures",
        prompt_label="latestCompletionCheckpointFailure",
    ),
    SessionCompletionDetailField(
        attr="latest_completion_active_background_processes",
        report_key="latestActiveBackgroundProcesses",
        prompt_label="latestCompletionActiveProcess",
    ),
    SessionCompletionDetailField(
        attr="latest_completion_denied_approvals",
        report_key="latestDeniedApprovals",
        prompt_label="latestCompletionDeniedApproval",
    ),
    SessionCompletionDetailField(
        attr="latest_completion_next_actions",
        report_key="latestNextActions",
        prompt_label="latestCompletionNextAction",
        blocker_signal=False,
    ),
)


def parse_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [
        str(item).strip()
        for item in value
        if isinstance(item, str) and item.strip()
    ]


def completion_detail_kwargs_from_report(completion: dict[str, object]) -> dict[str, list[str]]:
    return {
        field.attr: parse_string_list(completion.get(field.report_key))
        for field in SESSION_COMPLETION_DETAIL_FIELDS
    }


def completion_detail_kwargs_from_object(source: Any) -> dict[str, list[str]]:
    return {
        field.attr: list(value) if isinstance(value, list) else []
        for field in SESSION_COMPLETION_DETAIL_FIELDS
        for value in [getattr(source, field.attr, [])]
    }


def completion_detail_prompt_lines(source: Any, max_items: int = 20) -> list[str]:
    lines: list[str] = []
    for field in SESSION_COMPLETION_DETAIL_FIELDS:
        values = getattr(source, field.attr, [])
        if not isinstance(values, list):
            continue
        lines.extend(
            f"{field.prompt_label}: {value}"
            for value in values[:max_items]
            if isinstance(value, str) and value.strip()
        )
    return lines


def completion_blocker_detail_values(source: Any) -> list[str]:
    labels: list[str] = []
    for field in SESSION_COMPLETION_DETAIL_FIELDS:
        if not field.blocker_signal:
            continue
        values = getattr(source, field.attr, [])
        if not isinstance(values, list):
            continue
        labels.extend(str(value).strip() for value in values if isinstance(value, str) and value.strip())
    return labels
