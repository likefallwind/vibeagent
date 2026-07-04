from __future__ import annotations


def normalize_optional_run_id(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip() or None
