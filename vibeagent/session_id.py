from __future__ import annotations

from pathlib import Path


def is_valid_session_id(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and value not in {".", ".."}
        and Path(value).name == value
    )
