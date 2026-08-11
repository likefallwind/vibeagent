from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BuiltinModelWorkflow:
    task: str
    metadata: dict[str, object]


__all__ = ["BuiltinModelWorkflow"]
