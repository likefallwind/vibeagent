from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class LspQueryObservation:
    kind: Literal["lsp_query"]
    ok: bool
    server: str
    operation: str
    path: str | None
    results: list[dict[str, object]]
    total: int
    truncated: bool
    message: str


@dataclass(frozen=True)
class LspDiagnosticsObservation:
    kind: Literal["lsp_diagnostics"]
    ok: bool
    server: str
    paths: list[str]
    diagnostics: list[dict[str, object]]
    total: int
    truncated: bool
    message: str


__all__ = ["LspDiagnosticsObservation", "LspQueryObservation"]
