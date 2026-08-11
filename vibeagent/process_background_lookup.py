from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


def background_processes() -> dict[str, Any]:
    runtime_module = sys.modules.get("vibeagent.process_runtime")
    value = getattr(runtime_module, "BACKGROUND_PROCESSES", None) if runtime_module is not None else None
    return value if isinstance(value, dict) else {}


def background_process_for_root(root: Path, process_id: str) -> Any | None:
    background = background_processes().get(process_id)
    if background is None or getattr(background, "root", None) != root.resolve():
        return None
    return background


def background_processes_for_root(root: Path) -> dict[str, Any]:
    resolved_root = root.resolve()
    return {
        process_id: background
        for process_id, background in background_processes().items()
        if getattr(background, "root", None) == resolved_root
    }
