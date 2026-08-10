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
from .plugin_locations import (
    plugin_storage_root,
    resolve_marketplace_storage_root as _resolve_marketplace_storage_root,
    resolve_plugin_storage_root,
    user_home,
)
from .plugin_scope_settings import PluginScope
from .plugin_state import (
    PLUGIN_STORE_LOCK as _STORE_LOCK,
    read_plugin_state as _read_state,
    safe_marketplace_cache_path as _safe_marketplace_path,
    validate_plugin_name as _validate_name,
    write_plugin_state as _write_state,
)
from .plugin_store import _install_plugin_directory, read_installed_plugin
from .plugin_types import (
    InstalledMarketplace,
    InstalledPlugin,
    MarketplaceManifest,
    PluginUpdateResult,
)


def add_local_marketplace(
    project_root: Path,
    source_path: str,
    *,
    scope: PluginScope | None = None,
) -> InstalledMarketplace:
    store = plugin_storage_root(project_root, scope)
    with acquire_marketplace(
        project_root,
        source_path,
        source_kind="local",
        storage_root=store,
    ) as acquired:
        return _cache_acquired_marketplace(store, acquired)


def add_marketplace(
    project_root: Path,
    source: str,
    *,
    scope: PluginScope | None = None,
) -> InstalledMarketplace:
    store = plugin_storage_root(project_root, scope)
    with acquire_marketplace(project_root, source, storage_root=store) as acquired:
        return _cache_acquired_marketplace(store, acquired)


def update_marketplace(
    project_root: Path,
    name: str,
    *,
    scope: PluginScope | None = None,
) -> InstalledMarketplace:
    _validate_name(name, label="Marketplace")
    store = _resolve_marketplace_storage_root(project_root, name, scope)
    with _STORE_LOCK:
        state = _read_state(store)
        existing = dict(marketplace_state_entry(state, name))
        source = str(existing.get("source") or "")
        source_kind = str(existing.get("source_kind") or "local")
        source_ref = str(existing["source_ref"]) if existing.get("source_ref") else None
    with acquire_marketplace(
        project_root,
        source,
        source_kind=source_kind,
        source_ref=source_ref,
        storage_root=store,
    ) as acquired:
        manifest = read_marketplace_manifest(acquired.root)
        if manifest.name != name:
            raise ValueError(
                f"Updated marketplace name {manifest.name!r} does not match installed name {name!r}."
            )
        entry = cache_marketplace_snapshot(
            store,
            manifest,
            source=acquired.source,
            source_kind=acquired.source_kind,
            source_ref=acquired.source_ref,
            added_at=str(existing.get("added_at") or "") or None,
            expected_source=(source, source_kind, source_ref),
        )
        return _installed_marketplace(entry, scope=_store_scope(store))


def remove_marketplace(
    project_root: Path,
    name: str,
    *,
    scope: PluginScope | None = None,
) -> InstalledMarketplace:
    store = _resolve_marketplace_storage_root(project_root, name, scope)
    return _installed_marketplace(
        remove_marketplace_snapshot(store, name),
        scope=_store_scope(store),
    )


def install_marketplace_plugin(
    project_root: Path,
    qualified_name: str,
    *,
    scope: PluginScope | None = None,
) -> InstalledPlugin:
    plugin_name, marketplace_name = parse_qualified_plugin_name(qualified_name)
    store = _resolve_marketplace_storage_root(project_root, marketplace_name, scope)
    manifest = _read_installed_marketplace_manifest_from_store(store, marketplace_name)
    plugin = next((item for item in manifest.plugins if item.name == plugin_name), None)
    if plugin is None:
        available = ", ".join(item.name for item in manifest.plugins) or "none"
        raise ValueError(
            f"Plugin {plugin_name!r} is not in marketplace {marketplace_name!r}; available: {available}."
        )
    with acquire_marketplace_plugin(store, plugin) as source:
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
            resolved_version=fetched_manifest.version or plugin.version,
            scope=scope,
            storage_root=store,
        )


def update_marketplace_plugin(
    project_root: Path,
    name: str,
    *,
    current: InstalledPlugin | None = None,
    scope: PluginScope | None = None,
) -> PluginUpdateResult:
    store = resolve_plugin_storage_root(project_root, name, scope)
    current = current or read_installed_plugin(project_root, name)
    if current.marketplace is None:
        raise ValueError(f"Plugin {name} was not installed from a marketplace.")
    manifest = _read_installed_marketplace_manifest_from_store(store, current.marketplace)
    plugin = next((item for item in manifest.plugins if item.name == name), None)
    if plugin is None:
        raise ValueError(
            f"Plugin {name!r} is no longer in marketplace {current.marketplace!r}."
        )
    with acquire_marketplace_plugin(store, plugin) as source:
        fetched_manifest = read_plugin_manifest(source)
        if fetched_manifest.name != name:
            raise ValueError(
                f"Remote plugin manifest name {fetched_manifest.name!r} does not match "
                f"marketplace entry {name!r}."
            )
        resolved_version = fetched_manifest.version or plugin.version
        if resolved_version is not None and resolved_version == current.version:
            return PluginUpdateResult(
                current,
                updated=False,
                previous_version=current.version,
            )
        updated = _install_plugin_directory(
            project_root,
            source,
            source_label=f"{name}@{current.marketplace}",
            marketplace=current.marketplace,
            resolved_version=resolved_version,
            expected_plugin=(current.source, current.marketplace, current.version),
            storage_root=store,
        )
    return PluginUpdateResult(updated, updated=True, previous_version=current.version)


def set_marketplace_auto_update(
    project_root: Path,
    name: str,
    enabled: bool,
    *,
    scope: PluginScope | None = None,
) -> InstalledMarketplace:
    _validate_name(name, label="Marketplace")
    store = _resolve_marketplace_storage_root(project_root, name, scope)
    with _STORE_LOCK:
        state = _read_state(store)
        entry = marketplace_state_entry(state, name)
        entry["auto_update"] = enabled
        _write_state(store, state)
        return _installed_marketplace(entry, scope=_store_scope(store))


def list_installed_marketplaces(
    project_root: Path,
    *,
    scope: PluginScope | None = None,
) -> list[InstalledMarketplace]:
    project = project_root.resolve()
    if scope == "user":
        return _list_installed_marketplaces_from_store(user_home())
    if scope in {"local", "project"}:
        return _list_installed_marketplaces_from_store(project)
    project_items = _list_installed_marketplaces_from_store(project)
    user_items = _list_installed_marketplaces_from_store(user_home())
    merged = {item.name: item for item in user_items}
    merged.update({item.name: item for item in project_items})
    return sorted(merged.values(), key=lambda marketplace: marketplace.name)


def _list_installed_marketplaces_from_store(store: Path) -> list[InstalledMarketplace]:
    with _STORE_LOCK:
        state = _read_state(store)
    marketplaces = state.get("marketplaces", {})
    assert isinstance(marketplaces, dict)
    installed: list[InstalledMarketplace] = []
    for name, value in marketplaces.items():
        if not isinstance(name, str) or not isinstance(value, dict):
            continue
        try:
            item = _installed_marketplace(value, scope=_store_scope(store))
            _validate_name(item.name, label="Marketplace")
            path = _safe_marketplace_path(store, item.cache_path, item.name)
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
                auto_update=bool(value.get("auto_update", False)),
                error=str(error),
                scope=_store_scope(store),
            )
        installed.append(item)
    return sorted(installed, key=lambda marketplace: marketplace.name)


def read_installed_marketplace_manifest(
    project_root: Path,
    name: str,
    *,
    scope: PluginScope | None = None,
) -> MarketplaceManifest:
    store = _resolve_marketplace_storage_root(project_root, name, scope)
    return _read_installed_marketplace_manifest_from_store(store, name)


def _read_installed_marketplace_manifest_from_store(
    store: Path,
    name: str,
) -> MarketplaceManifest:
    _validate_name(name, label="Marketplace")
    with _STORE_LOCK:
        state = _read_state(store)
        entry = marketplace_state_entry(state, name)
        path = _safe_marketplace_path(
            store,
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


def _installed_marketplace(
    entry: dict[str, object],
    *,
    scope: str = "project",
) -> InstalledMarketplace:
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
        auto_update=bool(entry.get("auto_update", False)),
        scope=scope,
    )


def _cache_acquired_marketplace(
    store: Path,
    acquired: AcquiredMarketplace,
) -> InstalledMarketplace:
    manifest = read_marketplace_manifest(acquired.root)
    entry = cache_marketplace_snapshot(
        store,
        manifest,
        source=acquired.source,
        source_kind=acquired.source_kind,
        source_ref=acquired.source_ref,
    )
    return _installed_marketplace(entry, scope=_store_scope(store))


def update_local_marketplace(project_root: Path, name: str) -> InstalledMarketplace:
    return update_marketplace(project_root, name)


def _store_scope(store: Path) -> str:
    return "user" if store.resolve() == user_home() else "project"


__all__ = [
    "add_marketplace",
    "add_local_marketplace",
    "install_marketplace_plugin",
    "list_installed_marketplaces",
    "parse_qualified_plugin_name",
    "read_installed_marketplace_manifest",
    "remove_marketplace",
    "set_marketplace_auto_update",
    "update_local_marketplace",
    "update_marketplace",
    "update_marketplace_plugin",
]
