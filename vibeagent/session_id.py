from __future__ import annotations

from pathlib import Path
from uuid import UUID


def is_valid_session_id(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and value not in {".", ".."}
        and Path(value).name == value
    )


def normalize_requested_session_id(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("--session-id must be a valid UUID.")
    try:
        normalized = str(UUID(value))
    except (AttributeError, ValueError):
        raise ValueError("--session-id must be a valid UUID.") from None
    if value.lower() != normalized:
        raise ValueError("--session-id must be a valid UUID.")
    return normalized
