from __future__ import annotations

from .action_results import (
    build_session_command_output_scan_text,
    parse_session_commands_counts,
    parse_session_failures_counts,
    parse_session_files_counts,
    parse_session_search_counts,
)
from .output_conversion import output_context_results_from_dicts, output_diagnostics_from_dicts
from .session import (
    build_session_handoff_report,
    build_session_verification_report,
    format_session_audit,
    format_session_commands,
    format_session_failures,
    format_session_files,
    format_session_plan,
    format_session_search,
    format_session_summary,
    format_session_transcript,
    format_session_verification,
    format_sessions,
    read_session_events,
    session_audit_blockers,
    session_failure_entries,
    session_file_entries,
    summarize_session,
)
from .session_audit_formatting import format_session_handoff_report_text
from .session_handoff_details import empty_session_handoff_details, extract_session_handoff_details
from .session_verification_action_executor import (
    execute_run_session_verification_action,
    session_verification_group,
)
from .session_input import normalize_optional_run_id
from .types import (
    Observation,
    SessionAuditAction,
    SessionAuditObservation,
    SessionAuditProcess,
    SessionCommandsAction,
    SessionCommandsObservation,
    SessionFailuresAction,
    SessionFailuresObservation,
    SessionFilesAction,
    SessionFilesObservation,
    SessionHandoffAction,
    SessionHandoffObservation,
    SessionOutputContextsAction,
    SessionOutputContextsObservation,
    SessionOutputDiagnosticsAction,
    SessionOutputDiagnosticsObservation,
    SessionPlanAction,
    SessionPlanObservation,
    RunSessionVerificationAction,
    SessionSearchAction,
    SessionSearchObservation,
    SessionSummaryAction,
    SessionSummaryObservation,
    SessionTranscriptAction,
    SessionTranscriptObservation,
    SessionVerificationAction,
    SessionVerificationObservation,
)
from .workspace import RunWorkspace, read_output_contexts_result, read_output_diagnostics_result


def _select_session_run_id(action_run_id: str | None, workspace_run_id: str) -> str:
    return normalize_optional_run_id(action_run_id) or workspace_run_id


def execute_session_action(workspace: RunWorkspace, action: object, command_timeout_ms: int = 30_000) -> Observation | None:
    if isinstance(action, SessionSummaryAction):
        run_id = _select_session_run_id(action.run_id, workspace.run_id)
        try:
            summary_text = format_session_summary(summarize_session(workspace.root, run_id))
            ok = not summary_text.startswith("Session not found:")
            message = f"Read session summary for {run_id}." if ok else summary_text
        except ValueError as error:
            summary_text = ""
            ok = False
            message = str(error)
        recent_text = format_sessions(workspace.root, limit=action.recent_limit)
        return SessionSummaryObservation(
            kind="session_summary",
            run_id=run_id,
            ok=ok,
            summary=summary_text,
            recent_sessions=recent_text.splitlines(),
            message=message,
        )

    if isinstance(action, SessionPlanAction):
        run_id = _select_session_run_id(action.run_id, workspace.run_id)
        try:
            plan_text = format_session_plan(summarize_session(workspace.root, run_id))
            ok = not plan_text.startswith("Session not found:")
            message = f"Read session plan for {run_id}." if ok else plan_text
        except ValueError as error:
            plan_text = ""
            ok = False
            message = str(error)
        return SessionPlanObservation(
            kind="session_plan",
            run_id=run_id,
            ok=ok,
            plan=plan_text,
            message=message,
        )

    if isinstance(action, SessionTranscriptAction):
        run_id = _select_session_run_id(action.run_id, workspace.run_id)
        try:
            transcript = format_session_transcript(
                workspace.root,
                run_id,
                max_events=action.max_events,
                max_text=action.max_text,
            )
            ok = not transcript.startswith("Session not found:")
            message = f"Read session transcript for {run_id}." if ok else transcript
        except ValueError as error:
            transcript = ""
            ok = False
            message = str(error)
        return SessionTranscriptObservation(
            kind="session_transcript",
            run_id=run_id,
            ok=ok,
            transcript=transcript,
            message=message,
        )

    if isinstance(action, SessionSearchAction):
        run_id = _select_session_run_id(action.run_id, workspace.run_id)
        try:
            matches = format_session_search(
                workspace.root,
                run_id,
                action.query,
                max_matches=action.max_matches,
                max_text=action.max_text,
                case_sensitive=action.case_sensitive,
            )
            ok = not matches.startswith("Session not found:")
            message = f"Searched session {run_id} for {action.query!r}." if ok else matches
            total_matches, shown_matches = parse_session_search_counts(matches)
        except ValueError as error:
            matches = ""
            ok = False
            message = str(error)
            total_matches = 0
            shown_matches = 0
        return SessionSearchObservation(
            kind="session_search",
            run_id=run_id,
            ok=ok,
            query=action.query,
            matches=matches,
            total_matches=total_matches,
            shown_matches=shown_matches,
            message=message,
        )

    if isinstance(action, SessionCommandsAction):
        run_id = _select_session_run_id(action.run_id, workspace.run_id)
        try:
            commands = format_session_commands(
                workspace.root,
                run_id,
                max_commands=action.max_commands,
                max_output_chars=action.max_output_chars,
            )
            ok = not commands.startswith("Session not found:")
            message = f"Read session command results for {run_id}." if ok else commands
            command_count, shown_commands = parse_session_commands_counts(commands)
        except ValueError as error:
            commands = ""
            ok = False
            message = str(error)
            command_count = 0
            shown_commands = 0
        return SessionCommandsObservation(
            kind="session_commands",
            run_id=run_id,
            ok=ok,
            commands=commands,
            command_count=command_count,
            shown_commands=shown_commands,
            message=message,
        )

    if isinstance(action, SessionOutputContextsAction):
        run_id = _select_session_run_id(action.run_id, workspace.run_id)
        try:
            ok, command_count, shown_commands, output_text, scan_message = build_session_command_output_scan_text(
                workspace,
                run_id,
                max_commands=action.max_commands,
                max_output_chars=action.max_output_chars,
            )
            if not ok:
                return SessionOutputContextsObservation(
                    kind="session_output_contexts",
                    run_id=run_id,
                    ok=False,
                    contexts=[],
                    command_count=0,
                    shown_commands=0,
                    total_refs=0,
                    truncated=False,
                    message=scan_message,
                )
            if not output_text.strip():
                return SessionOutputContextsObservation(
                    kind="session_output_contexts",
                    run_id=run_id,
                    ok=True,
                    contexts=[],
                    command_count=command_count,
                    shown_commands=shown_commands,
                    total_refs=0,
                    truncated=False,
                    message=f"{scan_message} No command output references found.",
                )
            result = read_output_contexts_result(
                workspace,
                output_text,
                context_lines=action.context_lines,
                max_contexts=action.max_contexts,
                max_bytes_per_context=action.max_bytes_per_context,
            )
            contexts = output_context_results_from_dicts(result["contexts"])
            failed_contexts = sum(1 for item in contexts if not item.ok)
            return SessionOutputContextsObservation(
                kind="session_output_contexts",
                run_id=run_id,
                ok=failed_contexts == 0,
                contexts=contexts,
                command_count=command_count,
                shown_commands=shown_commands,
                total_refs=int(result["total_refs"]),
                truncated=bool(result["truncated"]),
                message=f"{scan_message} {result['message']}",
            )
        except ValueError as error:
            return SessionOutputContextsObservation(
                kind="session_output_contexts",
                run_id=run_id,
                ok=False,
                contexts=[],
                command_count=0,
                shown_commands=0,
                total_refs=0,
                truncated=False,
                message=str(error),
            )

    if isinstance(action, SessionOutputDiagnosticsAction):
        run_id = _select_session_run_id(action.run_id, workspace.run_id)
        try:
            ok, command_count, shown_commands, output_text, scan_message = build_session_command_output_scan_text(
                workspace,
                run_id,
                max_commands=action.max_commands,
                max_output_chars=action.max_output_chars,
            )
            if not ok:
                return SessionOutputDiagnosticsObservation(
                    kind="session_output_diagnostics",
                    run_id=run_id,
                    ok=False,
                    diagnostics=[],
                    contexts=[],
                    command_count=0,
                    shown_commands=0,
                    total_diagnostics=0,
                    total_refs=0,
                    diagnostics_truncated=False,
                    contexts_truncated=False,
                    message=scan_message,
                )
            if not output_text.strip():
                return SessionOutputDiagnosticsObservation(
                    kind="session_output_diagnostics",
                    run_id=run_id,
                    ok=True,
                    diagnostics=[],
                    contexts=[],
                    command_count=command_count,
                    shown_commands=shown_commands,
                    total_diagnostics=0,
                    total_refs=0,
                    diagnostics_truncated=False,
                    contexts_truncated=False,
                    message=f"{scan_message} No command output diagnostics found.",
                )
            result = read_output_diagnostics_result(
                workspace,
                output_text,
                context_lines=action.context_lines,
                max_diagnostics=action.max_diagnostics,
                max_contexts=action.max_contexts,
                max_bytes_per_context=action.max_bytes_per_context,
            )
            diagnostics = output_diagnostics_from_dicts(result["diagnostics"])
            contexts = output_context_results_from_dicts(result["contexts"])
            failed_contexts = sum(1 for item in contexts if not item.ok)
            return SessionOutputDiagnosticsObservation(
                kind="session_output_diagnostics",
                run_id=run_id,
                ok=failed_contexts == 0,
                diagnostics=diagnostics,
                contexts=contexts,
                command_count=command_count,
                shown_commands=shown_commands,
                total_diagnostics=int(result["total_diagnostics"]),
                total_refs=int(result["total_refs"]),
                diagnostics_truncated=bool(result["diagnostics_truncated"]),
                contexts_truncated=bool(result["contexts_truncated"]),
                message=f"{scan_message} {result['message']}",
            )
        except ValueError as error:
            return SessionOutputDiagnosticsObservation(
                kind="session_output_diagnostics",
                run_id=run_id,
                ok=False,
                diagnostics=[],
                contexts=[],
                command_count=0,
                shown_commands=0,
                total_diagnostics=0,
                total_refs=0,
                diagnostics_truncated=False,
                contexts_truncated=False,
                message=str(error),
            )

    if isinstance(action, SessionFilesAction):
        run_id = _select_session_run_id(action.run_id, workspace.run_id)
        try:
            files = format_session_files(workspace.root, run_id, max_files=action.max_files)
            ok = not files.startswith("Session not found:")
            message = f"Read session file references for {run_id}." if ok else files
            file_count, shown_files = parse_session_files_counts(files)
        except ValueError as error:
            files = ""
            ok = False
            message = str(error)
            file_count = 0
            shown_files = 0
        return SessionFilesObservation(
            kind="session_files",
            run_id=run_id,
            ok=ok,
            files=files,
            file_count=file_count,
            shown_files=shown_files,
            message=message,
        )

    if isinstance(action, SessionFailuresAction):
        run_id = _select_session_run_id(action.run_id, workspace.run_id)
        try:
            failures = format_session_failures(
                workspace.root,
                run_id,
                max_failures=action.max_failures,
                max_text=action.max_text,
            )
            ok = not failures.startswith("Session not found:")
            message = f"Read session failures for {run_id}." if ok else failures
            failure_count, shown_failures = parse_session_failures_counts(failures)
        except ValueError as error:
            failures = ""
            ok = False
            message = str(error)
            failure_count = 0
            shown_failures = 0
        return SessionFailuresObservation(
            kind="session_failures",
            run_id=run_id,
            ok=ok,
            failures=failures,
            failure_count=failure_count,
            shown_failures=shown_failures,
            message=message,
        )

    if isinstance(action, SessionVerificationAction):
        run_id = _select_session_run_id(action.run_id, workspace.run_id)
        verified_commands: list[dict[str, object]] = []
        pending_commands: list[dict[str, object]] = []
        failed_commands: list[dict[str, object]] = []
        verified_count = 0
        pending_count = 0
        failed_count = 0
        verification_truncated = False
        try:
            summary = summarize_session(workspace.root, run_id)
            verification = format_session_verification(summary, max_checks=action.max_checks)
            ok = not verification.startswith("Session not found:")
            message = f"Read session verification for {run_id}." if ok else verification
            if ok:
                report = build_session_verification_report(workspace.root, run_id, max_checks=action.max_checks)
                verified_commands, verified_count = session_verification_group(report, "verified")
                pending_commands, pending_count = session_verification_group(report, "pending")
                failed_commands, failed_count = session_verification_group(report, "failed")
                verification_truncated = bool(report.get("truncated"))
        except ValueError as error:
            verification = ""
            ok = False
            message = str(error)
        return SessionVerificationObservation(
            kind="session_verification",
            run_id=run_id,
            ok=ok,
            verification=verification,
            verified_commands=verified_commands,
            pending_commands=pending_commands,
            failed_commands=failed_commands,
            verified_count=verified_count,
            pending_count=pending_count,
            failed_count=failed_count,
            verification_truncated=verification_truncated,
            message=message,
        )

    if isinstance(action, RunSessionVerificationAction):
        return execute_run_session_verification_action(workspace, action, command_timeout_ms)

    if isinstance(action, SessionAuditAction):
        run_id = _select_session_run_id(action.run_id, workspace.run_id)
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
            completion_ready: bool | None = None
            completion_blockers: list[str] = []
            latest_completion_blockers: list[str] = []
            if ok:
                summary = summarize_session(workspace.root, run_id)
                events = read_session_events(workspace.root, run_id)
                failures = session_failure_entries(events, max_text=action.max_text)
                files = session_file_entries(events)
                blockers = session_audit_blockers(summary, failures, files)
                background_processes_started = summary.background_processes_started
                completion_ready = summary.completion_ready
                completion_blockers = list(summary.completion_blockers)
                latest_completion_blockers = list(summary.latest_completion_blockers)
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
            completion_ready = None
            completion_blockers = []
            latest_completion_blockers = []
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
            completion_ready=completion_ready,
            completion_blockers=completion_blockers,
            latest_completion_blockers=latest_completion_blockers,
        )

    if isinstance(action, SessionHandoffAction):
        run_id = _select_session_run_id(action.run_id, workspace.run_id)
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
        )

    return None
