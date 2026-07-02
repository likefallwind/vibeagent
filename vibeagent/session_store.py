from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from .session_types import SessionEvent, SessionInfo
from .session_utils import (
    events_path,
    session_events_safety_error,
    session_store_safety_error,
    sessions_dir,
)


def list_sessions(project_root: str | Path, limit: int = 20) -> list[SessionInfo]:
    if session_store_safety_error(project_root):
        return []
    sessions_root = sessions_dir(project_root)
    if not sessions_root.is_dir():
        return []

    infos: list[SessionInfo] = []
    for path in sessions_root.iterdir():
        if path.is_symlink() or not path.is_dir():
            continue
        try:
            info = read_session_info(path)
        except ValueError:
            continue
        if session_info_has_rows(info):
            infos.append(info)
    infos.sort(key=lambda info: info.last_event_time or datetime.min.replace(tzinfo=UTC), reverse=True)
    return infos[:limit]


def session_info_has_rows(info: SessionInfo) -> bool:
    return info.event_count > 0 or info.malformed_count > 0


def read_session_events(project_root: str | Path, run_id: str) -> list[SessionEvent]:
    return read_events_file(events_path(project_root, run_id))


def read_session_info(path: Path) -> SessionInfo:
    if path.is_symlink() or not path.is_dir():
        raise ValueError(f"Session path is not a regular directory: {path.name}")
    events = path / "events.jsonl"
    if session_events_safety_error(events):
        raise ValueError(f"Session events path is not a regular file: {path.name}/events.jsonl")
    parsed_events = read_events_file(events)
    event_count = len([event for event in parsed_events if not event.malformed])
    malformed_count = len(parsed_events) - event_count
    if events.exists():
        last_event_time = datetime.fromtimestamp(events.stat().st_mtime, tz=UTC)
    else:
        last_event_time = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    return SessionInfo(
        run_id=path.name,
        event_count=event_count,
        malformed_count=malformed_count,
        last_event_time=last_event_time,
    )


def read_events_file(path: Path) -> list[SessionEvent]:
    if session_events_safety_error(path):
        raise ValueError(f"Session events path is not a regular file: {path}")
    if not path.exists():
        return []
    events: list[SessionEvent] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError as error:
            events.append(
                SessionEvent(
                    type="malformed",
                    payload={},
                    line_number=line_number,
                    malformed=True,
                    error=f"Invalid JSON: {error.msg}",
                )
            )
            continue
        if not isinstance(parsed, dict) or not isinstance(parsed.get("type"), str):
            events.append(
                SessionEvent(
                    type="malformed",
                    payload={},
                    line_number=line_number,
                    malformed=True,
                    error="Event row must be an object with a string type.",
                )
            )
            continue
        events.append(
            SessionEvent(
                type=parsed["type"],
                payload={key: value for key, value in parsed.items() if key != "type"},
                line_number=line_number,
                raw=parsed,
            )
        )
    return events
