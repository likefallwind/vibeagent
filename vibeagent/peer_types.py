from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


PeerInboundMode = Literal["accept", "hold", "refuse"]
PeerDeliveryStatus = Literal["delivered", "held", "refused", "error"]


class PeerMessagingError(ValueError):
    pass


@dataclass(frozen=True)
class PeerSession:
    id: str
    name: str
    project_root: str
    run_id: str | None
    socket_path: str
    pid: int
    bypasses_permissions: bool
    updated_at: float


@dataclass(frozen=True)
class PeerMessage:
    sender_id: str
    sender_name: str
    sender_project_root: str
    sender_bypasses_permissions: bool
    message: str
    received_at: float


@dataclass(frozen=True)
class PeerDelivery:
    status: PeerDeliveryStatus
    target_id: str
    target_name: str
    message: str
