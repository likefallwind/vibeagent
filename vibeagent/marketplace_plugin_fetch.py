from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from uuid import uuid4

from .plugin_installation import remove_plugin_tree
from .plugin_npm_sources import download_npm_plugin
from .plugin_remote_sources import clone_remote_git
from .plugin_state import ensure_directory, plugins_root
from .plugin_types import MarketplacePlugin
from .workspace_metadata_files import has_symlink_component


@contextmanager
def acquire_marketplace_plugin(
    project_root: Path,
    plugin: MarketplacePlugin,
) -> Iterator[Path]:
    if plugin.source_kind == "relative":
        if plugin.path is None:
            raise ValueError(f"Relative plugin source is missing its cached path: {plugin.name}")
        yield plugin.path
        return
    fetch_root = plugins_root(project_root, create=True) / "fetches"
    ensure_directory(fetch_root, create=True)
    temporary = fetch_root / f".plugin-{plugin.name}-{uuid4().hex[:12]}"
    try:
        if plugin.source_kind == "npm":
            if plugin.npm_package is None:
                raise ValueError(f"npm plugin source is missing its package name: {plugin.name}")
            download_npm_plugin(
                plugin.npm_package,
                temporary,
                version=plugin.npm_version,
                registry=plugin.npm_registry,
            )
            selected = temporary
        else:
            if plugin.url is None:
                raise ValueError(f"Remote plugin source is missing its Git URL: {plugin.name}")
            clone_remote_git(plugin.url, temporary, ref=plugin.ref, sha=plugin.sha)
            selected = temporary / plugin.subdirectory if plugin.subdirectory else temporary
        if has_symlink_component(temporary, selected):
            raise ValueError(f"Remote plugin subdirectory contains a symbolic link: {plugin.name}")
        selected = selected.resolve()
        if selected != temporary and temporary not in selected.parents:
            raise ValueError(f"Remote plugin subdirectory escapes its checkout: {plugin.name}")
        if not selected.is_dir():
            raise ValueError(f"Remote plugin directory does not exist: {plugin.subdirectory}")
        yield selected
    finally:
        if temporary.exists():
            remove_plugin_tree(temporary)


__all__ = ["acquire_marketplace_plugin"]
