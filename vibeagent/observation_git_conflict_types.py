from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class GitConflictStatus:
    path: str
    status: str


@dataclass(frozen=True)
class GitConflictMarker:
    path: str
    line: int
    marker: str
    text: str


@dataclass(frozen=True)
class GitConflictsObservation:
    kind: Literal["git_conflicts"]
    ok: bool
    path: str
    unmerged: list[GitConflictStatus]
    unmerged_total: int
    markers: list[GitConflictMarker]
    markers_total: int
    scanned_files: int
    total_files: int
    truncated: bool
    message: str


__all__ = ["GitConflictMarker", "GitConflictStatus", "GitConflictsObservation"]
