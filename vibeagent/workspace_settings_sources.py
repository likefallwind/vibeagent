from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from .user_paths import user_home
from .workspace_core import RunWorkspace
from .workspace_metadata_files import has_symlink_component, read_regular_file_bytes


@dataclass(frozen=True)
class WorkspaceSettingsFile:
    path: Path | None
    boundary: Path
    source: str
    trusted: bool
    inline_json: str | None = None


def claude_settings_files(workspace: RunWorkspace) -> tuple[WorkspaceSettingsFile, ...]:
    home = user_home()
    user_path = home / ".claude/settings.json"
    project_path = workspace.root / ".claude/settings.json"
    local_path = workspace.root / ".claude/settings.local.json"
    selected = set(workspace.setting_sources)
    files: list[WorkspaceSettingsFile] = []
    if "user" in selected:
        files.append(_effective_settings_file(workspace, user_path, home, "~/.claude/settings.json", True))
    if "project" in selected:
        files.append(_effective_settings_file(workspace, project_path, workspace.root, ".claude/settings.json", False))
    if "local" in selected:
        files.append(_effective_settings_file(workspace, local_path, workspace.root, ".claude/settings.local.json", False))
    if workspace.settings_override_json is not None:
        files.append(
            WorkspaceSettingsFile(
                path=None,
                boundary=workspace.root,
                source="CLI --settings",
                trusted=True,
                inline_json=workspace.settings_override_json,
            )
        )
    return tuple(files)


def settings_file_exists(config: WorkspaceSettingsFile) -> bool:
    return config.inline_json is not None or (
        config.path is not None and (config.path.exists() or config.path.is_symlink())
    )


def read_settings_payload(
    config: WorkspaceSettingsFile,
    *,
    max_bytes: int,
) -> dict[str, object]:
    if config.inline_json is not None:
        raw = config.inline_json.encode("utf-8")
    else:
        assert config.path is not None
        if has_symlink_component(config.boundary, config.path):
            raise ValueError(
                f"{config.source} must be a regular non-symlink file; symbolic link detected."
            )
        raw = read_regular_file_bytes(config.path, max_bytes=max_bytes, label=config.source)
    if len(raw) > max_bytes:
        raise ValueError(f"{config.source} exceeds {max_bytes} bytes.")
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{config.source} must contain a JSON object.")
    return payload


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


__all__ = [
    "WorkspaceSettingsFile",
    "claude_settings_files",
    "project_config_file",
    "read_settings_payload",
    "settings_file_exists",
]
