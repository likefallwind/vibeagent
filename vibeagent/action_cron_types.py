from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class CronCreateAction:
    type: Literal["cron_create"]
    cron: str
    prompt: str
    recurring: bool


@dataclass(frozen=True)
class CronListAction:
    type: Literal["cron_list"]


@dataclass(frozen=True)
class CronDeleteAction:
    type: Literal["cron_delete"]
    task_id: str
