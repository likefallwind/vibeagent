from __future__ import annotations

from .action_results import (
    parse_session_commands_counts,
    parse_session_failures_counts,
    parse_session_files_counts,
    parse_session_search_counts,
)
from .session import (
    format_session_commands,
    format_session_failures,
    format_session_files,
    format_session_plan,
    format_session_search,
    format_session_summary,
    format_session_transcript,
    format_sessions,
    read_session_events,
    session_file_entries,
    summarize_session,
)
from .session_action_helpers import select_session_run_id, session_file_references
from .types import (
    Observation,
    SessionCommandsAction,
    SessionCommandsObservation,
    SessionFailuresAction,
    SessionFailuresObservation,
    SessionFilesAction,
    SessionFilesObservation,
    SessionPlanAction,
    SessionPlanObservation,
    SessionSearchAction,
    SessionSearchObservation,
    SessionSummaryAction,
    SessionSummaryObservation,
    SessionTranscriptAction,
    SessionTranscriptObservation,
)
from .workspace import RunWorkspace


def execute_session_report_action(workspace: RunWorkspace, action: object) -> Observation | None:
    if isinstance(action, SessionSummaryAction):
        return session_summary_observation(workspace, action)
    if isinstance(action, SessionPlanAction):
        return session_plan_observation(workspace, action)
    if isinstance(action, SessionTranscriptAction):
        return session_transcript_observation(workspace, action)
    if isinstance(action, SessionSearchAction):
        return session_search_observation(workspace, action)
    if isinstance(action, SessionCommandsAction):
        return session_commands_observation(workspace, action)
    if isinstance(action, SessionFilesAction):
        return session_files_observation(workspace, action)
    if isinstance(action, SessionFailuresAction):
        return session_failures_observation(workspace, action)
    return None


def session_summary_observation(workspace: RunWorkspace, action: SessionSummaryAction) -> SessionSummaryObservation:
    run_id = select_session_run_id(action.run_id, workspace.run_id)
    latest_subagent_failures: list[str] = []
    try:
        summary = summarize_session(workspace.root, run_id)
        summary_text = format_session_summary(summary)
        latest_subagent_failures = list(summary.latest_subagent_failures)
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
        latest_subagent_failures=latest_subagent_failures,
    )


def session_plan_observation(workspace: RunWorkspace, action: SessionPlanAction) -> SessionPlanObservation:
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


def session_transcript_observation(
    workspace: RunWorkspace,
    action: SessionTranscriptAction,
) -> SessionTranscriptObservation:
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


def session_search_observation(workspace: RunWorkspace, action: SessionSearchAction) -> SessionSearchObservation:
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


def session_commands_observation(
    workspace: RunWorkspace,
    action: SessionCommandsAction,
) -> SessionCommandsObservation:
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


def session_files_observation(workspace: RunWorkspace, action: SessionFilesAction) -> SessionFilesObservation:
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


def session_failures_observation(
    workspace: RunWorkspace,
    action: SessionFailuresAction,
) -> SessionFailuresObservation:
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
