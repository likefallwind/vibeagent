from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .user_paths import user_home
from .workspace_core import RunWorkspace


@dataclass(frozen=True)
class WorkspaceSettingsFile:
    path: Path
    boundary: Path
    source: str
    trusted: bool


def claude_settings_files(workspace: RunWorkspace) -> tuple[WorkspaceSettingsFile, ...]:
    home = user_home()
    user_path = home / ".claude/settings.json"
    project_path = workspace.root / ".claude/settings.json"
    local_path = workspace.root / ".claude/settings.local.json"
    return (
        _effective_settings_file(workspace, user_path, home, "~/.claude/settings.json", True),
        _effective_settings_file(workspace, project_path, workspace.root, ".claude/settings.json", False),
        _effective_settings_file(workspace, local_path, workspace.root, ".claude/settings.local.json", False),
    )


def _effective_settings_file(
    workspace: RunWorkspace,
    physical_path: Path,
    physical_boundary: Path,
    source: str,
    trusted: bool,
) -> WorkspaceSettingsFile:
    from .session_config_state import effective_settings_path

    path = effective_settings_path(workspace, physical_path)
    return WorkspaceSettingsFile(
        path=path,
        boundary=workspace.session_dir if path != physical_path else physical_boundary,
        source=source,
        trusted=trusted,
    )


def project_config_file(workspace: RunWorkspace, relative_path: str) -> WorkspaceSettingsFile:
    return WorkspaceSettingsFile(
        path=workspace.root / relative_path,
        boundary=workspace.root,
        source=relative_path,
        trusted=False,
    )


__all__ = ["WorkspaceSettingsFile", "claude_settings_files", "project_config_file"]
