from __future__ import annotations

from typing import Any

from .session_summary_reports import (
    CHECKPOINT_RESTORE_HINT,
    format_final_review_failure_lines,
    format_latest_completion_detail_lines,
    session_summary_status,
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
    if summary.malformed_count:
        blockers.append(f"{summary.malformed_count} malformed session row(s)")
    if summary.approvals_denied:
        blockers.append(f"{summary.approvals_denied} denied approval(s)")
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
            "verified": limited_string_group(summary.verification_checks, max_checks, max_text),
            "pending": limited_string_group(summary.pending_verification_checks, max_checks, max_text),
            "failed": limited_string_group(summary.failed_verification_checks, max_checks, max_text),
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


def format_session_verification_report_text(report: dict[str, object]) -> str:
    session = str(report.get("session") or "")
    if not bool(report.get("exists")):
        fallback = f"Session not found: {session}" if session else "No sessions found."
        return str(report.get("message") or fallback)

    lines = ["Session verification:"]
    truncated = bool(report.get("truncated"))
    for key, label in (("verified", "verified"), ("pending", "pendingChecks"), ("failed", "failedChecks")):
        group = report.get(key) if isinstance(report.get(key), dict) else {}
        total = int(group.get("total", 0) or 0)
        shown = int(group.get("shown", 0) or 0)
        items = [item for item in group.get("items", []) if isinstance(item, str)] if isinstance(group.get("items"), list) else []
        if items:
            lines.append(f"  {label}: {shown}/{total}")
            lines.extend(f"    - {item}" for item in items)
        else:
            lines.append(f"  {label}: none")
        truncated = truncated or bool(group.get("truncated"))
    lines.append(f"  truncated: {'yes' if truncated else 'no'}")
    return "\n".join(lines)


def format_session_audit_report_text(report: dict[str, object]) -> str:
    session = str(report.get("session") or "")
    if not bool(report.get("exists")):
        fallback = f"Session not found: {session}" if session else "No sessions found."
        return str(report.get("message") or fallback)

    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    approvals = summary.get("approvals") if isinstance(summary.get("approvals"), dict) else {}
    checkpoints = report.get("checkpoints") if isinstance(report.get("checkpoints"), dict) else {}
    final_review = report.get("finalReview") if isinstance(report.get("finalReview"), dict) else {}
    background = report.get("backgroundProcesses") if isinstance(report.get("backgroundProcesses"), dict) else {}
    blockers = report.get("blockers") if isinstance(report.get("blockers"), dict) else {}
    completion = report.get("completion") if isinstance(report.get("completion"), dict) else {}
    verification = report.get("verification") if isinstance(report.get("verification"), dict) else {}
    plan = report.get("plan") if isinstance(report.get("plan"), dict) else {}
    failures = report.get("failures") if isinstance(report.get("failures"), dict) else {}
    commands = report.get("commands") if isinstance(report.get("commands"), dict) else {}
    files = report.get("files") if isinstance(report.get("files"), dict) else {}

    lines = [
        "Session audit:",
        f"  session: {session}",
        f"  ready: {'yes' if bool(report.get('ready')) else 'no'}",
        f"  status: {report.get('status') or ''}",
        f"  events: {int(summary.get('events', 0) or 0)}",
        f"  iterations: {int(summary.get('iterations', 0) or 0)}",
        f"  tools: {int(summary.get('toolCalls', 0) or 0)}",
        (
            "  approvals: "
            f"{int(approvals.get('requested', 0) or 0)} requested, "
            f"{int(approvals.get('approved', 0) or 0)} approved, "
            f"{int(approvals.get('denied', 0) or 0)} denied"
        ),
    ]
    if summary.get("task"):
        lines.append(f"  task: {summary.get('task')}")
    if int(checkpoints.get("created", 0) or 0) > 0:
        checkpoint_line = (
            "  checkpoints: "
            f"created={int(checkpoints.get('created', 0) or 0)}, "
            f"auto={int(checkpoints.get('autoCreated', 0) or 0)}"
        )
        if checkpoints.get("latestId"):
            checkpoint_line += f", latest={checkpoints.get('latestId')}"
        lines.append(checkpoint_line)
        if checkpoints.get("latestId"):
            lines.append(f"  restoreHint: {CHECKPOINT_RESTORE_HINT}")
    if final_review.get("seen"):
        final_ready = final_review.get("ready")
        ready = "yes" if final_ready is True else "no" if final_ready is False else "unknown"
        lines.append(
            "  finalReview: "
            f"ready={ready}, "
            f"blocking={int(final_review.get('blockingIssues', 0) or 0)}, "
            f"warnings={int(final_review.get('warnings', 0) or 0)}, "
            f"files={int(final_review.get('files', 0) or 0)}, "
            f"suggestedChecks={int(final_review.get('suggestedChecks', 0) or 0)}"
        )
        lines.extend(_format_final_review_changed_file_report_lines(final_review, indent="  ", max_text=300))
    else:
        lines.append("  finalReview: not run")

    lines.append("  backgroundProcesses:")
    lines.append(f"    started: {int(background.get('started', 0) or 0)}")
    lines.append(f"    active: {int(background.get('active', 0) or 0)}")
    background_items = [item for item in background.get("processes", []) if isinstance(item, dict)] if isinstance(background.get("processes"), list) else []
    for process in background_items:
        lines.append(
            "    - "
            f"#{process.get('lineNumber', '')} {process.get('processId') or ''}: "
            f"pid={process.get('pid') if process.get('pid') is not None else 'unknown'}, "
            f"cwd={process.get('cwd') or ''}, "
            f"command={process.get('command') or ''}"
        )

    lines.append("  blockers:")
    blocker_items = [item for item in blockers.get("items", []) if isinstance(item, str)] if isinstance(blockers.get("items"), list) else []
    if blocker_items:
        lines.extend(f"    - {blocker}" for blocker in blocker_items)
    else:
        lines.append("    - none")

    if completion.get("ready") is not None:
        lines.append(f"  completionReady: {'yes' if completion.get('ready') else 'no'}")
    _append_audit_string_list(lines, "  completionBlockers:", completion.get("blockers"))
    if int(completion.get("blockedCount", 0) or 0) > 0:
        lines.append(f"  completionBlocked: {int(completion.get('blockedCount', 0) or 0)}")
        _append_audit_string_list(lines, "  latestCompletionBlockers:", completion.get("latestBlockers"))
    _append_audit_string_list(lines, "  latestPendingVerificationChecks:", completion.get("latestPendingVerificationChecks"))
    _append_audit_string_list(lines, "  latestFailedVerificationChecks:", completion.get("latestFailedVerificationChecks"))
    _append_audit_string_list(lines, "  latestFinalReviewBlockingIssues:", completion.get("latestFinalReviewBlockingIssues"))
    _append_audit_string_list(lines, "  latestFinalReviewChangedFiles:", completion.get("latestFinalReviewChangedFiles"))
    _append_audit_string_list(lines, "  latestToolErrors:", completion.get("latestToolErrors"))
    _append_audit_string_list(lines, "  latestCheckpointFailures:", completion.get("latestCheckpointFailures"))
    _append_audit_string_list(lines, "  latestActiveBackgroundProcesses:", completion.get("latestActiveBackgroundProcesses"))
    _append_audit_string_list(lines, "  latestDeniedApprovals:", completion.get("latestDeniedApprovals"))
    _append_audit_string_list(lines, "  completionWarnings:", completion.get("warnings"))

    lines.append("  verification:")
    _append_audit_verification_group(lines, "verified", "verifiedChecks", "verifiedChecksOmitted", verification.get("verified"))
    _append_audit_verification_group(lines, "pending", "pendingChecks", "pendingChecksOmitted", verification.get("pending"))
    _append_audit_verification_group(lines, "failed", "failedChecks", "failedChecksOmitted", verification.get("failed"))

    lines.append("  plan:")
    plan_items = int(plan.get("items", 0) or 0)
    lines.append(f"    items: {plan_items}")
    if plan_items > 0:
        lines.append(f"    inProgress: {'yes' if bool(plan.get('inProgress')) else 'no'}")
        pending = plan.get("pending") if isinstance(plan.get("pending"), dict) else {}
        pending_items = [item for item in pending.get("items", []) if isinstance(item, dict)] if isinstance(pending.get("items"), list) else []
        for item in pending_items:
            lines.append(f"    - {item.get('status') or ''}: {item.get('step') or ''}")

    _append_audit_failures(lines, failures)
    _append_audit_commands(lines, commands)
    _append_audit_files(lines, files)
    return "\n".join(lines)


def format_session_handoff_report_text(report: dict[str, object]) -> str:
    session = str(report.get("session") or "")
    if not bool(report.get("exists")):
        fallback = f"Session not found: {session}" if session else "No sessions found."
        return str(report.get("message") or fallback)

    lines = ["Session handoff:", f"  session: {session}"]
    sections = report.get("sections") if isinstance(report.get("sections"), dict) else {}
    for title in ("summary", "readiness", "plan", "verification", "failures", "files", "commands"):
        section_text = sections.get(title)
        if not isinstance(section_text, str):
            continue
        lines.append(f"  {title}:")
        lines.extend(f"    {line}" for line in section_text.splitlines())
    return "\n".join(lines)


def _format_final_review_changed_file_report_lines(report: dict[str, object], indent: str, max_text: int) -> list[str]:
    changed_files = report.get("changedFiles") if isinstance(report.get("changedFiles"), list) else []
    labels = [item for item in changed_files if isinstance(item, str) and item.strip()]
    if not labels:
        return []
    lines = [f"{indent}finalReviewChangedFiles:"]
    lines.extend(f"{indent}  - {compact(item, max_text)}" for item in labels[:20])
    if len(labels) > 20:
        lines.append(f"{indent}  - ... {len(labels) - 20} more")
    return lines


def _append_audit_string_list(lines: list[str], label: str, values: object) -> None:
    items = [item for item in values if isinstance(item, str)] if isinstance(values, list) else []
    if not items:
        return
    lines.append(label)
    lines.extend(f"    - {item}" for item in items)


def _append_audit_verification_group(
    lines: list[str],
    count_label: str,
    list_label: str,
    omitted_label: str,
    group: object,
) -> None:
    data = group if isinstance(group, dict) else {}
    total = int(data.get("total", 0) or 0)
    shown = int(data.get("shown", 0) or 0)
    items = [item for item in data.get("items", []) if isinstance(item, str)] if isinstance(data.get("items"), list) else []
    lines.append(f"    {count_label}: {total}")
    if not items:
        return
    lines.append(f"    {list_label}:")
    lines.extend(f"      - {item}" for item in items)
    omitted = max(total - shown, 0)
    if omitted > 0:
        lines.append(f"    {omitted_label}: {omitted}")


def _append_audit_failures(lines: list[str], failures: dict[str, object]) -> None:
    total = int(failures.get("total", 0) or 0)
    shown = int(failures.get("shown", 0) or 0)
    items = [item for item in failures.get("items", []) if isinstance(item, dict)] if isinstance(failures.get("items"), list) else []
    lines.append("  failures:")
    lines.append(f"    count: {total}")
    lines.append(f"    shown: {shown}/{total}")
    if not items:
        lines.append("    - none")
        return
    for failure in items:
        lines.append(
            "    - "
            f"#{failure.get('lineNumber', '')} {failure.get('type') or ''} {failure.get('name') or ''}: "
            f"{failure.get('message') or ''}"
        )
        if failure.get("detail"):
            lines.append(f"      detail: {failure.get('detail')}")


def _append_audit_commands(lines: list[str], commands: dict[str, object]) -> None:
    total = int(commands.get("total", 0) or 0)
    shown = int(commands.get("shown", 0) or 0)
    items = [item for item in commands.get("items", []) if isinstance(item, dict)] if isinstance(commands.get("items"), list) else []
    lines.append("  commands:")
    lines.append(f"    count: {total}")
    lines.append(f"    shown: {shown}/{total}")
    if not items:
        lines.append("    - none")
        return
    for command in items:
        exit_code = command.get("exitCode")
        lines.append(
            "    - "
            f"#{command.get('lineNumber', '')} {command.get('kind') or ''}[{command.get('index')}]: "
            f"exit={exit_code if isinstance(exit_code, int) else 'unknown'}, "
            f"timedOut={'yes' if command.get('timedOut') is True else 'no'}, "
            f"cwd={command.get('cwd') or '.'}, "
            f"command={command.get('command') or 'unknown'}"
        )


def _append_audit_files(lines: list[str], files: dict[str, object]) -> None:
    total = int(files.get("total", 0) or 0)
    shown = int(files.get("shown", 0) or 0)
    items = [item for item in files.get("items", []) if isinstance(item, dict)] if isinstance(files.get("items"), list) else []
    lines.append("  files:")
    lines.append(f"    count: {total}")
    lines.append(f"    shown: {shown}/{total}")
    if not items:
        lines.append("    - none")
        return
    for item in items:
        uses = ",".join(str(use) for use in item.get("uses", []) if isinstance(use, str)) if isinstance(item.get("uses"), list) else "unknown"
        lines.append(f"    - {item.get('path') or 'unknown'} uses={uses}")


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
    return {
        "lineNumber": entry.get("line_number"),
        "kind": entry.get("kind"),
        "index": entry.get("index"),
        "command": compact(command, max_text) if isinstance(command, str) else None,
        "cwd": cwd if isinstance(cwd, str) and cwd else ".",
        "exitCode": exit_code if isinstance(exit_code, int) else None,
        "timedOut": result.get("timed_out") is True,
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
            lines.append(
                "    - "
                f"#{entry['line_number']} {entry['kind']}[{entry['index']}]: "
                f"exit={exit_code if isinstance(exit_code, int) else 'unknown'}, "
                f"timedOut={'yes' if timed_out is True else 'no'}, "
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
