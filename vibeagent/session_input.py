from __future__ import annotations


def normalize_optional_run_id(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if normalized.lower() == "latest":
        return None
    return normalized or None
