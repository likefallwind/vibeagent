from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class BrowserObservation:
    kind: Literal["browser"]
    ok: bool
    operation: str
    session: str
    output: str
    output_truncated: bool
    path: str | None
    error: str | None
    message: str


__all__ = ["BrowserObservation"]
