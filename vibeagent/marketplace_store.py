from __future__ import annotations

from pathlib import Path

from .marketplace_acquisition import AcquiredMarketplace, acquire_marketplace
from .marketplace_manifest import read_marketplace_manifest
from .marketplace_plugin_fetch import acquire_marketplace_plugin
from .marketplace_state_ops import (
    cache_marketplace_snapshot,
    marketplace_state_entry,
    remove_marketplace_snapshot,
)
from .plugin_manifest import read_plugin_manifest
from .plugin_state import (
    PLUGIN_STORE_LOCK as _STORE_LOCK,
    read_plugin_state as _read_state,
    safe_marketplace_cache_path as _safe_marketplace_path,
    validate_plugin_name as _validate_name,
)
from .plugin_store import _install_plugin_directory
from .plugin_types import InstalledMarketplace, InstalledPlugin, MarketplaceManifest


def add_local_marketplace(project_root: Path, source_path: str) -> InstalledMarketplace:
    with acquire_marketplace(project_root, source_path, source_kind="local") as acquired:
        return _cache_acquired_marketplace(project_root, acquired)


def add_marketplace(project_root: Path, source: str) -> InstalledMarketplace:
    with acquire_marketplace(project_root, source) as acquired:
        return _cache_acquired_marketplace(project_root, acquired)


def update_marketplace(project_root: Path, name: str) -> InstalledMarketplace:
    _validate_name(name, label="Marketplace")
    with _STORE_LOCK:
        state = _read_state(project_root)
        existing = dict(marketplace_state_entry(state, name))
        source = str(existing.get("source") or "")
        source_kind = str(existing.get("source_kind") or "local")
        source_ref = str(existing["source_ref"]) if existing.get("source_ref") else None
    with acquire_marketplace(
        project_root,
        source,
        source_kind=source_kind,
        source_ref=source_ref,
    ) as acquired:
        manifest = read_marketplace_manifest(acquired.root)
        if manifest.name != name:
            raise ValueError(
                f"Updated marketplace name {manifest.name!r} does not match installed name {name!r}."
            )
        entry = cache_marketplace_snapshot(
            project_root,
            manifest,
            source=acquired.source,
            source_kind=acquired.source_kind,
            source_ref=acquired.source_ref,
            added_at=str(existing.get("added_at") or "") or None,
            expected_source=(source, source_kind, source_ref),
        )
        return _installed_marketplace(entry)


def remove_marketplace(project_root: Path, name: str) -> InstalledMarketplace:
    return _installed_marketplace(remove_marketplace_snapshot(project_root, name))


def install_marketplace_plugin(project_root: Path, qualified_name: str) -> InstalledPlugin:
    plugin_name, marketplace_name = parse_qualified_plugin_name(qualified_name)
    manifest = read_installed_marketplace_manifest(project_root, marketplace_name)
    plugin = next((item for item in manifest.plugins if item.name == plugin_name), None)
    if plugin is None:
        available = ", ".join(item.name for item in manifest.plugins) or "none"
        raise ValueError(
            f"Plugin {plugin_name!r} is not in marketplace {marketplace_name!r}; available: {available}."
        )
    with acquire_marketplace_plugin(project_root, plugin) as source:
        fetched_manifest = read_plugin_manifest(source)
        if fetched_manifest.name != plugin_name:
            raise ValueError(
                f"Remote plugin manifest name {fetched_manifest.name!r} does not match "
                f"marketplace entry {plugin_name!r}."
            )
        return _install_plugin_directory(
            project_root,
            source,
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
                source_kind=str(value.get("source_kind") or "local"),
                source_ref=(str(value["source_ref"]) if value.get("source_ref") else None),
                error=str(error),
            )
        installed.append(item)
    return sorted(installed, key=lambda marketplace: marketplace.name)


def read_installed_marketplace_manifest(project_root: Path, name: str) -> MarketplaceManifest:
    _validate_name(name, label="Marketplace")
    with _STORE_LOCK:
        state = _read_state(project_root)
        entry = marketplace_state_entry(state, name)
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


def _installed_marketplace(entry: dict[str, object]) -> InstalledMarketplace:
    return InstalledMarketplace(
        name=str(entry.get("name") or ""),
        description=str(entry.get("description") or ""),
        owner=str(entry.get("owner") or ""),
        source=str(entry.get("source") or ""),
        cache_path=str(entry.get("cache_path") or ""),
        added_at=str(entry.get("added_at") or ""),
        plugin_count=int(entry.get("plugin_count") or 0),
        source_kind=str(entry.get("source_kind") or "local"),
        source_ref=(str(entry["source_ref"]) if entry.get("source_ref") else None),
    )


def _cache_acquired_marketplace(
    project_root: Path,
    acquired: AcquiredMarketplace,
) -> InstalledMarketplace:
    manifest = read_marketplace_manifest(acquired.root)
    entry = cache_marketplace_snapshot(
        project_root,
        manifest,
        source=acquired.source,
        source_kind=acquired.source_kind,
        source_ref=acquired.source_ref,
    )
    return _installed_marketplace(entry)


def update_local_marketplace(project_root: Path, name: str) -> InstalledMarketplace:
    return update_marketplace(project_root, name)


__all__ = [
    "add_marketplace",
    "add_local_marketplace",
    "install_marketplace_plugin",
    "list_installed_marketplaces",
    "parse_qualified_plugin_name",
    "read_installed_marketplace_manifest",
    "remove_marketplace",
    "update_local_marketplace",
    "update_marketplace",
]
