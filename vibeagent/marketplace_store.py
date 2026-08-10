from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from .marketplace_manifest import read_marketplace_manifest
from .plugin_installation import copy_plugin_tree, remove_plugin_tree
from .plugin_state import (
    PLUGIN_STORE_LOCK as _STORE_LOCK,
    ensure_directory as _ensure_directory,
    plugins_root as _plugins_root,
    read_plugin_state as _read_state,
    safe_marketplace_cache_path as _safe_marketplace_path,
    safe_plugin_cache_path as _safe_plugin_path,
    state_timestamp as _timestamp,
    validate_plugin_name as _validate_name,
    write_plugin_state as _write_state,
)
from .plugin_store import _install_plugin_directory
from .plugin_types import InstalledMarketplace, InstalledPlugin, MarketplaceManifest
from .workspace_resolve import resolve_mutation_path


def add_local_marketplace(project_root: Path, source_path: str) -> InstalledMarketplace:
    source = resolve_mutation_path(project_root, source_path)
    manifest = read_marketplace_manifest(source)
    source_label = source.relative_to(project_root.resolve()).as_posix()
    return _cache_marketplace(project_root, manifest, source_label=source_label)


def update_local_marketplace(project_root: Path, name: str) -> InstalledMarketplace:
    _validate_name(name, label="Marketplace")
    with _STORE_LOCK:
        state = _read_state(project_root)
        existing = _marketplace_entry(state, name)
        source_label = str(existing.get("source") or "")
        source = resolve_mutation_path(project_root, source_label)
        manifest = read_marketplace_manifest(source)
        if manifest.name != name:
            raise ValueError(
                f"Updated marketplace name {manifest.name!r} does not match installed name {name!r}."
            )
        return _cache_marketplace(
            project_root,
            manifest,
            source_label=source_label,
            added_at=str(existing.get("added_at") or "") or None,
        )


def remove_marketplace(project_root: Path, name: str) -> InstalledMarketplace:
    _validate_name(name, label="Marketplace")
    with _STORE_LOCK:
        state = _read_state(project_root)
        entry = _marketplace_entry(state, name)
        installed = _installed_marketplace(entry)
        marketplace_path = _safe_marketplace_path(
            project_root,
            str(entry.get("cache_path") or ""),
            name,
        )
        plugins = state["plugins"]
        marketplaces = state["marketplaces"]
        assert isinstance(plugins, dict)
        assert isinstance(marketplaces, dict)
        plugin_names = sorted(
            plugin_name
            for plugin_name, plugin_entry in plugins.items()
            if isinstance(plugin_name, str)
            and isinstance(plugin_entry, dict)
            and plugin_entry.get("marketplace") == name
        )
        for plugin_name in plugin_names:
            _validate_name(plugin_name)
        paths = [
            _safe_plugin_path(
                project_root,
                str(plugins[plugin_name].get("cache_path") or ""),
                plugin_name,
            )
            for plugin_name in plugin_names
        ]
        paths.append(marketplace_path)
        moved: list[tuple[Path, Path]] = []
        try:
            for path in paths:
                if not path.exists():
                    continue
                trash = path.parent / f".{path.name}.remove-{uuid4().hex[:8]}"
                path.replace(trash)
                moved.append((path, trash))
            for plugin_name in plugin_names:
                del plugins[plugin_name]
            del marketplaces[name]
            _write_state(project_root, state)
        except Exception:
            for path, trash in reversed(moved):
                if trash.exists() and not path.exists():
                    trash.replace(path)
            raise
        for _path, trash in moved:
            if trash.exists():
                remove_plugin_tree(trash)
        return installed


def install_marketplace_plugin(project_root: Path, qualified_name: str) -> InstalledPlugin:
    plugin_name, marketplace_name = parse_qualified_plugin_name(qualified_name)
    with _STORE_LOCK:
        manifest = read_installed_marketplace_manifest(project_root, marketplace_name)
        plugin = next((item for item in manifest.plugins if item.name == plugin_name), None)
        if plugin is None:
            available = ", ".join(item.name for item in manifest.plugins) or "none"
            raise ValueError(
                f"Plugin {plugin_name!r} is not in marketplace {marketplace_name!r}; available: {available}."
            )
        return _install_plugin_directory(
            project_root,
            plugin.path,
            source_label=qualified_name,
            marketplace=marketplace_name,
        )


def list_installed_marketplaces(project_root: Path) -> list[InstalledMarketplace]:
    with _STORE_LOCK:
        state = _read_state(project_root)
    marketplaces = state.get("marketplaces", {})
    assert isinstance(marketplaces, dict)
    installed: list[InstalledMarketplace] = []
    for name, value in marketplaces.items():
        if not isinstance(name, str) or not isinstance(value, dict):
            continue
        try:
            item = _installed_marketplace(value)
            _validate_name(item.name, label="Marketplace")
            path = _safe_marketplace_path(project_root, item.cache_path, item.name)
            manifest = read_marketplace_manifest(path)
            if manifest.name != item.name:
                raise ValueError("cached marketplace name does not match installed state")
        except (OSError, UnicodeError, ValueError) as error:
            item = InstalledMarketplace(
                name=name,
                description=str(value.get("description") or ""),
                owner=str(value.get("owner") or ""),
                source=str(value.get("source") or ""),
                cache_path=str(value.get("cache_path") or ""),
                added_at=str(value.get("added_at") or ""),
                plugin_count=int(value.get("plugin_count") or 0),
                error=str(error),
            )
        installed.append(item)
    return sorted(installed, key=lambda marketplace: marketplace.name)


def read_installed_marketplace_manifest(project_root: Path, name: str) -> MarketplaceManifest:
    _validate_name(name, label="Marketplace")
    with _STORE_LOCK:
        state = _read_state(project_root)
        entry = _marketplace_entry(state, name)
        path = _safe_marketplace_path(
            project_root,
            str(entry.get("cache_path") or ""),
            name,
        )
    manifest = read_marketplace_manifest(path)
    if manifest.name != name:
        raise ValueError(f"Cached marketplace manifest name mismatch: {name}")
    return manifest


def parse_qualified_plugin_name(value: str) -> tuple[str, str]:
    if value.count("@") != 1:
        raise ValueError("Marketplace plugin must use plugin-name@marketplace-name.")
    plugin_name, marketplace_name = value.split("@", 1)
    _validate_name(plugin_name)
    _validate_name(marketplace_name, label="Marketplace")
    return plugin_name, marketplace_name


def _cache_marketplace(
    project_root: Path,
    manifest: MarketplaceManifest,
    *,
    source_label: str,
    added_at: str | None = None,
) -> InstalledMarketplace:
    root = _plugins_root(project_root, create=True)
    cache_root = root / "marketplaces"
    _ensure_directory(cache_root, create=True)
    destination = cache_root / manifest.name
    if destination.is_symlink():
        raise ValueError(f"Marketplace cache destination must not be a symbolic link: {manifest.name}")
    staging = cache_root / f".{manifest.name}.install-{uuid4().hex[:8]}"
    backup = cache_root / f".{manifest.name}.backup-{uuid4().hex[:8]}"
    copy_plugin_tree(manifest.root, staging)

    with _STORE_LOCK:
        state = _read_state(project_root)
        marketplaces = state["marketplaces"]
        assert isinstance(marketplaces, dict)
        existing = marketplaces.get(manifest.name)
        try:
            if destination.exists():
                destination.replace(backup)
            staging.replace(destination)
            installed_manifest = read_marketplace_manifest(destination)
            if installed_manifest.name != manifest.name:
                raise ValueError("Marketplace identity changed while copying the install source.")
            entry = {
                "name": installed_manifest.name,
                "description": installed_manifest.description,
                "owner": installed_manifest.owner,
                "source": source_label,
                "cache_path": destination.relative_to(project_root.resolve()).as_posix(),
                "added_at": added_at
                or (str(existing.get("added_at") or "") if isinstance(existing, dict) else "")
                or _timestamp(),
                "plugin_count": len(installed_manifest.plugins),
            }
            marketplaces[manifest.name] = entry
            _write_state(project_root, state)
        except Exception:
            if destination.exists() and not backup.exists():
                remove_plugin_tree(destination)
            if backup.exists():
                if destination.exists():
                    remove_plugin_tree(destination)
                backup.replace(destination)
            raise
        finally:
            if staging.exists():
                remove_plugin_tree(staging)
            if backup.exists():
                remove_plugin_tree(backup)
    return _installed_marketplace(entry)


def _marketplace_entry(state: dict[str, object], name: str) -> dict[str, object]:
    marketplaces = state.get("marketplaces")
    if not isinstance(marketplaces, dict) or not isinstance(marketplaces.get(name), dict):
        raise ValueError(f"Marketplace is not installed: {name}")
    entry = marketplaces[name]
    if entry.get("name") != name:
        raise ValueError(f"Marketplace state identity mismatch: {name}")
    return entry


def _installed_marketplace(entry: dict[str, object]) -> InstalledMarketplace:
    return InstalledMarketplace(
        name=str(entry.get("name") or ""),
        description=str(entry.get("description") or ""),
        owner=str(entry.get("owner") or ""),
        source=str(entry.get("source") or ""),
        cache_path=str(entry.get("cache_path") or ""),
        added_at=str(entry.get("added_at") or ""),
        plugin_count=int(entry.get("plugin_count") or 0),
    )


__all__ = [
    "add_local_marketplace",
    "install_marketplace_plugin",
    "list_installed_marketplaces",
    "parse_qualified_plugin_name",
    "read_installed_marketplace_manifest",
    "remove_marketplace",
    "update_local_marketplace",
]
