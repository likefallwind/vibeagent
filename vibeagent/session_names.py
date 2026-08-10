from __future__ import annotations

import re
from pathlib import Path

from .agent_runtime_utils import append_session_event
from .redaction import redact_sensitive_text
from .session_id import is_valid_session_id
from .session_store import list_sessions, read_session_events


MAX_SESSION_NAME_CHARS = 80
SESSION_NAMED_EVENT = "session_named"
SESSION_BRANCH_EVENT = "session_branched"
RESERVED_SESSION_NAMES = frozenset({"latest", "off", "clear", "none"})


def name_session(project_root: Path, run_id: str, name: str | None = None) -> str:
    root = project_root.resolve()
    _require_session(root, run_id)
    normalized = normalize_session_name(name) if name is not None else suggest_session_name(root, run_id)
    existing = find_named_session(root, normalized)
    if existing is not None and existing != run_id:
        raise ValueError(f"Session name is already in use: {normalized} ({existing})")
    append_session_event(root / ".vibeagent" / "sessions" / run_id, SESSION_NAMED_EVENT, {"name": normalized})
    return normalized


def clear_session_name(project_root: Path, run_id: str) -> None:
    root = project_root.resolve()
    _require_session(root, run_id)
    append_session_event(root / ".vibeagent" / "sessions" / run_id, SESSION_NAMED_EVENT, {"name": None})


def transfer_session_name(project_root: Path, source_run_id: str | None, target_run_id: str) -> str | None:
    if source_run_id is None or source_run_id == target_run_id:
        return None
    root = project_root.resolve()
    name = read_session_name(root, source_run_id)
    if name is None:
        return None
    _require_session(root, target_run_id)
    target_dir = root / ".vibeagent" / "sessions" / target_run_id
    append_session_event(target_dir, SESSION_NAMED_EVENT, {"name": name})
    try:
        clear_session_name(root, source_run_id)
    except (OSError, ValueError):
        append_session_event(target_dir, SESSION_NAMED_EVENT, {"name": None})
        raise
    return name


def read_session_name(project_root: Path, run_id: str) -> str | None:
    current: str | None = None
    for event in read_session_events(project_root, run_id):
        if event.malformed or event.type not in {SESSION_BRANCH_EVENT, SESSION_NAMED_EVENT}:
            continue
        name = event.payload.get("name")
        if event.type == SESSION_BRANCH_EVENT and name is None:
            continue
        if event.type == SESSION_NAMED_EVENT and name is None:
            current = None
            continue
        if not isinstance(name, str):
            raise ValueError(f"Session {run_id} has malformed name metadata.")
        try:
            normalized = normalize_session_name(name)
        except ValueError as error:
            raise ValueError(f"Session {run_id} has malformed name metadata.") from error
        if normalized != name:
            raise ValueError(f"Session {run_id} has malformed name metadata.")
        current = normalized
    return current


def resolve_session_reference(project_root: Path, value: str) -> str:
    root = project_root.resolve()
    direct = root / ".vibeagent" / "sessions" / value
    if is_valid_session_id(value) and direct.is_dir() and not direct.is_symlink():
        return value
    matches: list[str] = []
    for info in list_sessions(root, limit=10_000):
        try:
            name = read_session_name(root, info.run_id)
        except ValueError:
            continue
        if name == value:
            matches.append(info.run_id)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(f"Session name is ambiguous: {value}")
    return value


def find_named_session(project_root: Path, name: str) -> str | None:
    resolved = resolve_session_reference(project_root, name)
    direct = project_root.resolve() / ".vibeagent" / "sessions" / name
    return resolved if resolved != name or (direct.is_dir() and not direct.is_symlink()) else None


def normalize_session_name(value: str) -> str:
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ValueError("Session name must not contain control characters.")
    if redact_sensitive_text(value) != value:
        raise ValueError("Session name must not contain sensitive credentials.")
    normalized = " ".join(value.strip().split())
    if not normalized:
        raise ValueError("Session name must not be empty.")
    if len(normalized) > MAX_SESSION_NAME_CHARS:
        raise ValueError(f"Session name must not exceed {MAX_SESSION_NAME_CHARS} characters.")
    if normalized.lower() in RESERVED_SESSION_NAMES:
        raise ValueError(f"Session name is reserved: {normalized}")
    return normalized


def suggest_session_name(project_root: Path, run_id: str) -> str:
    task: str | None = None
    for event in read_session_events(project_root, run_id):
        if not event.malformed and event.type == "task" and isinstance(event.payload.get("task"), str):
            task = str(event.payload["task"])
            break
    if not task or not task.strip():
        raise ValueError("Cannot generate a session name before the first coding task.")
    words = re.sub(r"[^\w.-]+", "-", task.strip(), flags=re.UNICODE).strip("-._")
    base = words[:60].rstrip("-._") or "session"
    if base.lower() in RESERVED_SESSION_NAMES:
        base = f"{base}-session"
    candidate = base
    suffix = 2
    while (existing := find_named_session(project_root, candidate)) is not None and existing != run_id:
        tail = f"-{suffix}"
        candidate = f"{base[: MAX_SESSION_NAME_CHARS - len(tail)].rstrip('-._')}{tail}"
        suffix += 1
    return normalize_session_name(candidate)


def _require_session(project_root: Path, run_id: str) -> None:
    if not is_valid_session_id(run_id):
        raise ValueError(f"Invalid session id: {run_id}")
    path = project_root / ".vibeagent" / "sessions" / run_id
    if path.is_symlink() or not path.is_dir():
        raise ValueError(f"Session not found: {run_id}")


__all__ = [
    "MAX_SESSION_NAME_CHARS",
    "RESERVED_SESSION_NAMES",
    "SESSION_NAMED_EVENT",
    "find_named_session",
    "clear_session_name",
    "name_session",
    "normalize_session_name",
    "read_session_name",
    "resolve_session_reference",
    "suggest_session_name",
    "transfer_session_name",
]
