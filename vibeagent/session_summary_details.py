from __future__ import annotations

from .session_summary_helpers import parse_string_list


CompletionDetailLists = tuple[
    list[str],
    list[str],
    list[str],
    list[str],
    list[str],
    list[str],
    list[str],
    list[str],
    list[str],
]


def parse_completion_detail_lists(details: dict[object, object]) -> CompletionDetailLists:
    return (
        parse_string_list(details.get("pendingVerificationChecks")),
        parse_string_list(details.get("failedVerificationChecks")),
        parse_string_list(details.get("finalReviewBlockingIssues")),
        parse_string_list(details.get("finalReviewChangedFiles")),
        parse_string_list(details.get("toolErrors")),
        parse_string_list(details.get("checkpointFailures")),
        parse_string_list(details.get("activeBackgroundProcesses")),
        parse_string_list(details.get("deniedApprovals")),
        parse_string_list(details.get("nextActions")),
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
