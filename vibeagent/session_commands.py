from __future__ import annotations

from pathlib import Path

from .output_serialization import serialize_output_context_result, serialize_output_diagnostic
from .session import build_session_audit_report, build_session_commands_report, build_session_failures_report, build_session_files_report, build_session_handoff_report, build_session_resume_context, build_session_verification_report, get_last_session_id
from .session_accounting_commands import (
    format_cost_report_text as _format_cost_report_text,
    format_sessions_report_text as _format_sessions_report_text,
    format_usage_report_text as _format_usage_report_text,
    get_cost_report as _get_cost_report,
    get_sessions_report as _get_sessions_report,
    get_usage_report as _get_usage_report,
)
from .session_summary_commands import (
    _format_final_review_changed_file_lines,
    format_session_plan_report_text as _format_session_plan_report_text,
    format_session_search_report_text as _format_session_search_report_text,
    format_session_summary_report_text as _format_session_summary_report_text,
    format_session_transcript_report_text as _format_session_transcript_report_text,
    get_last_session_report as _get_last_session_report,
    get_plan_report as _get_plan_report,
    get_session_report as _get_session_report,
    get_session_search_report as _get_session_search_report,
    get_transcript_report as _get_transcript_report,
)
from .session_output_commands import (
    format_session_output_contexts_report_text,
    format_session_output_diagnostics_report_text,
    get_session_output_contexts_observation,
    get_session_output_contexts_report,
    get_session_output_contexts_text,
    get_session_output_diagnostics_observation,
    get_session_output_diagnostics_report,
    get_session_output_diagnostics_text,
)


def get_sessions_text(project_root: str | Path = ".") -> str:
    return format_sessions_report_text(get_sessions_report(project_root))


def get_sessions_report(project_root: str | Path = ".") -> dict[str, object]:
    return _get_sessions_report(project_root)


def format_sessions_report_text(report: dict[str, object]) -> str:
    return _format_sessions_report_text(report)


def get_usage_text(project_root: str | Path = ".") -> str:
    return format_usage_report_text(get_usage_report(project_root))


def get_usage_report(project_root: str | Path = ".") -> dict[str, object]:
    return _get_usage_report(project_root)


def format_usage_report_text(report: dict[str, object]) -> str:
    return _format_usage_report_text(report)


def get_cost_text(project_root: str | Path = ".", env: dict[str, str | None] | None = None) -> str:
    return format_cost_report_text(get_cost_report(project_root, env))


def get_cost_report(project_root: str | Path = ".", env: dict[str, str | None] | None = None) -> dict[str, object]:
    return _get_cost_report(project_root, env)


def format_cost_report_text(report: dict[str, object]) -> str:
    return _format_cost_report_text(report)


def get_session_text(run_id: str | None, project_root: str | Path = ".") -> str:
    return format_session_summary_report_text(get_session_report(run_id, project_root))


def get_session_report(run_id: str | None, project_root: str | Path = ".") -> dict[str, object]:
    return _get_session_report(run_id, project_root)


def format_session_summary_report_text(report: dict[str, object]) -> str:
    return _format_session_summary_report_text(report)


def get_last_session_text(project_root: str | Path = ".") -> str:
    return format_session_summary_report_text(get_last_session_report(project_root))


def get_last_session_report(project_root: str | Path = ".") -> dict[str, object]:
    return _get_last_session_report(project_root)


def get_plan_text(project_root: str | Path = ".", run_id: str | None = None) -> str:
    return format_session_plan_report_text(get_plan_report(project_root, run_id))


def get_plan_report(project_root: str | Path = ".", run_id: str | None = None) -> dict[str, object]:
    return _get_plan_report(project_root, run_id)


def format_session_plan_report_text(report: dict[str, object]) -> str:
    return _format_session_plan_report_text(report)


def get_transcript_text(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_events: int = 80,
    max_text: int = 500,
) -> str:
    return format_session_transcript_report_text(
        get_transcript_report(project_root, run_id, max_events=max_events, max_text=max_text)
    )


def get_transcript_report(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_events: int = 80,
    max_text: int = 500,
) -> dict[str, object]:
    return _get_transcript_report(project_root, run_id, max_events=max_events, max_text=max_text)


def format_session_transcript_report_text(report: dict[str, object]) -> str:
    return _format_session_transcript_report_text(report)


def get_session_search_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    run_id: str | None = None,
    max_matches: int = 20,
    max_text: int = 500,
    case_sensitive: bool = False,
) -> str:
    return format_session_search_report_text(
        get_session_search_report(
            project_root,
            argument,
            run_id,
            max_matches=max_matches,
            max_text=max_text,
            case_sensitive=case_sensitive,
        )
    )


def get_session_search_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    run_id: str | None = None,
    max_matches: int = 20,
    max_text: int = 500,
    case_sensitive: bool = False,
) -> dict[str, object]:
    return _get_session_search_report(
        project_root,
        argument,
        run_id,
        max_matches=max_matches,
        max_text=max_text,
        case_sensitive=case_sensitive,
    )


def format_session_search_report_text(report: dict[str, object]) -> str:
    return _format_session_search_report_text(report)


def get_session_commands_text(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_commands: int = 20,
    max_output_chars: int = 2_000,
) -> str:
    return format_session_commands_report_text(
        get_session_commands_report(
            project_root,
            run_id,
            max_commands=max_commands,
            max_output_chars=max_output_chars,
        )
    )


def get_session_commands_report(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_commands: int = 20,
    max_output_chars: int = 2_000,
) -> dict[str, object]:
    selected = run_id or get_last_session_id(project_root)
    if not selected:
        return {
            "session": None,
            "exists": False,
            "ok": False,
            "status": "missing",
            "message": "No sessions found.",
        }
    try:
        return build_session_commands_report(
            project_root,
            selected,
            max_commands=max_commands,
            max_output_chars=max_output_chars,
        )
    except ValueError as error:
        return {
            "session": selected,
            "exists": False,
            "ok": False,
            "status": "invalid",
            "message": str(error),
        }


def format_session_commands_report_text(report: dict[str, object]) -> str:
    session = str(report.get("session") or "")
    if not bool(report.get("exists")):
        fallback = f"Session not found: {session}" if session else "No sessions found."
        return str(report.get("message") or fallback)

    commands = report.get("commands") if isinstance(report.get("commands"), dict) else {}
    total = int(commands.get("total", 0) or 0)
    shown = int(commands.get("shown", 0) or 0)
    omitted = int(commands.get("omitted", 0) or 0)
    lines = [
        "Command results:",
        f"  session: {session}",
        f"  commands: {total}",
        f"  shown: {shown}/{total}",
        "  entries:",
    ]
    if omitted > 0:
        lines.append(f"    - [{omitted} older command result(s) omitted]")
    items = [item for item in commands.get("items", []) if isinstance(item, dict)] if isinstance(commands.get("items"), list) else []
    if not items:
        lines.append("    - none")
        return "\n".join(lines)
    for item in items:
        parts = [
            f"exit={item.get('exitCode') if isinstance(item.get('exitCode'), int) else 'unknown'}",
            f"timedOut={'yes' if bool(item.get('timedOut')) else 'no'}",
        ]
        if item.get("signal"):
            parts.append(f"signal={item.get('signal')}")
        if item.get("cwd"):
            parts.append(f"cwd={item.get('cwd')}")
        line_number = item.get("lineNumber") if item.get("lineNumber") is not None else "?"
        kind = item.get("kind") or "command"
        index = item.get("index") if item.get("index") is not None else "?"
        lines.append(f"    - #{line_number} {kind}[{index}]: " + ", ".join(parts))
        lines.append(f"      command: {item.get('command') or 'unknown'}")
        for label, text_key, truncated_key in (
            ("stdout", "stdout", "stdoutStoredTruncated"),
            ("stderr", "stderr", "stderrStoredTruncated"),
        ):
            suffix = " (stored truncated)" if bool(item.get(truncated_key)) else ""
            lines.append(f"      {label}{suffix}:")
            text = item.get(text_key) if isinstance(item.get(text_key), str) else ""
            if not text:
                lines.append("        (empty)")
            else:
                lines.extend(f"        {line}" for line in text.splitlines())
    return "\n".join(lines)


def get_session_files_text(project_root: str | Path = ".", run_id: str | None = None, max_files: int = 100) -> str:
    return format_session_files_report_text(get_session_files_report(project_root, run_id, max_files=max_files))


def get_session_files_report(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_files: int = 100,
) -> dict[str, object]:
    selected = run_id or get_last_session_id(project_root)
    if not selected:
        return {
            "session": None,
            "exists": False,
            "ok": False,
            "status": "missing",
            "message": "No sessions found.",
        }
    try:
        return build_session_files_report(project_root, selected, max_files=max_files)
    except ValueError as error:
        return {
            "session": selected,
            "exists": False,
            "ok": False,
            "status": "invalid",
            "message": str(error),
        }


def format_session_files_report_text(report: dict[str, object]) -> str:
    session = str(report.get("session") or "")
    if not bool(report.get("exists")):
        fallback = f"Session not found: {session}" if session else "No sessions found."
        return str(report.get("message") or fallback)

    files = report.get("files") if isinstance(report.get("files"), dict) else {}
    total = int(files.get("total", 0) or 0)
    shown = int(files.get("shown", 0) or 0)
    omitted = int(files.get("omitted", 0) or 0)
    lines = [
        "Session files:",
        f"  session: {session}",
        f"  files: {total}",
        f"  shown: {shown}/{total}",
        "  entries:",
    ]
    items = [item for item in files.get("items", []) if isinstance(item, dict)] if isinstance(files.get("items"), list) else []
    if not items:
        lines.append("    - none")
        return "\n".join(lines)
    for item in items:
        tools = ", ".join(str(tool) for tool in item.get("tools", []) if isinstance(tool, str)) if isinstance(item.get("tools"), list) else ""
        uses = ", ".join(str(use) for use in item.get("uses", []) if isinstance(use, str)) if isinstance(item.get("uses"), list) else ""
        line_values = [line for line in item.get("lines", []) if isinstance(line, int)] if isinstance(item.get("lines"), list) else []
        line_numbers = ", ".join(f"#{line}" for line in line_values[:8])
        if len(line_values) > 8:
            line_numbers += f", +{len(line_values) - 8} more"
        lines.append(f"    - {item.get('path') or ''}")
        lines.append(f"      uses: {uses}")
        lines.append(f"      tools: {tools}")
        lines.append(f"      count: {int(item.get('count', 0) or 0)}")
        lines.append(f"      lines: {line_numbers}")
    if omitted > 0:
        lines.append(f"    - [{omitted} file(s) omitted]")
    return "\n".join(lines)


def get_session_failures_text(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_failures: int = 50,
    max_text: int = 500,
) -> str:
    return format_session_failures_report_text(
        get_session_failures_report(project_root, run_id, max_failures=max_failures, max_text=max_text)
    )


def get_session_failures_report(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_failures: int = 50,
    max_text: int = 500,
) -> dict[str, object]:
    selected = run_id or get_last_session_id(project_root)
    if not selected:
        return {
            "session": None,
            "exists": False,
            "ok": False,
            "status": "missing",
            "message": "No sessions found.",
        }
    try:
        return build_session_failures_report(
            project_root,
            selected,
            max_failures=max_failures,
            max_text=max_text,
        )
    except ValueError as error:
        return {
            "session": selected,
            "exists": False,
            "ok": False,
            "status": "invalid",
            "message": str(error),
        }


def format_session_failures_report_text(report: dict[str, object]) -> str:
    session = str(report.get("session") or "")
    if not bool(report.get("exists")):
        fallback = f"Session not found: {session}" if session else "No sessions found."
        return str(report.get("message") or fallback)

    failures = report.get("failures") if isinstance(report.get("failures"), dict) else {}
    total = int(failures.get("total", 0) or 0)
    shown = int(failures.get("shown", 0) or 0)
    omitted = int(failures.get("omitted", 0) or 0)
    lines = [
        "Session failures:",
        f"  session: {session}",
        f"  failures: {total}",
        f"  shown: {shown}/{total}",
        "  entries:",
    ]
    if omitted > 0:
        lines.append(f"    - [{omitted} older failure(s) omitted]")
    items = [item for item in failures.get("items", []) if isinstance(item, dict)] if isinstance(failures.get("items"), list) else []
    if not items:
        lines.append("    - none")
        return "\n".join(lines)
    for failure in items:
        lines.append(f"    - #{failure.get('lineNumber', '')} {failure.get('type') or ''}: {failure.get('name') or ''}")
        if failure.get("message"):
            lines.append(f"      message: {failure.get('message')}")
        if failure.get("detail"):
            lines.append(f"      detail: {failure.get('detail')}")
    return "\n".join(lines)


def get_session_verification_text(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_checks: int = 50,
) -> str:
    return format_session_verification_report_text(
        get_session_verification_report(project_root, run_id, max_checks=max_checks)
    )


def get_session_verification_report(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_checks: int = 50,
    max_text: int = 160,
) -> dict[str, object]:
    selected = run_id or get_last_session_id(project_root)
    if not selected:
        return {
            "session": None,
            "exists": False,
            "ok": False,
            "ready": False,
            "status": "missing",
            "message": "No sessions found.",
        }
    try:
        return build_session_verification_report(
            project_root,
            selected,
            max_checks=max_checks,
            max_text=max_text,
        )
    except ValueError as error:
        return {
            "session": selected,
            "exists": False,
            "ok": False,
            "ready": False,
            "status": "invalid",
            "message": str(error),
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


def get_session_audit_report(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_failures: int = 10,
    max_files: int = 20,
    max_commands: int = 10,
    max_checks: int = 50,
    max_text: int = 300,
) -> dict[str, object]:
    selected = run_id or get_last_session_id(project_root)
    if not selected:
        return {
            "session": None,
            "exists": False,
            "ok": False,
            "ready": False,
            "status": "missing",
            "message": "No sessions found.",
        }
    try:
        return build_session_audit_report(
            project_root,
            selected,
            max_failures=max_failures,
            max_files=max_files,
            max_commands=max_commands,
            max_checks=max_checks,
            max_text=max_text,
        )
    except ValueError as error:
        return {
            "session": selected,
            "exists": False,
            "ok": False,
            "ready": False,
            "status": "invalid",
            "message": str(error),
        }


def get_session_audit_text(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_failures: int = 10,
    max_files: int = 20,
    max_commands: int = 10,
    max_checks: int = 50,
    max_text: int = 300,
) -> str:
    return format_session_audit_report_text(
        get_session_audit_report(
            project_root,
            run_id,
            max_failures=max_failures,
            max_files=max_files,
            max_commands=max_commands,
            max_checks=max_checks,
            max_text=max_text,
        )
    )


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
        lines.extend(_format_final_review_changed_file_lines(final_review, indent="  ", max_text=300))
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


def get_session_handoff_text(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_failures: int = 20,
    max_files: int = 50,
    max_commands: int = 10,
    max_checks: int = 50,
    max_output_chars: int = 1_000,
    max_text: int = 500,
) -> str:
    return format_session_handoff_report_text(
        get_session_handoff_report(
            project_root,
            run_id,
            max_failures=max_failures,
            max_files=max_files,
            max_commands=max_commands,
            max_checks=max_checks,
            max_output_chars=max_output_chars,
            max_text=max_text,
        )
    )


def get_session_handoff_report(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_failures: int = 20,
    max_files: int = 50,
    max_commands: int = 10,
    max_checks: int = 50,
    max_output_chars: int = 1_000,
    max_text: int = 500,
) -> dict[str, object]:
    selected = run_id or get_last_session_id(project_root)
    if not selected:
        return {
            "session": None,
            "exists": False,
            "ok": False,
            "ready": False,
            "status": "missing",
            "message": "No sessions found.",
        }
    try:
        return build_session_handoff_report(
            project_root,
            selected,
            max_failures=max_failures,
            max_files=max_files,
            max_commands=max_commands,
            max_checks=max_checks,
            max_output_chars=max_output_chars,
            max_text=max_text,
        )
    except ValueError as error:
        return {
            "session": selected,
            "exists": False,
            "ok": False,
            "ready": False,
            "status": "invalid",
            "message": str(error),
        }


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


def get_resume_context(
    run_id: str | None,
    project_root: str | Path = ".",
    max_failures: int = 20,
    max_files: int = 50,
    max_commands: int = 10,
    max_checks: int = 50,
    max_output_chars: int = 1_000,
    max_text: int = 500,
) -> tuple[str | None, str | None, str]:
    if run_id and run_id.strip().lower() in {"off", "clear", "none"}:
        return None, None, "Resume context cleared."
    selected = run_id or get_last_session_id(project_root)
    if not selected:
        return None, None, "No sessions found."
    try:
        context = build_session_resume_context(
            project_root,
            selected,
            max_failures=max_failures,
            max_files=max_files,
            max_commands=max_commands,
            max_checks=max_checks,
            max_output_chars=max_output_chars,
            max_text=max_text,
        )
    except ValueError as error:
        return None, None, str(error)
    return selected, context, f"Resume context loaded from session {selected}."


def get_compact_context(
    run_id: str | None,
    project_root: str | Path = ".",
    max_failures: int = 20,
    max_files: int = 50,
    max_commands: int = 10,
    max_checks: int = 50,
    max_output_chars: int = 1_000,
    max_text: int = 500,
) -> tuple[str | None, str | None, str]:
    selected = run_id or get_last_session_id(project_root)
    if not selected:
        return None, None, "No sessions found."
    try:
        context = build_session_resume_context(
            project_root,
            selected,
            max_failures=max_failures,
            max_files=max_files,
            max_commands=max_commands,
            max_checks=max_checks,
            max_output_chars=max_output_chars,
            max_text=max_text,
        )
    except ValueError as error:
        return None, None, str(error)
    return selected, context, f"Compacted context loaded from session {selected}."
