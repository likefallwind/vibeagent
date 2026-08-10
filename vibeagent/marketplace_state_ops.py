from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from .marketplace_manifest import read_marketplace_manifest
from .plugin_installation import copy_plugin_tree, remove_plugin_tree
from .plugin_scope_settings import (
    restore_plugin_settings,
    write_plugin_enabled_setting,
)
from .plugin_scoped_state import plugin_entry_scopes
from .plugin_state import (
    PLUGIN_STORE_LOCK,
    ensure_directory,
    plugins_root,
    read_plugin_state,
    safe_marketplace_cache_path,
    safe_plugin_cache_path,
    state_timestamp,
    validate_plugin_name,
    write_plugin_state as _write_state,
)
from .plugin_types import MarketplaceManifest


def cache_marketplace_snapshot(
    project_root: Path,
    manifest: MarketplaceManifest,
    *,
    source: str,
    source_kind: str,
    source_ref: str | None,
    added_at: str | None = None,
    expected_source: tuple[str, str, str | None] | None = None,
) -> dict[str, object]:
    root = plugins_root(project_root, create=True)
    cache_root = root / "marketplaces"
    ensure_directory(cache_root, create=True)
    destination = cache_root / manifest.name
    if destination.is_symlink():
        raise ValueError(f"Marketplace cache destination must not be a symbolic link: {manifest.name}")
    staging = cache_root / f".{manifest.name}.install-{uuid4().hex[:8]}"
    backup = cache_root / f".{manifest.name}.backup-{uuid4().hex[:8]}"
    copy_plugin_tree(manifest.root, staging)

    with PLUGIN_STORE_LOCK:
        state = read_plugin_state(project_root)
        marketplaces = state["marketplaces"]
        assert isinstance(marketplaces, dict)
        existing = marketplaces.get(manifest.name)
        try:
            _verify_expected_source(existing, expected_source)
            if destination.exists():
                destination.replace(backup)
            staging.replace(destination)
            installed_manifest = read_marketplace_manifest(destination)
            if installed_manifest.name != manifest.name:
                raise ValueError("Marketplace identity changed while copying the install source.")
            entry: dict[str, object] = {
                "name": installed_manifest.name,
                "description": installed_manifest.description,
                "owner": installed_manifest.owner,
                "source": source,
                "source_kind": source_kind,
                "source_ref": source_ref,
                "cache_path": destination.relative_to(project_root.resolve()).as_posix(),
                "added_at": added_at
                or (str(existing.get("added_at") or "") if isinstance(existing, dict) else "")
                or state_timestamp(),
                "plugin_count": len(installed_manifest.plugins),
                "auto_update": (
                    bool(existing.get("auto_update", False))
                    if isinstance(existing, dict)
                    else False
                ),
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
    return entry


def remove_marketplace_snapshot(project_root: Path, name: str) -> dict[str, object]:
    validate_plugin_name(name, label="Marketplace")
    with PLUGIN_STORE_LOCK:
        state = read_plugin_state(project_root)
        entry = dict(marketplace_state_entry(state, name))
        marketplace_path = safe_marketplace_cache_path(
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
            validate_plugin_name(plugin_name)
        paths = [
            safe_plugin_cache_path(
                project_root,
                str(plugins[plugin_name].get("cache_path") or ""),
                plugin_name,
            )
            for plugin_name in plugin_names
        ]
        paths.append(marketplace_path)
        moved: list[tuple[Path, Path]] = []
        settings_snapshots = []
        try:
            for plugin_name in plugin_names:
                for scope in sorted(plugin_entry_scopes(plugins[plugin_name])):
                    settings_snapshots.append(
                        write_plugin_enabled_setting(
                            project_root,
                            scope,
                            f"{plugin_name}@{name}",
                            None,
                        )
                    )
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
            for snapshot in reversed(settings_snapshots):
                restore_plugin_settings(snapshot)
            raise
        for _path, trash in moved:
            if trash.exists():
                remove_plugin_tree(trash)
    return entry


def marketplace_state_entry(state: dict[str, object], name: str) -> dict[str, object]:
    marketplaces = state.get("marketplaces")
    if not isinstance(marketplaces, dict) or not isinstance(marketplaces.get(name), dict):
        raise ValueError(f"Marketplace is not installed: {name}")
    entry = marketplaces[name]
    if entry.get("name") != name:
        raise ValueError(f"Marketplace state identity mismatch: {name}")
    return entry


def _verify_expected_source(
    existing: object,
    expected: tuple[str, str, str | None] | None,
) -> None:
    if expected is None:
        return
    current = (
        str(existing.get("source") or "") if isinstance(existing, dict) else "",
        str(existing.get("source_kind") or "local") if isinstance(existing, dict) else "",
        str(existing["source_ref"])
        if isinstance(existing, dict) and existing.get("source_ref")
        else None,
    )
    if current != expected:
        raise ValueError("Marketplace source changed while its update was downloading.")


__all__ = [
    "cache_marketplace_snapshot",
    "marketplace_state_entry",
    "remove_marketplace_snapshot",
]
