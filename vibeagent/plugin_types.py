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
    lsp_files: tuple[Path, ...]
    bin_files: tuple[Path, ...]
    monitor_files: tuple[Path, ...]
    inline_lsp_servers: dict[str, object] | None = None
    inline_monitors: tuple[object, ...] | None = None
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
                self.lsp_files,
                self.bin_files,
                self.monitor_files,
            )
        ) + (1 if self.inline_lsp_servers is not None else 0) + len(
            self.inline_monitors or ()
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
    marketplace: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class MarketplacePlugin:
    name: str
    source: str
    source_kind: str
    path: Path | None
    url: str | None
    ref: str | None
    sha: str | None
    subdirectory: str | None
    description: str
    version: str | None


@dataclass(frozen=True)
class MarketplaceManifest:
    name: str
    description: str
    owner: str
    root: Path
    manifest_path: Path
    plugins: tuple[MarketplacePlugin, ...]


@dataclass(frozen=True)
class InstalledMarketplace:
    name: str
    description: str
    owner: str
    source: str
    cache_path: str
    added_at: str
    plugin_count: int
    source_kind: str = "local"
    source_ref: str | None = None
    error: str | None = None


__all__ = [
    "InstalledMarketplace",
    "InstalledPlugin",
    "MarketplaceManifest",
    "MarketplacePlugin",
    "PluginManifest",
]
