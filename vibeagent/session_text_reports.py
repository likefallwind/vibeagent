from __future__ import annotations

from typing import Any

from .session_timeline_reports import (
    format_session_event_timeline_item,
    serialize_session_timeline_event,
)
from .session_types import SessionEvent


def format_session_transcript_events(
    run_id: str,
    events: list[SessionEvent],
    max_events: int = 80,
    max_text: int = 500,
) -> str:
    shown_events = events[-max_events:]
    omitted = len(events) - len(shown_events)
    malformed_count = sum(1 for event in events if event.malformed)
    lines = [
        "Transcript:",
        f"  session: {run_id}",
        f"  events: {len(events)}",
        f"  shown: {len(shown_events)}/{len(events)}",
        f"  truncated: {'yes' if omitted > 0 else 'no'}",
    ]
    if malformed_count:
        lines.append(f"  malformedRows: {malformed_count}")
    lines.append("  timeline:")
    if omitted > 0:
        lines.append(f"    - [{omitted} older event(s) omitted]")
    if not shown_events:
        lines.append("    - none")
        return "\n".join(lines)

    for event in shown_events:
        lines.append(format_session_event_timeline_item(event, max_text=max_text))
    return "\n".join(lines)


def validate_session_transcript_limits(max_events: int, max_text: int) -> None:
    if max_events < 1:
        raise ValueError("max_events must be at least 1.")
    if max_events > 500:
        raise ValueError("max_events must be at most 500.")
    if max_text < 80:
        raise ValueError("max_text must be at least 80.")
    if max_text > 5_000:
        raise ValueError("max_text must be at most 5000.")


def build_session_transcript_report_from_events(
    run_id: str,
    events: list[SessionEvent],
    max_events: int = 80,
    max_text: int = 500,
) -> dict[str, Any]:
    shown_events = events[-max_events:]
    omitted = len(events) - len(shown_events)
    malformed_count = sum(1 for event in events if event.malformed)
    return {
        "session": run_id,
        "exists": True,
        "ok": True,
        "status": "ready",
        "events": {
            "total": len(events),
            "shown": len(shown_events),
            "omitted": omitted,
            "truncated": omitted > 0,
            "malformed": malformed_count,
            "items": [serialize_session_timeline_event(event, max_text=max_text) for event in shown_events],
        },
        "message": f"Found {len(events)} session event(s).",
    }


def format_session_search_matches(
    run_id: str,
    query: str,
    matches: list[dict[str, Any]],
    max_matches: int = 20,
    case_sensitive: bool = False,
) -> str:
    shown = matches[:max_matches]
    lines = [
        "Session search:",
        f"  session: {run_id}",
        f"  query: {query}",
        f"  matches: {len(matches)}",
        f"  shown: {len(shown)}/{len(matches)}",
        f"  caseSensitive: {'yes' if case_sensitive else 'no'}",
        "  timeline:",
    ]
    if not shown:
        lines.append("    - none")
    else:
        lines.extend(item["summary"] for item in shown)
    if len(matches) > len(shown):
        lines.append(f"    - [{len(matches) - len(shown)} later match(es) omitted]")
    return "\n".join(lines)


def validate_session_search_limits(query: str, max_matches: int, max_text: int) -> None:
    if not query.strip():
        raise ValueError("query must not be empty.")
    if max_matches < 1:
        raise ValueError("max_matches must be at least 1.")
    if max_matches > 100:
        raise ValueError("max_matches must be at most 100.")
    if max_text < 80:
        raise ValueError("max_text must be at least 80.")
    if max_text > 5_000:
        raise ValueError("max_text must be at most 5000.")


def build_session_search_report_from_matches(
    run_id: str,
    query: str,
    matches: list[dict[str, Any]],
    max_matches: int = 20,
    case_sensitive: bool = False,
) -> dict[str, Any]:
    shown = matches[:max_matches]
    omitted = len(matches) - len(shown)
    return {
        "session": run_id,
        "exists": True,
        "ok": True,
        "status": "ready",
        "query": query,
        "caseSensitive": case_sensitive,
        "matches": {
            "total": len(matches),
            "shown": len(shown),
            "omitted": omitted,
            "truncated": omitted > 0,
            "items": shown,
        },
        "message": f"Found {len(matches)} matching session event(s).",
    }


def session_search_matches_from_events(
    events: list[SessionEvent],
    query: str,
    max_text: int = 500,
    case_sensitive: bool = False,
) -> list[dict[str, Any]]:
    needle = query if case_sensitive else query.casefold()
    matches: list[dict[str, Any]] = []
    for event in events:
        item = serialize_session_timeline_event(event, max_text=max_text)
        haystack = item["summary"] if case_sensitive else item["summary"].casefold()
        if needle in haystack:
            matches.append(item)
    return matches
