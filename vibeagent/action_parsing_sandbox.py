from __future__ import annotations

from typing import Any

from .action_parsing_scalars import ActionParseError


def parse_dangerously_disable_sandbox(
    value: dict[str, Any],
    raw: str,
    label: str,
) -> bool:
    requested = value.get("dangerouslyDisableSandbox", False)
    if not isinstance(requested, bool):
        raise ActionParseError(
            f"{label} dangerouslyDisableSandbox must be a boolean.",
            raw,
        )
    return requested


__all__ = ["parse_dangerously_disable_sandbox"]
