from __future__ import annotations

from .session import (
    build_session_handoff_report,
    format_session_audit,
    read_session_events,
    session_audit_blockers,
    session_failure_entries,
    session_file_entries,
    summarize_session,
)
from .session_action_helpers import select_session_run_id, session_file_references
from .session_audit_formatting import format_session_handoff_report_text
from .session_completion_detail_fields import completion_detail_kwargs_from_object
from .session_handoff_details import empty_session_handoff_details, extract_session_handoff_details
from .types import (
    SessionAuditAction,
    SessionAuditObservation,
    SessionAuditProcess,
    SessionHandoffAction,
    SessionHandoffObservation,
)
from .workspace import RunWorkspace


def execute_session_audit_action(workspace: RunWorkspace, action: SessionAuditAction) -> SessionAuditObservation:
    run_id = select_session_run_id(action.run_id, workspace.run_id)
    try:
        audit = format_session_audit(
            workspace.root,
            run_id,
            max_failures=action.max_failures,
            max_files=action.max_files,
            max_commands=action.max_commands,
            max_checks=action.max_checks,
            max_text=action.max_text,
        )
        ok = not audit.startswith("Session not found:")
        ready = "\n  ready: yes\n" in f"\n{audit}\n"
        message = f"Read session audit for {run_id}." if ok else audit
        blockers: list[str] = []
        background_processes_started = 0
        active_background_processes: list[SessionAuditProcess] = []
        file_references: list[dict[str, object]] = []
        file_count = 0
        shown_file_count = 0
        files_truncated = False
        completion_ready: bool | None = None
        completion_blockers: list[str] = []
        latest_completion_blockers: list[str] = []
        latest_subagent_failures: list[str] = []
        completion_detail_kwargs: dict[str, list[str]] = {}
        if ok:
            summary = summarize_session(workspace.root, run_id)
            events = read_session_events(workspace.root, run_id)
            failures = session_failure_entries(events, max_text=action.max_text)
            files = session_file_entries(events)
            blockers = session_audit_blockers(summary, failures, files)
            file_references, file_count, shown_file_count, files_truncated = session_file_references(
                files, action.max_files
            )
            background_processes_started = summary.background_processes_started
            completion_ready = summary.completion_ready
            completion_blockers = list(summary.completion_blockers)
            latest_completion_blockers = list(summary.latest_completion_blockers)
            latest_subagent_failures = list(summary.latest_subagent_failures)
            completion_detail_kwargs = completion_detail_kwargs_from_object(summary)
            active_background_processes = [
                SessionAuditProcess(
                    process_id=process.process_id,
                    pid=process.pid,
                    command=process.command,
                    cwd=process.cwd,
                    line_number=process.line_number,
                )
                for process in summary.active_background_processes
            ]
    except ValueError as error:
        audit = ""
        ok = False
        ready = False
        blockers = []
        background_processes_started = 0
        active_background_processes = []
        file_references = []
        file_count = 0
        shown_file_count = 0
        files_truncated = False
        completion_ready = None
        completion_blockers = []
        latest_completion_blockers = []
        latest_subagent_failures = []
        completion_detail_kwargs = {}
        message = str(error)
    return SessionAuditObservation(
        kind="session_audit",
        run_id=run_id,
        ok=ok,
        audit=audit,
        ready=ready,
        blockers=blockers,
        background_processes_started=background_processes_started,
        active_background_processes=active_background_processes,
        message=message,
        file_references=file_references,
        file_count=file_count,
        shown_file_count=shown_file_count,
        files_truncated=files_truncated,
        completion_ready=completion_ready,
        completion_blockers=completion_blockers,
        latest_completion_blockers=latest_completion_blockers,
        latest_subagent_failures=latest_subagent_failures,
        **completion_detail_kwargs,
    )


def execute_session_handoff_action(workspace: RunWorkspace, action: SessionHandoffAction) -> SessionHandoffObservation:
    run_id = select_session_run_id(action.run_id, workspace.run_id)
    try:
        report = build_session_handoff_report(
            workspace.root,
            run_id,
            max_failures=action.max_failures,
            max_files=action.max_files,
            max_commands=action.max_commands,
            max_checks=action.max_checks,
            max_output_chars=action.max_output_chars,
            max_text=action.max_text,
        )
        handoff = format_session_handoff_report_text(report)
        exists = report.get("exists") is True
        ok = exists
        details = extract_session_handoff_details(report)
        message = f"Read session handoff for {run_id}." if ok else handoff
    except ValueError as error:
        handoff = ""
        ok = False
        details = empty_session_handoff_details(status="invalid", ready=False)
        message = str(error)
    return SessionHandoffObservation(
        kind="session_handoff",
        run_id=run_id,
        ok=ok,
        handoff=handoff,
        message=message,
        ready=details.ready,
        status=details.status,
        blockers=details.blockers,
        background_processes_started=details.background_processes_started,
        active_background_processes=details.active_background_processes,
        verified_commands=details.verified_commands,
        pending_commands=details.pending_commands,
        failed_commands=details.failed_commands,
        verified_count=details.verified_count,
        pending_count=details.pending_count,
        failed_count=details.failed_count,
        pending_plan_items=details.pending_plan_items,
        pending_plan_count=details.pending_plan_count,
        plan_items_count=details.plan_items_count,
        plan_in_progress=details.plan_in_progress,
        file_references=details.file_references,
        file_count=details.file_count,
        shown_file_count=details.shown_file_count,
        files_truncated=details.files_truncated,
        completion_ready=details.completion_ready,
        completion_blockers=details.completion_blockers,
        latest_completion_blockers=details.latest_completion_blockers,
        latest_subagent_failures=details.latest_subagent_failures,
        **completion_detail_kwargs_from_object(details),
    )
