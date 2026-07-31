from __future__ import annotations

from typing import Any

from .session_audit_formatting import (
    format_session_audit_report_text,
    format_session_handoff_report_text,
    format_session_verification_report_text,
)
from .session_audit_serialization import (
    failed_checkpoint_create_count,
    serialize_session_command_entry,
    serialize_session_failure,
    validate_session_audit_limits,
    validate_session_handoff_limits,
)
from .session_audit_readiness import (
    session_audit_blockers,
    session_audit_denied_approval_blocker_count,
    session_pending_plan_items,
)
from .session_audit_section_reports import (
    build_audit_background_processes_section,
    build_audit_checkpoints_section,
    build_audit_completion_section,
    build_audit_final_review_section,
    build_audit_summary_section,
)
from .session_audit_text import (
    format_session_audit_from_parts,
    format_session_handoff_readiness,
    format_session_handoff_sections,
)
from .session_types import SessionSummary
from .session_utils import compact
from .session_verification_reports import limited_string_group


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

    return {
        "session": run_id,
        "exists": True,
        "ok": not blockers,
        "ready": not blockers,
        "status": "ready" if not blockers else "blocked",
        "summary": build_audit_summary_section(summary, max_text=max_text),
        "finalReview": build_audit_final_review_section(summary),
        "checkpoints": build_audit_checkpoints_section(summary),
        "backgroundProcesses": build_audit_background_processes_section(
            summary,
            max_processes=max_failures,
            max_text=max_text,
        ),
        "blockers": {
            "count": len(blockers),
            "items": [compact(blocker, max_text) for blocker in blockers],
        },
        "completion": build_audit_completion_section(summary, max_text=max_text),
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
                    {
                        "status": item.status,
                        "step": compact(item.step, max_text),
                        **({"activeForm": compact(item.active_form, max_text)} if item.active_form else {}),
                    }
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
