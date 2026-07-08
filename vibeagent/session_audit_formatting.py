from __future__ import annotations

from .session_summary_reports import CHECKPOINT_RESTORE_HINT
from .session_utils import compact


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
        final_review_line = (
            "  finalReview: "
            f"ready={ready}, "
            f"blocking={int(final_review.get('blockingIssues', 0) or 0)}, "
            f"warnings={int(final_review.get('warnings', 0) or 0)}, "
            f"files={int(final_review.get('files', 0) or 0)}, "
            f"suggestedChecks={int(final_review.get('suggestedChecks', 0) or 0)}"
        )
        if final_review.get("resolvedByCompletion") is True:
            final_review_line += ", resolvedByCompletion=yes"
        lines.append(final_review_line)
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
        duration_ms = command.get("durationMs")
        duration_text = f"durationMs={duration_ms}, " if isinstance(duration_ms, int) else ""
        lines.append(
            "    - "
            f"#{command.get('lineNumber', '')} {command.get('kind') or ''}[{command.get('index')}]: "
            f"exit={exit_code if isinstance(exit_code, int) else 'unknown'}, "
            f"timedOut={'yes' if command.get('timedOut') is True else 'no'}, "
            f"{duration_text}"
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
