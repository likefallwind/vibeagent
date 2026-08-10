from __future__ import annotations

from pathlib import Path

from .session_store import read_session_events


def checkpoint_session_metadata(project_root: Path, run_id: str | None) -> dict[str, object]:
    if run_id is None:
        return {}
    try:
        events = read_session_events(project_root, run_id)
    except (OSError, ValueError):
        return {}
    if not events:
        return {}
    return {
        "session_run_id": run_id,
        "session_event_line": max(event.line_number for event in events),
    }


__all__ = ["checkpoint_session_metadata"]
