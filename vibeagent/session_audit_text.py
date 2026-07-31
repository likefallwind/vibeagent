from __future__ import annotations

from typing import Any

from .session_audit_readiness import session_audit_blockers, session_pending_plan_items
from .session_audit_text_sections import (
    append_checkpoint_lines,
    append_completion_lines,
    append_final_review_lines,
)
from .session_types import SessionSummary
from .session_utils import compact


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
    append_final_review_lines(lines, summary, max_text=max_text, include_counts=False, changed_file_limit=20)
    append_checkpoint_lines(lines, summary, max_text=max_text)
    if summary.background_processes_started or summary.active_background_processes:
        lines.append(
            "  backgroundProcesses: "
            f"started={summary.background_processes_started}, "
            f"active={len(summary.active_background_processes)}"
        )
    if summary.subagents_started or summary.subagent_context_compacted_count:
        lines.append(
            "  subagents: "
            f"started={summary.subagents_started}, "
            f"completed={summary.subagents_completed}, "
            f"failed={summary.subagents_failed}, "
            f"toolCalls={len(summary.subagent_tool_calls)}, "
            f"contextCompacted={summary.subagent_context_compacted_count}"
        )
        if summary.latest_subagent_failures:
            lines.append("  latestSubagentFailures:")
            lines.extend(f"    - {compact(failure, max_text)}" for failure in summary.latest_subagent_failures[:20])
    lines.append("  blockers:")
    if blockers:
        lines.extend(f"    - {compact(blocker, max_text)}" for blocker in blockers)
    else:
        lines.append("    - none")
    append_completion_lines(lines, summary, max_text=max_text)
    return "\n".join(lines)


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
    append_checkpoint_lines(lines, summary, max_text=max_text)
    append_final_review_lines(lines, summary, max_text=max_text, include_counts=True)

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

    lines.append("  subagents:")
    lines.append(f"    started: {summary.subagents_started}")
    lines.append(f"    completed: {summary.subagents_completed}")
    lines.append(f"    failed: {summary.subagents_failed}")
    lines.append(f"    toolCalls: {len(summary.subagent_tool_calls)}")
    lines.append(f"    contextCompacted: {summary.subagent_context_compacted_count}")
    if summary.latest_subagent_failures:
        lines.append("    latestFailures:")
        lines.extend(f"      - {compact(failure, max_text)}" for failure in summary.latest_subagent_failures[:20])

    lines.append("  blockers:")
    if blockers:
        lines.extend(f"    - {compact(blocker, max_text)}" for blocker in blockers)
    else:
        lines.append("    - none")

    append_completion_lines(lines, summary, max_text=max_text)

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
            line = f"    - {item.status}: {compact(item.step, max_text)}"
            if item.active_form:
                line += f" (activeForm: {compact(item.active_form, max_text)})"
            lines.append(line)
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
