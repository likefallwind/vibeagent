from __future__ import annotations

from .action_results import (
    parse_session_commands_counts,
    parse_session_failures_counts,
    parse_session_files_counts,
    parse_session_search_counts,
)
from .session import (
    build_session_verification_report,
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
    session_file_entries,
    summarize_session,
)
from .session_action_helpers import select_session_run_id, session_file_references
from .session_audit_action_executor import execute_session_audit_action, execute_session_handoff_action
from .session_output_action_executor import execute_session_output_action
from .session_verification_action_executor import (
    execute_run_session_verification_action,
    session_verification_group,
)
from .types import (
    Observation,
    SessionAuditAction,
    SessionCommandsAction,
    SessionCommandsObservation,
    SessionFailuresAction,
    SessionFailuresObservation,
    SessionFilesAction,
    SessionFilesObservation,
    SessionHandoffAction,
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
from .workspace import RunWorkspace


def execute_session_action(workspace: RunWorkspace, action: object, command_timeout_ms: int = 30_000) -> Observation | None:
    output_observation = execute_session_output_action(workspace, action)
    if output_observation is not None:
        return output_observation

    if isinstance(action, SessionSummaryAction):
        run_id = select_session_run_id(action.run_id, workspace.run_id)
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
        run_id = select_session_run_id(action.run_id, workspace.run_id)
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
        run_id = select_session_run_id(action.run_id, workspace.run_id)
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
        run_id = select_session_run_id(action.run_id, workspace.run_id)
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
        run_id = select_session_run_id(action.run_id, workspace.run_id)
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

    if isinstance(action, SessionFilesAction):
        run_id = select_session_run_id(action.run_id, workspace.run_id)
        try:
            files = format_session_files(workspace.root, run_id, max_files=action.max_files)
            ok = not files.startswith("Session not found:")
            message = f"Read session file references for {run_id}." if ok else files
            file_count, shown_files = parse_session_files_counts(files)
            file_references: list[dict[str, object]] = []
            files_truncated = False
            if ok:
                file_entries = session_file_entries(read_session_events(workspace.root, run_id))
                file_references, file_count, shown_files, files_truncated = session_file_references(
                    file_entries, action.max_files
                )
        except ValueError as error:
            files = ""
            ok = False
            message = str(error)
            file_count = 0
            shown_files = 0
            file_references = []
            files_truncated = False
        return SessionFilesObservation(
            kind="session_files",
            run_id=run_id,
            ok=ok,
            files=files,
            file_count=file_count,
            shown_files=shown_files,
            message=message,
            file_references=file_references,
            files_truncated=files_truncated,
        )

    if isinstance(action, SessionFailuresAction):
        run_id = select_session_run_id(action.run_id, workspace.run_id)
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
        run_id = select_session_run_id(action.run_id, workspace.run_id)
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
        return execute_session_audit_action(workspace, action)

    if isinstance(action, SessionHandoffAction):
        return execute_session_handoff_action(workspace, action)

    return None
