from __future__ import annotations

import os
from pathlib import Path


VIBEAGENT_USER_HOME = "VIBEAGENT_USER_HOME"


def user_home() -> Path:
    configured = os.environ.get(VIBEAGENT_USER_HOME)
    return (Path(configured).expanduser() if configured else Path.home()).resolve()


__all__ = ["VIBEAGENT_USER_HOME", "user_home"]
