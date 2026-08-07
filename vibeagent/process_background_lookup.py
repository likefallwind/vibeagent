from __future__ import annotations

import sys
from typing import Any


def background_processes() -> dict[str, Any]:
    runtime_module = sys.modules.get("vibeagent.process_runtime")
    value = getattr(runtime_module, "BACKGROUND_PROCESSES", None) if runtime_module is not None else None
    return value if isinstance(value, dict) else {}
