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
    return (
        WorkspaceSettingsFile(
            path=home / ".claude/settings.json",
            boundary=home,
            source="~/.claude/settings.json",
            trusted=True,
        ),
        WorkspaceSettingsFile(
            path=workspace.root / ".claude/settings.json",
            boundary=workspace.root,
            source=".claude/settings.json",
            trusted=False,
        ),
        WorkspaceSettingsFile(
            path=workspace.root / ".claude/settings.local.json",
            boundary=workspace.root,
            source=".claude/settings.local.json",
            trusted=False,
        ),
    )


def project_config_file(workspace: RunWorkspace, relative_path: str) -> WorkspaceSettingsFile:
    return WorkspaceSettingsFile(
        path=workspace.root / relative_path,
        boundary=workspace.root,
        source=relative_path,
        trusted=False,
    )


__all__ = ["WorkspaceSettingsFile", "claude_settings_files", "project_config_file"]
