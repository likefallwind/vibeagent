from __future__ import annotations

from pathlib import Path

from .workspace_core import RunWorkspace


def local_command_workspace(root: Path, run_id: str) -> RunWorkspace:
    return RunWorkspace(root=root, run_id=run_id, session_dir=root / ".vibeagent" / "sessions" / run_id)
