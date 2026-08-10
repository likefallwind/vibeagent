from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PluginManifest:
    name: str
    description: str
    version: str | None
    default_enabled: bool
    root: Path
    manifest_path: Path | None
    skill_files: tuple[Path, ...]
    command_files: tuple[Path, ...]
    agent_files: tuple[Path, ...]
    hook_files: tuple[Path, ...]
    mcp_files: tuple[Path, ...]
    warnings: tuple[str, ...] = ()

    @property
    def component_count(self) -> int:
        return sum(
            len(items)
            for items in (
                self.skill_files,
                self.command_files,
                self.agent_files,
                self.hook_files,
                self.mcp_files,
            )
        )


@dataclass(frozen=True)
class InstalledPlugin:
    name: str
    description: str
    version: str | None
    enabled: bool
    source: str
    cache_path: str
    installed_at: str
    component_count: int
    error: str | None = None


__all__ = ["InstalledPlugin", "PluginManifest"]
