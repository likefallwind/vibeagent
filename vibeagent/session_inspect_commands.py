from __future__ import annotations

from pathlib import Path
from typing import Any

from .session_file_reports import session_file_entries as _session_file_entries
from .session_id import is_valid_session_id as _is_valid_session_id
from .session_store import read_session_events as _read_session_events
from .session_summary_builder import summarize_session_from_events as _summarize_session_from_events
from .session_summary_reports import (
    session_plan_status as _session_plan_status,
    session_summary_status as _session_summary_status,
)
from .session_text_reports import build_session_transcript_report_from_events as _build_transcript
from .session_types import SessionEvent as _SessionEvent
from .session_types import SessionSummary as _SessionSummary
from .session_utils import compact as _compact
from .session_verification_reports import (
    build_session_verification_report_from_summary as _build_verification,
)


INSPECT_MAX_EVENTS = 80
INSPECT_MAX_EVENT_TEXT = 1_000
INSPECT_MAX_FILES = 100
INSPECT_MAX_FILE_TOOLS = 20
INSPECT_MAX_FILE_LINES = 20
INSPECT_MAX_CHECKS = 50
INSPECT_MAX_CHECK_TEXT = 500
INSPECT_MAX_PLAN_ITEMS = 20
INSPECT_MAX_PLAN_TEXT = 2_000
INSPECT_MAX_OVERVIEW_TEXT = 4_000


def get_session_inspect_report(
    project_root: str | Path,
    run_id: str,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    if not _is_valid_session_id(run_id):
        return _error_report(root, run_id, f"Invalid session id: {run_id}")
    try:
        events = _read_session_events(root, run_id)
        summary = _summarize_session_from_events(root, run_id, events)
        if not summary.exists:
            return _error_report(root, run_id, f"Session not found: {run_id}")
        transcript = _build_transcript(
            run_id,
            events,
            max_events=INSPECT_MAX_EVENTS,
            max_text=INSPECT_MAX_EVENT_TEXT,
        )
        verification = _verification(
            _build_verification(
                summary,
                max_checks=INSPECT_MAX_CHECKS,
                max_text=INSPECT_MAX_CHECK_TEXT,
            )
        )
    except (OSError, ValueError) as error:
        return _error_report(root, run_id, str(error))

    return {
        "projectRoot": str(root),
        "session": run_id,
        "exists": True,
        "ok": True,
        "status": _session_summary_status(summary),
        "overview": _overview(summary),
        "plan": _plan(summary),
        "transcript": transcript,
        "files": _files(run_id, events),
        "verification": verification,
        "message": f"Read session inspector report for {run_id}.",
    }


def format_session_inspect_report_text(report: dict[str, object]) -> str:
    if not bool(report.get("ok")):
        return str(report.get("message") or "Session inspector report is unavailable.")
    overview = _mapping(report.get("overview"))
    plan = _mapping(report.get("plan"))
    verification = _mapping(report.get("verification"))
    files = _mapping(_mapping(report.get("files")).get("files"))
    events = _mapping(_mapping(report.get("transcript")).get("events"))
    lines = [
        "Session inspector:",
        f"  session: {report.get('session')}",
        f"  status: {report.get('status')}",
        f"  task: {overview.get('task') or ''}",
        f"  final: {overview.get('finalMessage') or ''}",
        f"  plan: {plan.get('shown', 0)}/{plan.get('total', 0)}",
        (
            "  verification: "
            f"ready={'yes' if bool(verification.get('ready')) else 'no'}, "
            f"verified={_group_total(verification, 'verified')}, "
            f"pending={_group_total(verification, 'pending')}, "
            f"failed={_group_total(verification, 'failed')}"
        ),
        f"  files: {files.get('shown', 0)}/{files.get('total', 0)}",
        f"  timeline: {events.get('shown', 0)}/{events.get('total', 0)}",
    ]
    return "\n".join(lines)


def _overview(summary: _SessionSummary) -> dict[str, object]:
    return {
        "status": _session_summary_status(summary),
        "task": _optional_compact(summary.task, INSPECT_MAX_OVERVIEW_TEXT),
        "finalMessage": _optional_compact(summary.final_message, INSPECT_MAX_OVERVIEW_TEXT),
        "events": {
            "total": summary.event_count,
            "malformed": summary.malformed_count,
            "iterations": summary.iterations,
        },
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
        },
        "completion": {
            "ready": summary.completion_ready,
            "blockers": len(summary.completion_blockers),
            "warnings": len(summary.completion_warnings),
            "blockedAttempts": summary.completion_blocked_count,
        },
        "finalReview": {
            "seen": summary.final_review_seen,
            "ready": summary.final_review_ready,
            "blockingIssues": summary.final_review_blocking_issues,
            "warnings": summary.final_review_warnings,
            "files": summary.final_review_files,
        },
        "checkpoints": {
            "created": summary.checkpoints_created,
            "latestId": _optional_compact(summary.latest_checkpoint_id, 255),
        },
    }


def _plan(summary: _SessionSummary) -> dict[str, object]:
    shown = summary.latest_plan[:INSPECT_MAX_PLAN_ITEMS]
    return {
        "status": _session_plan_status(summary),
        "total": len(summary.latest_plan),
        "shown": len(shown),
        "truncated": len(summary.latest_plan) > len(shown),
        "items": [
            {
                "status": item.status,
                "step": _compact(item.step, INSPECT_MAX_PLAN_TEXT),
                "activeForm": _optional_compact(item.active_form, INSPECT_MAX_PLAN_TEXT),
            }
            for item in shown
        ],
    }


def _files(run_id: str, events: list[_SessionEvent]) -> dict[str, object]:
    entries = _session_file_entries(events)
    shown = entries[:INSPECT_MAX_FILES]
    return {
        "session": run_id,
        "exists": True,
        "ok": True,
        "status": "ready",
        "files": {
            "total": len(entries),
            "shown": len(shown),
            "omitted": len(entries) - len(shown),
            "truncated": len(entries) > len(shown),
            "items": [
                {
                    "path": _compact(entry["path"], INSPECT_MAX_OVERVIEW_TEXT),
                    "tools": entry["tools"][:INSPECT_MAX_FILE_TOOLS],
                    "toolCount": len(entry["tools"]),
                    "toolsTruncated": len(entry["tools"]) > INSPECT_MAX_FILE_TOOLS,
                    "uses": entry["uses"][:INSPECT_MAX_FILE_TOOLS],
                    "useCount": len(entry["uses"]),
                    "usesTruncated": len(entry["uses"]) > INSPECT_MAX_FILE_TOOLS,
                    "lines": entry["lines"][:INSPECT_MAX_FILE_LINES],
                    "count": entry["count"],
                    "linesTruncated": len(entry["lines"]) > INSPECT_MAX_FILE_LINES,
                }
                for entry in shown
            ],
        },
        "message": f"Found {len(entries)} referenced file(s).",
    }


def _verification(report: dict[str, Any]) -> dict[str, object]:
    return {
        "session": report.get("session"),
        "exists": report.get("exists"),
        "ok": report.get("ok"),
        "ready": report.get("ready"),
        "status": report.get("status"),
        "verified": _verification_group(report.get("verified")),
        "pending": _verification_group(report.get("pending")),
        "failed": _verification_group(report.get("failed")),
        "truncated": report.get("truncated"),
    }


def _verification_group(value: object) -> dict[str, object]:
    group = _mapping(value)
    return {
        "total": group.get("total", 0),
        "shown": group.get("shown", 0),
        "truncated": group.get("truncated", False),
        "items": group.get("items", []),
    }


def _optional_compact(value: object, maximum: int) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return _compact(value, maximum)


def _mapping(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _group_total(report: dict[str, Any], key: str) -> int:
    return int(_mapping(report.get(key)).get("total", 0) or 0)


def _error_report(root: Path, run_id: str, message: str) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "session": run_id,
        "exists": False,
        "ok": False,
        "status": "missing" if message.startswith("Session not found:") else "invalid",
        "overview": None,
        "plan": None,
        "transcript": None,
        "files": None,
        "verification": None,
        "message": message,
    }


__all__ = [
    "format_session_inspect_report_text",
    "get_session_inspect_report",
]
