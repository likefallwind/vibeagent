from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class TeamCreateObservation:
    kind: Literal["team_create"]
    ok: bool
    team_name: str | None
    description: str
    message: str


@dataclass(frozen=True)
class TeamDeleteObservation:
    kind: Literal["team_delete"]
    ok: bool
    team_name: str | None
    active_teammates: list[str] = field(default_factory=list)
    message: str = ""
