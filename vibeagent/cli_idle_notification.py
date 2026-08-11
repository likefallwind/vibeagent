from __future__ import annotations

from dataclasses import dataclass, field
import time


@dataclass
class IdleNotificationTimer:
    delay_seconds: float = 60.0
    started_at: float = field(default_factory=time.monotonic)
    sent: bool = False

    def due(self, now: float | None = None) -> bool:
        if self.sent:
            return False
        current = time.monotonic() if now is None else now
        if current - self.started_at < self.delay_seconds:
            return False
        self.sent = True
        return True


__all__ = ["IdleNotificationTimer"]
