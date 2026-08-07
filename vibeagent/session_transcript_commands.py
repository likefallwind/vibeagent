from __future__ import annotations

from pathlib import Path

from .session import build_session_transcript_report, get_last_session_id
from .session_input import normalize_optional_run_id


def get_transcript_text(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_events: int = 80,
    max_text: int = 500,
) -> str:
    return format_session_transcript_report_text(get_transcript_report(project_root, run_id, max_events=max_events, max_text=max_text))


def get_transcript_report(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_events: int = 80,
    max_text: int = 500,
) -> dict[str, object]:
    selected = normalize_optional_run_id(run_id) or get_last_session_id(project_root)
    if not selected:
        return {
            "session": None,
            "exists": False,
            "ok": False,
            "status": "missing",
            "message": "No sessions found.",
        }
    try:
        return build_session_transcript_report(project_root, selected, max_events=max_events, max_text=max_text)
    except ValueError as error:
        return {
            "session": selected,
            "exists": False,
            "ok": False,
            "status": "invalid",
            "message": str(error),
        }


def format_session_transcript_report_text(report: dict[str, object]) -> str:
    session = str(report.get("session") or "")
    if not bool(report.get("exists")):
        fallback = f"Session not found: {session}" if session else "No sessions found."
        return str(report.get("message") or fallback)

    events = report.get("events") if isinstance(report.get("events"), dict) else {}
    total = int(events.get("total", 0) or 0)
    shown = int(events.get("shown", 0) or 0)
    omitted = int(events.get("omitted", 0) or 0)
    lines = [
        "Transcript:",
        f"  session: {session}",
        f"  events: {total}",
        f"  shown: {shown}/{total}",
        f"  truncated: {'yes' if bool(events.get('truncated')) else 'no'}",
    ]
    malformed = int(events.get("malformed", 0) or 0)
    if malformed:
        lines.append(f"  malformedRows: {malformed}")
    lines.append("  timeline:")
    if omitted > 0:
        lines.append(f"    - [{omitted} older event(s) omitted]")
    items = [item for item in events.get("items", []) if isinstance(item, dict)] if isinstance(events.get("items"), list) else []
    if not items:
        lines.append("    - none")
        return "\n".join(lines)
    lines.extend(str(item.get("summary") or "    - unknown") for item in items)
    return "\n".join(lines)
