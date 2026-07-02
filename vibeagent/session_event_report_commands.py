from __future__ import annotations

from pathlib import Path
from typing import Any

from .session_command_reports import (
    format_session_command_entry,
    serialize_session_command_with_output,
    session_command_entries,
)
from .session_store import read_session_events
from .session_text_reports import (
    build_session_search_report_from_matches,
    build_session_transcript_report_from_events,
    format_session_search_matches,
    format_session_transcript_events,
    session_search_matches_from_events,
    validate_session_search_limits,
    validate_session_transcript_limits,
)
from .session_utils import session_dir


def format_session_transcript(
    project_root: str | Path,
    run_id: str,
    max_events: int = 80,
    max_text: int = 500,
) -> str:
    validate_session_transcript_limits(max_events, max_text)

    current_session_dir = session_dir(project_root, run_id)
    if not current_session_dir.is_dir():
        return f"Session not found: {run_id}"

    return format_session_transcript_events(
        run_id,
        read_session_events(project_root, run_id),
        max_events=max_events,
        max_text=max_text,
    )


def build_session_transcript_report(
    project_root: str | Path,
    run_id: str,
    max_events: int = 80,
    max_text: int = 500,
) -> dict[str, Any]:
    validate_session_transcript_limits(max_events, max_text)

    current_session_dir = session_dir(project_root, run_id)
    if not current_session_dir.is_dir():
        return {
            "session": run_id,
            "exists": False,
            "ok": False,
            "status": "missing",
            "message": f"Session not found: {run_id}",
        }

    return build_session_transcript_report_from_events(
        run_id,
        read_session_events(project_root, run_id),
        max_events=max_events,
        max_text=max_text,
    )


def format_session_search(
    project_root: str | Path,
    run_id: str,
    query: str,
    max_matches: int = 20,
    max_text: int = 500,
    case_sensitive: bool = False,
) -> str:
    validate_session_search_limits(query, max_matches, max_text)

    current_session_dir = session_dir(project_root, run_id)
    if not current_session_dir.is_dir():
        return f"Session not found: {run_id}"

    return format_session_search_matches(
        run_id,
        query,
        session_search_matches(project_root, run_id, query, max_text=max_text, case_sensitive=case_sensitive),
        max_matches=max_matches,
        case_sensitive=case_sensitive,
    )


def build_session_search_report(
    project_root: str | Path,
    run_id: str,
    query: str,
    max_matches: int = 20,
    max_text: int = 500,
    case_sensitive: bool = False,
) -> dict[str, Any]:
    validate_session_search_limits(query, max_matches, max_text)

    current_session_dir = session_dir(project_root, run_id)
    if not current_session_dir.is_dir():
        return {
            "session": run_id,
            "exists": False,
            "ok": False,
            "status": "missing",
            "query": query,
            "caseSensitive": case_sensitive,
            "message": f"Session not found: {run_id}",
        }

    return build_session_search_report_from_matches(
        run_id,
        query,
        session_search_matches(project_root, run_id, query, max_text=max_text, case_sensitive=case_sensitive),
        max_matches=max_matches,
        case_sensitive=case_sensitive,
    )


def session_search_matches(
    project_root: str | Path,
    run_id: str,
    query: str,
    max_text: int = 500,
    case_sensitive: bool = False,
) -> list[dict[str, Any]]:
    return session_search_matches_from_events(
        read_session_events(project_root, run_id),
        query,
        max_text=max_text,
        case_sensitive=case_sensitive,
    )


def format_session_commands(
    project_root: str | Path,
    run_id: str,
    max_commands: int = 20,
    max_output_chars: int = 2_000,
) -> str:
    validate_session_commands_limits(max_commands, max_output_chars)

    current_session_dir = session_dir(project_root, run_id)
    if not current_session_dir.is_dir():
        return f"Session not found: {run_id}"

    entries = session_command_entries(read_session_events(project_root, run_id))
    shown_entries = entries[-max_commands:]
    omitted = len(entries) - len(shown_entries)
    lines = [
        "Command results:",
        f"  session: {run_id}",
        f"  commands: {len(entries)}",
        f"  shown: {len(shown_entries)}/{len(entries)}",
        "  entries:",
    ]
    if omitted > 0:
        lines.append(f"    - [{omitted} older command result(s) omitted]")
    if not shown_entries:
        lines.append("    - none")
        return "\n".join(lines)

    for entry in shown_entries:
        lines.extend(format_session_command_entry(entry, max_output_chars=max_output_chars))
    return "\n".join(lines)


def validate_session_commands_limits(max_commands: int, max_output_chars: int) -> None:
    if max_commands < 1:
        raise ValueError("max_commands must be at least 1.")
    if max_commands > 100:
        raise ValueError("max_commands must be at most 100.")
    if max_output_chars < 0:
        raise ValueError("max_output_chars must be at least 0.")
    if max_output_chars > 20_000:
        raise ValueError("max_output_chars must be at most 20000.")


def build_session_commands_report(
    project_root: str | Path,
    run_id: str,
    max_commands: int = 20,
    max_output_chars: int = 2_000,
) -> dict[str, Any]:
    validate_session_commands_limits(max_commands, max_output_chars)

    current_session_dir = session_dir(project_root, run_id)
    if not current_session_dir.is_dir():
        return {
            "session": run_id,
            "exists": False,
            "ok": False,
            "status": "missing",
            "message": f"Session not found: {run_id}",
        }

    entries = session_command_entries(read_session_events(project_root, run_id))
    shown_entries = entries[-max_commands:]
    omitted = len(entries) - len(shown_entries)
    return {
        "session": run_id,
        "exists": True,
        "ok": True,
        "status": "ready",
        "commands": {
            "total": len(entries),
            "shown": len(shown_entries),
            "omitted": omitted,
            "truncated": omitted > 0,
            "items": [
                serialize_session_command_with_output(entry, max_output_chars)
                for entry in shown_entries
            ],
        },
        "message": f"Found {len(entries)} command result(s).",
    }
