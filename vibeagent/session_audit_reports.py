from __future__ import annotations

from typing import Any

from .session_summary_reports import (
    CHECKPOINT_RESTORE_HINT,
    format_final_review_failure_lines,
    format_latest_completion_detail_lines,
    session_summary_status,
)
from .session_audit_formatting import (
    format_session_audit_report_text,
    format_session_handoff_report_text,
    format_session_verification_report_text,
)
from .session_types import SessionPlanItem, SessionSummary
from .session_utils import compact
from .session_verification_reports import limited_string_group


def format_session_handoff_sections(run_id: str, sections: list[tuple[str, str]]) -> str:
    lines = ["Session handoff:", f"  session: {run_id}"]
    for title, text in sections:
        lines.append(f"  {title}:")
        lines.extend(f"    {line}" for line in text.splitlines())
    return "\n".join(lines)


def format_session_handoff_readiness(
    summary: SessionSummary,
    failures: list[dict[str, str | int]],
    files: list[dict[str, Any]],
    max_text: int = 500,
) -> str:
    blockers = session_audit_blockers(summary, failures, files)
    lines = [
        "Session readiness:",
        f"  ready: {'yes' if not blockers else 'no'}",
        f"  status: {'ready' if not blockers else 'blocked'}",
    ]
    if summary.final_review_seen:
        ready = "yes" if summary.final_review_ready is True else "no" if summary.final_review_ready is False else "unknown"
        lines.append(
            "  finalReview: "
            f"ready={ready}, "
            f"blocking={summary.final_review_blocking_issues}, "
            f"warnings={summary.final_review_warnings}"
        )
        if summary.final_review_changed_files:
            lines.append("  finalReviewChangedFiles:")
            lines.extend(f"    - {compact(path, max_text)}" for path in summary.final_review_changed_files[:20])
            if len(summary.final_review_changed_files) > 20:
                lines.append(f"    - ... {len(summary.final_review_changed_files) - 20} more")
        lines.extend(format_final_review_failure_lines(summary, indent="  ", max_text=max_text))
    else:
        lines.append("  finalReview: not run")
    if summary.checkpoints_created:
        checkpoint_line = (
            "  checkpoints: "
            f"created={summary.checkpoints_created}, "
            f"auto={summary.auto_checkpoints_created}"
        )
        if summary.latest_checkpoint_id:
            checkpoint_line += f", latest={compact(summary.latest_checkpoint_id, max_text)}"
        lines.append(checkpoint_line)
        if summary.latest_checkpoint_id:
            lines.append(f"  restoreHint: {CHECKPOINT_RESTORE_HINT}")
    if summary.background_processes_started or summary.active_background_processes:
        lines.append(
            "  backgroundProcesses: "
            f"started={summary.background_processes_started}, "
            f"active={len(summary.active_background_processes)}"
        )
    lines.append("  blockers:")
    if blockers:
        lines.extend(f"    - {compact(blocker, max_text)}" for blocker in blockers)
    else:
        lines.append("    - none")
    if summary.completion_ready is not None:
        lines.append(f"  completionReady: {'yes' if summary.completion_ready else 'no'}")
    if summary.completion_blockers:
        lines.append("  completionBlockers:")
        lines.extend(f"    - {compact(blocker, max_text)}" for blocker in summary.completion_blockers)
    if summary.completion_blocked_count:
        lines.append(f"  completionBlocked: {summary.completion_blocked_count}")
        if summary.latest_completion_blockers:
            lines.append("  latestCompletionBlockers:")
            lines.extend(f"    - {compact(blocker, max_text)}" for blocker in summary.latest_completion_blockers)
        lines.extend(format_latest_completion_detail_lines(summary, indent="  ", max_text=max_text))
    if summary.completion_warnings:
        lines.append("  completionWarnings:")
        lines.extend(f"    - {compact(warning, max_text)}" for warning in summary.completion_warnings)
    return "\n".join(lines)


def session_pending_plan_items(summary: SessionSummary) -> list[SessionPlanItem]:
    return [
        item
        for item in summary.latest_plan
        if item.status not in {"completed", "done", "skipped"}
    ]


def session_audit_blockers(
    summary: SessionSummary,
    failures: list[dict[str, str | int]],
    files: list[dict[str, Any]],
) -> list[str]:
    blockers: list[str] = []
    pending_plan_items = session_pending_plan_items(summary)
    checkpoint_failures = failed_checkpoint_create_count(failures)
    if summary.failed:
        blockers.append("session status is failed")
    elif summary.blocked:
        blockers.append("session status is blocked")
    elif not summary.completed:
        blockers.append("session status is incomplete")
    if summary.completion_ready is False:
        if summary.completion_blockers:
            blockers.append(f"{len(summary.completion_blockers)} completion blocker(s)")
        else:
            blockers.append("completion is not ready")
    if summary.malformed_count:
        blockers.append(f"{summary.malformed_count} malformed session row(s)")
    denied_approval_blocker_count = session_audit_denied_approval_blocker_count(summary)
    if denied_approval_blocker_count:
        blockers.append(f"{denied_approval_blocker_count} denied approval(s)")
    if failures and (summary.failed or not summary.completed):
        blockers.append(f"{len(failures)} failure event(s)")
    if checkpoint_failures:
        blockers.append(f"{checkpoint_failures} checkpoint creation failure(s); restore point may be unavailable")
    if summary.final_review_seen and summary.final_review_ready is False:
        blockers.append("final review is not ready")
    if not summary.final_review_seen and files:
        blockers.append("changed files exist but final_review has not run")
    if not summary.final_review_seen and summary.background_processes_started:
        blockers.append("background process(es) were started but final_review has not run")
    if summary.pending_verification_checks:
        blockers.append(f"{len(summary.pending_verification_checks)} pending verification check(s)")
    if summary.failed_verification_checks:
        blockers.append(f"{len(summary.failed_verification_checks)} failed verification check(s)")
    if pending_plan_items:
        blockers.append(f"{len(pending_plan_items)} non-completed plan item(s)")
    if summary.active_background_processes:
        blockers.append(f"{len(summary.active_background_processes)} active background process(es)")
    return blockers


def session_audit_denied_approval_blocker_count(summary: SessionSummary) -> int:
    if summary.completion_ready is True:
        return 0
    if summary.latest_completion_denied_approvals:
        return len(summary.latest_completion_denied_approvals)
    if summary.completion_ready is False or not summary.completed:
        return summary.approvals_denied
    return 0


def validate_session_audit_limits(
    max_failures: int,
    max_files: int,
    max_commands: int,
    max_checks: int,
    max_text: int,
) -> None:
    if max_failures < 1:
        raise ValueError("max_failures must be at least 1.")
    if max_failures > 200:
        raise ValueError("max_failures must be at most 200.")
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 500:
        raise ValueError("max_files must be at most 500.")
    if max_commands < 1:
        raise ValueError("max_commands must be at least 1.")
    if max_commands > 100:
        raise ValueError("max_commands must be at most 100.")
    if max_checks < 1:
        raise ValueError("max_checks must be at least 1.")
    if max_checks > 500:
        raise ValueError("max_checks must be at most 500.")
    if max_text < 80:
        raise ValueError("max_text must be at least 80.")
    if max_text > 5000:
        raise ValueError("max_text must be at most 5000.")


def validate_session_handoff_limits(max_output_chars: int) -> None:
    if max_output_chars < 0:
        raise ValueError("max_output_chars must be at least 0.")
    if max_output_chars > 20_000:
        raise ValueError("max_output_chars must be at most 20000.")


def build_session_audit_report_from_parts(
    run_id: str,
    summary: SessionSummary,
    failures: list[dict[str, str | int]],
    command_entries: list[dict[str, Any]],
    files: list[dict[str, Any]],
    max_failures: int = 10,
    max_files: int = 20,
    max_commands: int = 10,
    max_checks: int = 50,
    max_text: int = 300,
) -> dict[str, Any]:
    pending_plan_items = session_pending_plan_items(summary)
    blockers = session_audit_blockers(summary, failures, files)
    plan_statuses = {item.status for item in summary.latest_plan}
    shown_failures = failures[-max_failures:]
    shown_commands = command_entries[-max_commands:]
    shown_files = files[:max_files]
    shown_processes = summary.active_background_processes[:max_failures]

    return {
        "session": run_id,
        "exists": True,
        "ok": not blockers,
        "ready": not blockers,
        "status": "ready" if not blockers else "blocked",
        "summary": {
            "sessionStatus": session_summary_status(summary),
            "events": summary.event_count,
            "malformedRows": summary.malformed_count,
            "iterations": summary.iterations,
            "toolCalls": len(summary.tool_calls),
            "approvals": {
                "requested": summary.approvals_requested,
                "approved": summary.approvals_approved,
                "denied": summary.approvals_denied,
            },
            "tokens": {
                "input": summary.input_tokens,
                "output": summary.output_tokens,
                "total": summary.total_tokens,
                "cacheCreation": summary.cache_creation_tokens,
                "cacheRead": summary.cache_read_tokens,
            },
            "task": summary.task,
            "completed": summary.completed,
            "failed": summary.failed,
            "blocked": summary.blocked,
            "modelErrors": summary.model_errors,
            "latestModelError": summary.latest_model_error,
        },
        "finalReview": {
            "seen": summary.final_review_seen,
            "ready": summary.final_review_ready,
            "blockingIssues": summary.final_review_blocking_issues,
            "warnings": summary.final_review_warnings,
            "files": summary.final_review_files,
            "changedFiles": summary.final_review_changed_files,
            "suggestedChecks": summary.final_review_suggested_checks,
            "message": summary.final_review_message,
            "failures": {
                "python": summary.final_review_python_failures,
                "config": summary.final_review_config_failures,
            },
        },
        "checkpoints": {
            "created": summary.checkpoints_created,
            "autoCreated": summary.auto_checkpoints_created,
            "latestId": summary.latest_checkpoint_id,
            "latestMessage": summary.latest_checkpoint_message,
            "restoreHint": CHECKPOINT_RESTORE_HINT if summary.latest_checkpoint_id else None,
        },
        "backgroundProcesses": {
            "started": summary.background_processes_started,
            "active": len(summary.active_background_processes),
            "shown": len(shown_processes),
            "truncated": len(summary.active_background_processes) > len(shown_processes),
            "processes": [
                {
                    "processId": process.process_id,
                    "pid": process.pid,
                    "cwd": compact(process.cwd, max_text),
                    "command": compact(process.command, max_text),
                    "lineNumber": process.line_number,
                }
                for process in shown_processes
            ],
        },
        "blockers": {
            "count": len(blockers),
            "items": [compact(blocker, max_text) for blocker in blockers],
        },
        "completion": {
            "ready": summary.completion_ready,
            "blockers": [compact(blocker, max_text) for blocker in summary.completion_blockers],
            "blockedCount": summary.completion_blocked_count,
            "latestBlockers": [compact(blocker, max_text) for blocker in summary.latest_completion_blockers],
            "latestPendingVerificationChecks": [
                compact(check, max_text)
                for check in summary.latest_completion_pending_verification_checks
            ],
            "latestFailedVerificationChecks": [
                compact(check, max_text)
                for check in summary.latest_completion_failed_verification_checks
            ],
            "latestFinalReviewBlockingIssues": [
                compact(issue, max_text)
                for issue in summary.latest_completion_final_review_issues
            ],
            "latestFinalReviewChangedFiles": [
                compact(path, max_text)
                for path in summary.latest_completion_final_review_changed_files
            ],
            "latestToolErrors": [
                compact(error, max_text)
                for error in summary.latest_completion_tool_errors
            ],
            "latestCheckpointFailures": [
                compact(failure, max_text)
                for failure in summary.latest_completion_checkpoint_failures
            ],
            "latestActiveBackgroundProcesses": [
                compact(process, max_text)
                for process in summary.latest_completion_active_background_processes
            ],
            "latestDeniedApprovals": [
                compact(approval, max_text)
                for approval in summary.latest_completion_denied_approvals
            ],
            "warnings": [compact(warning, max_text) for warning in summary.completion_warnings],
        },
        "verification": {
            "verified": limited_string_group(summary.verification_checks, max_checks, max_text, status="verified"),
            "pending": limited_string_group(summary.pending_verification_checks, max_checks, max_text, status="pending"),
            "failed": limited_string_group(summary.failed_verification_checks, max_checks, max_text, status="failed"),
        },
        "plan": {
            "items": len(summary.latest_plan),
            "inProgress": "in_progress" in plan_statuses,
            "pending": {
                "total": len(pending_plan_items),
                "shown": min(len(pending_plan_items), max_failures),
                "truncated": len(pending_plan_items) > max_failures,
                "items": [
                    {"status": item.status, "step": compact(item.step, max_text)}
                    for item in pending_plan_items[:max_failures]
                ],
            },
        },
        "failures": {
            "total": len(failures),
            "shown": len(shown_failures),
            "truncated": len(failures) > len(shown_failures),
            "items": [serialize_session_failure(failure, max_text) for failure in shown_failures],
        },
        "commands": {
            "total": len(command_entries),
            "shown": len(shown_commands),
            "truncated": len(command_entries) > len(shown_commands),
            "items": [serialize_session_command_entry(entry, max_text) for entry in shown_commands],
        },
        "files": {
            "total": len(files),
            "shown": len(shown_files),
            "truncated": len(files) > len(shown_files),
            "items": [
                {
                    "path": compact(str(file_entry.get("path", "unknown")), max_text),
                    "uses": file_entry.get("uses") if isinstance(file_entry.get("uses"), list) else [],
                }
                for file_entry in shown_files
            ],
        },
        "message": "Session is ready." if not blockers else f"Session has {len(blockers)} blocker(s).",
    }


def build_session_handoff_report_from_sections(
    run_id: str,
    audit: dict[str, Any],
    sections: dict[str, str],
    max_failures: int,
    max_files: int,
    max_commands: int,
    max_checks: int,
    max_output_chars: int,
    max_text: int,
) -> dict[str, Any]:
    ready = audit.get("ready") is True
    return {
        "session": run_id,
        "exists": True,
        "ok": ready,
        "ready": ready,
        "status": audit.get("status", "ready" if ready else "blocked"),
        "audit": audit,
        "sections": sections,
        "limits": {
            "maxFailures": max_failures,
            "maxFiles": max_files,
            "maxCommands": max_commands,
            "maxChecks": max_checks,
            "maxOutputChars": max_output_chars,
            "maxText": max_text,
        },
        "message": "Session handoff is ready." if ready else "Session handoff has blocker(s).",
    }


def serialize_session_failure(failure: dict[str, str | int], max_text: int) -> dict[str, Any]:
    item: dict[str, Any] = {
        "lineNumber": failure.get("line_number"),
        "type": failure.get("type"),
        "name": failure.get("name"),
        "message": compact(str(failure.get("message", "")), max_text),
    }
    detail = failure.get("detail")
    if isinstance(detail, str) and detail.strip():
        item["detail"] = compact(detail, max_text)
    return item


def serialize_session_command_entry(entry: dict[str, Any], max_text: int) -> dict[str, Any]:
    result = entry["result"]
    command = result.get("command")
    cwd = result.get("cwd")
    exit_code = result.get("exit_code")
    duration_ms = result.get("duration_ms")
    return {
        "lineNumber": entry.get("line_number"),
        "kind": entry.get("kind"),
        "index": entry.get("index"),
        "command": compact(command, max_text) if isinstance(command, str) else None,
        "cwd": cwd if isinstance(cwd, str) and cwd else ".",
        "exitCode": exit_code if isinstance(exit_code, int) else None,
        "timedOut": result.get("timed_out") is True,
        "durationMs": duration_ms if isinstance(duration_ms, int) else None,
    }


def failed_checkpoint_create_count(failures: list[dict[str, str | int]]) -> int:
    return sum(
        1
        for failure in failures
        if failure.get("type") == "tool_result" and failure.get("name") == "checkpoint_create"
    )


def format_session_audit_from_parts(
    run_id: str,
    summary: SessionSummary,
    failures: list[dict[str, str | int]],
    command_entries: list[dict[str, Any]],
    files: list[dict[str, Any]],
    max_failures: int = 10,
    max_files: int = 20,
    max_commands: int = 10,
    max_checks: int = 50,
    max_text: int = 300,
) -> str:
    plan_statuses = {item.status for item in summary.latest_plan}
    pending_plan_items = session_pending_plan_items(summary)
    blockers = session_audit_blockers(summary, failures, files)

    status = "ready" if not blockers else "blocked"
    lines = [
        "Session audit:",
        f"  session: {run_id}",
        f"  ready: {'yes' if not blockers else 'no'}",
        f"  status: {status}",
        f"  events: {summary.event_count}",
        f"  iterations: {summary.iterations}",
        f"  tools: {len(summary.tool_calls)}",
        (
            "  approvals: "
            f"{summary.approvals_requested} requested, "
            f"{summary.approvals_approved} approved, "
            f"{summary.approvals_denied} denied"
        ),
    ]
    if summary.task:
        lines.append(f"  task: {compact(summary.task, max_text)}")
    if summary.checkpoints_created:
        checkpoint_line = (
            "  checkpoints: "
            f"created={summary.checkpoints_created}, "
            f"auto={summary.auto_checkpoints_created}"
        )
        if summary.latest_checkpoint_id:
            checkpoint_line += f", latest={compact(summary.latest_checkpoint_id, max_text)}"
        lines.append(checkpoint_line)
        if summary.latest_checkpoint_id:
            lines.append(f"  restoreHint: {CHECKPOINT_RESTORE_HINT}")
    if summary.final_review_seen:
        ready = "yes" if summary.final_review_ready is True else "no" if summary.final_review_ready is False else "unknown"
        lines.append(
            "  finalReview: "
            f"ready={ready}, "
            f"blocking={summary.final_review_blocking_issues}, "
            f"warnings={summary.final_review_warnings}, "
            f"files={summary.final_review_files}, "
            f"suggestedChecks={summary.final_review_suggested_checks}"
        )
        if summary.final_review_changed_files:
            lines.append("  finalReviewChangedFiles:")
            lines.extend(f"    - {compact(path, max_text)}" for path in summary.final_review_changed_files)
        lines.extend(format_final_review_failure_lines(summary, indent="  ", max_text=max_text))
    else:
        lines.append("  finalReview: not run")

    lines.append("  backgroundProcesses:")
    lines.append(f"    started: {summary.background_processes_started}")
    lines.append(f"    active: {len(summary.active_background_processes)}")
    if summary.active_background_processes:
        for process in summary.active_background_processes[:max_failures]:
            pid = process.pid if process.pid is not None else "unknown"
            lines.append(
                "    - "
                f"#{process.line_number} {compact(process.process_id, max_text)}: "
                f"pid={pid}, cwd={compact(process.cwd, max_text)}, command={compact(process.command, max_text)}"
            )

    lines.append("  blockers:")
    if blockers:
        lines.extend(f"    - {compact(blocker, max_text)}" for blocker in blockers)
    else:
        lines.append("    - none")

    if summary.completion_ready is not None:
        lines.append(f"  completionReady: {'yes' if summary.completion_ready else 'no'}")
    if summary.completion_blockers:
        lines.append("  completionBlockers:")
        lines.extend(f"    - {compact(blocker, max_text)}" for blocker in summary.completion_blockers)
    if summary.completion_blocked_count:
        lines.append(f"  completionBlocked: {summary.completion_blocked_count}")
        if summary.latest_completion_blockers:
            lines.append("  latestCompletionBlockers:")
            lines.extend(f"    - {compact(blocker, max_text)}" for blocker in summary.latest_completion_blockers)
        lines.extend(format_latest_completion_detail_lines(summary, indent="  ", max_text=max_text))

    if summary.completion_warnings:
        lines.append("  completionWarnings:")
        lines.extend(f"    - {compact(warning, max_text)}" for warning in summary.completion_warnings)

    lines.append("  verification:")
    lines.append(f"    verified: {len(summary.verification_checks)}")
    lines.append(f"    pending: {len(summary.pending_verification_checks)}")
    lines.append(f"    failed: {len(summary.failed_verification_checks)}")
    if summary.verification_checks:
        lines.append("    verifiedChecks:")
        lines.extend(f"      - {compact(check, max_text)}" for check in summary.verification_checks[:max_checks])
        omitted = len(summary.verification_checks) - max_checks
        if omitted > 0:
            lines.append(f"    verifiedChecksOmitted: {omitted}")
    if summary.pending_verification_checks:
        lines.append("    pendingChecks:")
        lines.extend(f"      - {compact(check, max_text)}" for check in summary.pending_verification_checks[:max_checks])
        omitted = len(summary.pending_verification_checks) - max_checks
        if omitted > 0:
            lines.append(f"    pendingChecksOmitted: {omitted}")
    if summary.failed_verification_checks:
        lines.append("    failedChecks:")
        lines.extend(f"      - {compact(check, max_text)}" for check in summary.failed_verification_checks[:max_checks])
        omitted = len(summary.failed_verification_checks) - max_checks
        if omitted > 0:
            lines.append(f"    failedChecksOmitted: {omitted}")

    lines.append("  plan:")
    if summary.latest_plan:
        lines.append(f"    items: {len(summary.latest_plan)}")
        lines.append(f"    inProgress: {'yes' if 'in_progress' in plan_statuses else 'no'}")
        for item in pending_plan_items[:max_failures]:
            lines.append(f"    - {item.status}: {compact(item.step, max_text)}")
    else:
        lines.append("    items: 0")

    shown_failures = failures[-max_failures:]
    lines.append("  failures:")
    lines.append(f"    count: {len(failures)}")
    lines.append(f"    shown: {len(shown_failures)}/{len(failures)}")
    if shown_failures:
        for failure in shown_failures:
            lines.append(
                "    - "
                f"#{failure['line_number']} {failure['type']} {failure['name']}: "
                f"{compact(str(failure['message']), max_text)}"
            )
            detail = failure.get("detail")
            if isinstance(detail, str) and detail.strip():
                lines.append(f"      detail: {compact(detail, max_text)}")
    else:
        lines.append("    - none")

    shown_commands = command_entries[-max_commands:]
    lines.append("  commands:")
    lines.append(f"    count: {len(command_entries)}")
    lines.append(f"    shown: {len(shown_commands)}/{len(command_entries)}")
    if shown_commands:
        for entry in shown_commands:
            result = entry["result"]
            command = result.get("command")
            exit_code = result.get("exit_code")
            timed_out = result.get("timed_out")
            cwd = result.get("cwd")
            duration_ms = result.get("duration_ms")
            duration_text = f"durationMs={duration_ms}, " if isinstance(duration_ms, int) else ""
            lines.append(
                "    - "
                f"#{entry['line_number']} {entry['kind']}[{entry['index']}]: "
                f"exit={exit_code if isinstance(exit_code, int) else 'unknown'}, "
                f"timedOut={'yes' if timed_out is True else 'no'}, "
                f"{duration_text}"
                f"cwd={cwd if isinstance(cwd, str) and cwd else '.'}, "
                f"command={compact(command, max_text) if isinstance(command, str) else 'unknown'}"
            )
    else:
        lines.append("    - none")

    shown_files = files[:max_files]
    lines.append("  files:")
    lines.append(f"    count: {len(files)}")
    lines.append(f"    shown: {len(shown_files)}/{len(files)}")
    if shown_files:
        for file_entry in shown_files:
            lines.append(
                "    - "
                f"{compact(str(file_entry.get('path', 'unknown')), max_text)} "
                f"uses={','.join(file_entry.get('uses', [])) if isinstance(file_entry.get('uses'), list) else 'unknown'}"
            )
    else:
        lines.append("    - none")
    return "\n".join(lines)
