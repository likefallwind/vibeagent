from __future__ import annotations

from typing import Any


def rename_fields(value: dict[str, Any], aliases: dict[str, str]) -> dict[str, Any]:
    normalized = dict(value)
    for source, target in aliases.items():
        if source in normalized and target not in normalized:
            normalized[target] = normalized[source]
        normalized.pop(source, None)
    return normalized
