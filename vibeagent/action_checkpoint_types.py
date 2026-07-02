from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class CheckpointCreateAction:
    type: Literal["checkpoint_create"]
    label: str | None = None


@dataclass(frozen=True)
class CheckpointListAction:
    type: Literal["checkpoint_list"]
    max_entries: int = 20


@dataclass(frozen=True)
class CheckpointShowAction:
    type: Literal["checkpoint_show"]
    checkpoint_id: str


@dataclass(frozen=True)
class CheckpointDiffAction:
    type: Literal["checkpoint_diff"]
    checkpoint_id: str
    max_chars: int = 40_000


@dataclass(frozen=True)
class CheckpointStatusAction:
    type: Literal["checkpoint_status"]
    checkpoint_id: str


@dataclass(frozen=True)
class CheckCheckpointRestoreAction:
    type: Literal["check_checkpoint_restore"]
    checkpoint_id: str


@dataclass(frozen=True)
class CheckpointRestoreAction:
    type: Literal["checkpoint_restore"]
    checkpoint_id: str


@dataclass(frozen=True)
class CheckCheckpointDeleteAction:
    type: Literal["check_checkpoint_delete"]
    checkpoint_id: str


@dataclass(frozen=True)
class CheckpointDeleteAction:
    type: Literal["checkpoint_delete"]
    checkpoint_id: str


@dataclass(frozen=True)
class CheckCheckpointPruneAction:
    type: Literal["check_checkpoint_prune"]
    keep_last: int


@dataclass(frozen=True)
class CheckpointPruneAction:
    type: Literal["checkpoint_prune"]
    keep_last: int
