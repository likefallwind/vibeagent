from __future__ import annotations

from pathlib import Path
from typing import Any

from .session_command_reports import (
    command_output_tail,
    session_command_entries,
)
from .session_event_report_commands import (
    build_session_commands_report,
    build_session_search_report,
    build_session_transcript_report,
    format_session_commands,
    format_session_search,
    format_session_transcript,
    session_search_matches,
    validate_session_commands_limits,
)
from .session_file_reports import (
    add_session_path,
    build_session_files_report,
    classify_session_file_use,
    extract_session_paths,
    format_session_files,
    session_file_entries,
    session_file_payload,
)
from .session_failure_reports import (
    approval_failure_entry,
    approval_request_failure_detail,
    build_session_failures_report,
    command_failure_entry,
    format_session_failures,
    model_error_failure_entry,
    result_failure_detail,
    result_failure_entry,
    result_failure_message,
    session_failure_entries,
    session_failure_result_failed,
    tool_result_failure_entries,
    validate_session_failures_limits,
)
from .session_store import (
    list_sessions,
    read_events_file,
    read_session_events,
    read_session_info,
    session_info_has_rows,
)
from .session_summary_builder import summarize_session
from .session_timeline_reports import (
    format_detail_suffix,
    format_session_event_timeline_item,
    format_usage_suffix,
    legacy_model_raw_summary,
    model_tool_call_names,
    serialize_session_timeline_event,
)
from .session_verification_reports import (
    build_session_verification_report_from_summary,
    format_session_verification_summary,
    limited_string_group,
    validate_session_verification_report_limits,
)
from .session_summary_reports import (
    build_session_plan_report,
    build_session_summary_report,
    format_final_review_failure_lines,
    format_latest_completion_detail_lines,
    format_session_datetime,
    format_session_plan,
    format_session_summary,
    serialize_session_process,
    session_plan_status,
    session_summary_status,
)
from .session_audit_reports import (
    build_session_audit_report_from_parts,
    build_session_handoff_report_from_sections,
)
from .session_audit_readiness import (
    session_audit_blockers,
    session_pending_plan_items,
)
from .session_audit_text import (
    format_session_audit_from_parts,
    format_session_handoff_readiness,
    format_session_handoff_sections,
)
from .session_audit_serialization import (
    failed_checkpoint_create_count,
    serialize_session_command_entry,
    serialize_session_failure,
    validate_session_audit_limits,
    validate_session_handoff_limits,
)
from .session_types import SessionInfo, SessionSummary
from .session_summary_helpers import (
    merge_session_process_info,
    session_check_location,
    session_process_info,
)
from .session_handoff_commands import (
    build_session_audit_report,
    build_session_handoff_report,
    build_session_resume_context,
    build_session_verification_report,
    format_session_audit,
    format_session_handoff,
    format_session_verification,
)
from .session_utils import (
    as_nonnegative_int,
    compact,
    is_local_session_id,
    session_dir,
)
from .session_verification_state import (
    SESSION_PROJECT_CHANGE_RESULT_KINDS,
    session_command_result_key,
    session_failed_suggested_check_label,
    session_final_review_suggested_commands,
    session_iter_command_results,
    session_suggested_check_label,
)
def format_sessions(project_root: str | Path, limit: int = 20) -> str:
    sessions = list_sessions(project_root, limit=limit)
    if not sessions:
        return "No sessions found."
    lines = ["Recent sessions:"]
    for info in sessions:
        summary = summarize_session(project_root, info.run_id)
        last = (
            info.last_event_time.isoformat(timespec="seconds").replace("+00:00", "Z")
            if info.last_event_time
            else "unknown"
        )
        malformed = f", {info.malformed_count} malformed" if info.malformed_count else ""
        task = f"  task={compact(summary.task, 160)}" if summary.task else ""
        lines.append(
            f"  {info.run_id}  status={session_summary_status(summary)}  "
            f"events={info.event_count}{malformed}  last={last}{task}"
        )
    return "\n".join(lines)


def build_sessions_report(project_root: str | Path, limit: int = 20, max_text: int = 240) -> dict[str, Any]:
    sessions = list_sessions(project_root, limit=limit)
    return {
        "exists": bool(sessions),
        "ok": True,
        "status": "ready" if sessions else "missing",
        "sessions": {
            "total": len(sessions),
            "shown": len(sessions),
            "items": [
                serialize_session_info(project_root, info, max_text=max_text)
                for info in sessions
            ],
        },
        "message": f"Found {len(sessions)} session(s)." if sessions else "No sessions found.",
    }


def serialize_session_info(project_root: str | Path, info: SessionInfo, max_text: int = 240) -> dict[str, Any]:
    summary = summarize_session(project_root, info.run_id)
    return {
        "session": info.run_id,
        "status": session_summary_status(summary),
        "events": info.event_count,
        "malformed": info.malformed_count,
        "lastEventTime": format_session_datetime(info.last_event_time),
        "task": compact(summary.task, max_text) if summary.task else None,
        "completed": summary.completed,
        "failed": summary.failed,
        "blocked": summary.blocked,
    }


def get_last_session_id(project_root: str | Path) -> str | None:
    sessions = list_sessions(project_root, limit=1000)
    for session in sessions:
        if not is_local_session_id(session.run_id):
            return session.run_id
    return None


from .session_usage import (
    SessionUsageSummary,
    build_cost_report,
    build_run_cost_report,
    build_usage_report,
    decimal_rate_string,
    decimal_usd_string,
    format_cost,
    format_usage,
    format_usd,
    missing_cost_rate_names,
    serialize_cost_rates,
    serialize_usage_summary,
    summarize_usage,
    token_cost,
    usage_has_tokens,
)
