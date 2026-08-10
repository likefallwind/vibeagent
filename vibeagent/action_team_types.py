from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class TeamCreateAction:
    type: Literal["team_create"]
    team_name: str
    description: str


@dataclass(frozen=True)
class TeamDeleteAction:
    type: Literal["team_delete"]
