from __future__ import annotations

import shlex
from dataclasses import dataclass
from pathlib import Path

from .session_export import export_session
from .session_names import name_session, read_session_name
from .workspace_core import RunWorkspace, create_run_workspace


@dataclass(frozen=True)
class InteractiveSessionUpdate:
    text: str
    run_id: str | None
    pending_workspace: RunWorkspace | None


def interactive_session_prompt(
    project_root: Path,
    run_id: str | None,
    pending_workspace: RunWorkspace | None,
) -> str:
    selected = pending_workspace.run_id if pending_workspace is not None else run_id
    if selected is None:
        return "\nvibeagent> "
    try:
        name = read_session_name(project_root, selected)
    except (OSError, ValueError):
        name = None
    return f"\nvibeagent[{name}]> " if name else "\nvibeagent> "


def run_interactive_session_management(
    command,
    *,
    project_root: Path,
    run_id: str | None,
    pending_workspace: RunWorkspace | None,
) -> InteractiveSessionUpdate | None:
    if command.type == "rename":
        workspace = pending_workspace
        if run_id is None:
            workspace = create_run_workspace(project_root)
            run_id = workspace.run_id
        try:
            name = name_session(project_root, run_id, command.argument)
        except (OSError, ValueError) as error:
            return InteractiveSessionUpdate(f"Rename error: {error}", run_id, workspace)
        return InteractiveSessionUpdate(f"Session renamed: {name} ({run_id})", run_id, workspace)
    if command.type == "export":
        if run_id is None:
            return InteractiveSessionUpdate("Export error: no active coding session.", run_id, pending_workspace)
        path, error = _parse_export_path(command.argument)
        if error:
            return InteractiveSessionUpdate(error, run_id, pending_workspace)
        try:
            result = export_session(project_root, run_id, path)
        except (OSError, ValueError) as export_error:
            return InteractiveSessionUpdate(f"Export error: {export_error}", run_id, pending_workspace)
        return InteractiveSessionUpdate(result.message, run_id, pending_workspace)
    return None


def _parse_export_path(argument: str | None) -> tuple[str | None, str | None]:
    if not argument:
        return None, None
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        return None, f"Usage: /export [filename]\n  error: {error}"
    if len(parts) != 1:
        return None, "Usage: /export [filename]"
    return parts[0], None


__all__ = [
    "InteractiveSessionUpdate",
    "interactive_session_prompt",
    "run_interactive_session_management",
]
