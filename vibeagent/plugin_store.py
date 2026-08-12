from __future__ import annotations

from pathlib import Path
from typing import Any, TYPE_CHECKING
from uuid import uuid4

from .plugin_installation import copy_plugin_tree, remove_plugin_tree
from .plugin_locations import (
    plugin_storage_root,
    resolve_plugin_storage_root as _resolve_plugin_storage_root,
    user_home,
)
from .plugin_manifest import read_plugin_manifest
from .plugin_scope_settings import (
    PluginScope,
    restore_plugin_settings,
    write_plugin_enabled_setting,
)
from .plugin_scoped_state import (
    effective_installed_plugin as _effective_installed_plugin,
    plugin_entry_scopes as _entry_scopes,
    qualified_plugin_id as _plugin_id,
    safe_plugin_scope_names as _safe_entry_scope_names,
)
from .plugin_state import (
    PLUGIN_STORE_LOCK as _STORE_LOCK,
    ensure_directory as _ensure_directory,
    plugins_root as _plugins_root,
    read_plugin_state as _read_state,
    safe_plugin_cache_path as _safe_cache_path,
    state_timestamp as _timestamp,
    validate_plugin_name as _validate_name,
    write_plugin_state as _write_state,
)
from .plugin_types import InstalledPlugin, PluginManifest, PluginUpdateResult
from .workspace_resolve import resolve_mutation_path

if TYPE_CHECKING:
    from .workspace_core import RunWorkspace


def install_local_plugin(
    project_root: Path,
    source_path: str,
    *,
    scope: PluginScope | None = None,
) -> InstalledPlugin:
    source = resolve_mutation_path(project_root, source_path)
    source_label = (
        source.as_posix()
        if scope == "user"
        else source.relative_to(project_root.resolve()).as_posix()
    )
    return _install_plugin_directory(
        project_root,
        source,
        source_label=source_label,
        scope=scope,
    )


def _install_plugin_directory(
    project_root: Path,
    source: Path,
    *,
    source_label: str,
    marketplace: str | None = None,
    resolved_version: str | None = None,
    expected_plugin: tuple[str, str | None, str | None] | None = None,
    scope: PluginScope | None = None,
    storage_root: Path | None = None,
) -> InstalledPlugin:
    manifest = read_plugin_manifest(source)
    store = (storage_root or plugin_storage_root(project_root, scope)).resolve()
    root = _plugins_root(store, create=True)
    cache_root = root / "cache"
    _ensure_directory(cache_root, create=True)
    destination = cache_root / manifest.name
    if destination.is_symlink():
        raise ValueError(f"Plugin cache destination must not be a symbolic link: {manifest.name}")
    staging = cache_root / f".{manifest.name}.install-{uuid4().hex[:8]}"
    backup = cache_root / f".{manifest.name}.backup-{uuid4().hex[:8]}"
    copy_plugin_tree(source, staging)

    with _STORE_LOCK:
        settings_snapshot = None
        state = _read_state(store)
        existing_plugins = state.get("plugins", {})
        existing_entry = existing_plugins.get(manifest.name) if isinstance(existing_plugins, dict) else None
        try:
            _verify_expected_plugin(existing_entry, expected_plugin)
            existing_scopes = _entry_scopes(existing_entry)
            _validate_scope_storage(store, existing_scopes)
            existing_marketplace = (
                str(existing_entry["marketplace"])
                if isinstance(existing_entry, dict) and existing_entry.get("marketplace")
                else None
            )
            if existing_scopes and existing_marketplace != marketplace:
                raise ValueError(
                    f"Plugin {manifest.name} is installed from a different source; "
                    "uninstall its scoped declarations first."
                )
            if marketplace is not None:
                marketplaces = state.get("marketplaces")
                if not isinstance(marketplaces, dict) or marketplace not in marketplaces:
                    raise ValueError(f"Marketplace was removed during plugin installation: {marketplace}")
            if destination.exists():
                destination.replace(backup)
            staging.replace(destination)
            installed_manifest = read_plugin_manifest(destination)
            if installed_manifest.name != manifest.name:
                raise ValueError("Plugin identity changed while copying the install source.")
            enabled = (
                existing_scopes[scope]
                if scope is not None and scope in existing_scopes
                else (
                    bool(existing_entry.get("enabled"))
                    if isinstance(existing_entry, dict)
                    else installed_manifest.default_enabled
                )
            )
            if enabled and installed_manifest.user_config:
                from .plugin_user_config import resolve_plugin_user_config

                plugin_id = (
                    f"{installed_manifest.name}@{marketplace}"
                    if marketplace is not None
                    else installed_manifest.name
                )
                configured = resolve_plugin_user_config(
                    project_root,
                    installed_manifest,
                    plugin_id=plugin_id,
                )
                if configured.missing_required:
                    enabled = False
            scopes = existing_scopes
            if scope is not None:
                scopes[scope] = enabled
            entry = {
                "name": installed_manifest.name,
                "description": installed_manifest.description,
                "version": resolved_version or installed_manifest.version,
                "enabled": enabled,
                "source": source_label,
                "cache_path": destination.relative_to(store).as_posix(),
                "installed_at": _timestamp(),
                "component_count": installed_manifest.component_count,
                "marketplace": marketplace,
                "scopes": scopes,
            }
            plugins = state.setdefault("plugins", {})
            if not isinstance(plugins, dict):
                raise ValueError("Plugin state plugins field is invalid.")
            plugins[manifest.name] = entry
            if scope is not None:
                settings_snapshot = write_plugin_enabled_setting(
                    project_root,
                    scope,
                    _plugin_id(installed_manifest.name, marketplace),
                    enabled,
                )
            _write_state(store, state)
        except Exception:
            if destination.exists() and not backup.exists():
                remove_plugin_tree(destination)
            if backup.exists():
                if destination.exists():
                    remove_plugin_tree(destination)
                backup.replace(destination)
            if settings_snapshot is not None:
                restore_plugin_settings(settings_snapshot)
            raise
        finally:
            if staging.exists():
                remove_plugin_tree(staging)
            if backup.exists():
                remove_plugin_tree(backup)
    return _effective_installed_plugin(project_root, _installed_plugin(entry))


def update_installed_plugin(
    project_root: Path,
    name: str,
    *,
    scope: PluginScope | None = None,
) -> PluginUpdateResult:
    store = _resolve_plugin_storage_root(project_root, name, scope)
    current = _read_installed_plugin_from_store(project_root, store, name)
    if scope is not None and scope not in current.scopes:
        raise ValueError(f"Plugin {name} is not installed at {scope} scope.")
    if current.marketplace is not None:
        from .marketplace_store import update_marketplace, update_marketplace_plugin

        marketplace_scope: PluginScope | None = "user" if store == user_home() else None
        update_marketplace(project_root, current.marketplace, scope=marketplace_scope)
        return update_marketplace_plugin(
            project_root,
            name,
            current=current,
            scope=marketplace_scope,
        )
    source = (
        Path(current.source).resolve()
        if store == user_home()
        else resolve_mutation_path(project_root, current.source)
    )
    manifest = read_plugin_manifest(source)
    if manifest.name != name:
        raise ValueError(
            f"Updated plugin name {manifest.name!r} does not match installed name {name!r}."
        )
    if manifest.version is not None and manifest.version == current.version:
        return PluginUpdateResult(current, updated=False, previous_version=current.version)
    updated = _install_plugin_directory(
        project_root,
        source,
        source_label=current.source,
        expected_plugin=(current.source, None, current.version),
        storage_root=store,
    )
    return PluginUpdateResult(updated, updated=True, previous_version=current.version)


def set_plugin_enabled(
    project_root: Path,
    name: str,
    enabled: bool,
    *,
    scope: PluginScope | None = None,
) -> InstalledPlugin:
    _validate_name(name)
    with _STORE_LOCK:
        store = _resolve_plugin_storage_root(project_root, name, scope)
        state = _read_state(store)
        entry = _plugin_entry(state, name)
        _validate_scope_storage(store, _entry_scopes(entry))
        snapshot = None
        if scope is None:
            if _entry_scopes(entry):
                raise ValueError(
                    f"Plugin {name} has scoped declarations; specify --scope local, project, or user."
                )
            entry["enabled"] = enabled
        else:
            scopes = _entry_scopes(entry)
            if scope not in scopes:
                raise ValueError(f"Plugin {name} is not installed at {scope} scope.")
            scopes[scope] = enabled
            entry["scopes"] = scopes
            snapshot = write_plugin_enabled_setting(
                project_root,
                scope,
                _plugin_id(name, str(entry["marketplace"]) if entry.get("marketplace") else None),
                enabled,
            )
        try:
            _write_state(store, state)
        except Exception:
            if snapshot is not None:
                restore_plugin_settings(snapshot)
            raise
        return _effective_installed_plugin(project_root, _installed_plugin(entry))


def uninstall_plugin(
    project_root: Path,
    name: str,
    *,
    scope: PluginScope | None = None,
) -> InstalledPlugin:
    _validate_name(name)
    with _STORE_LOCK:
        store = _resolve_plugin_storage_root(project_root, name, scope)
        state = _read_state(store)
        entry = _plugin_entry(state, name)
        _validate_scope_storage(store, _entry_scopes(entry))
        installed = _effective_installed_plugin(project_root, _installed_plugin(entry))
        cache_path = _safe_cache_path(store, str(entry.get("cache_path") or ""), name)
        trash_path = cache_path.parent / f".{name}.uninstall-{uuid4().hex[:8]}"
        plugins = state["plugins"]
        assert isinstance(plugins, dict)
        scopes = _entry_scopes(entry)
        selected_scopes = [scope] if scope is not None else list(scopes)
        if scope is not None and scope not in scopes:
            raise ValueError(f"Plugin {name} is not installed at {scope} scope.")
        snapshots = []
        try:
            for selected_scope in selected_scopes:
                snapshots.append(
                    write_plugin_enabled_setting(
                        project_root,
                        selected_scope,
                        _plugin_id(name, installed.marketplace),
                        None,
                    )
                )
                scopes.pop(selected_scope, None)
            if scope is not None and scopes:
                entry["scopes"] = scopes
                _write_state(store, state)
                return _effective_installed_plugin(project_root, _installed_plugin(entry))
            if cache_path.exists():
                cache_path.replace(trash_path)
            del plugins[name]
            _write_state(store, state)
        except Exception:
            if trash_path.exists():
                trash_path.replace(cache_path)
            for snapshot in reversed(snapshots):
                restore_plugin_settings(snapshot)
            raise
        if trash_path.exists():
            remove_plugin_tree(trash_path)
        return installed


def list_installed_plugins(
    project_root: Path,
    *,
    workspace: RunWorkspace | None = None,
) -> list[InstalledPlugin]:
    project = project_root.resolve()
    project_plugins = _list_installed_plugins_from_store(project, project, workspace=workspace)
    user_plugins = _list_installed_plugins_from_store(project, user_home(), workspace=workspace)
    merged = {plugin.name: plugin for plugin in user_plugins}
    merged.update({plugin.name: plugin for plugin in project_plugins})
    return sorted(merged.values(), key=lambda plugin: plugin.name)


def _list_installed_plugins_from_store(
    project_root: Path,
    store: Path,
    *,
    workspace: RunWorkspace | None = None,
) -> list[InstalledPlugin]:
    with _STORE_LOCK:
        state = _read_state(store)
    plugins = state.get("plugins", {})
    if not isinstance(plugins, dict):
        return []
    installed: list[InstalledPlugin] = []
    for name, value in plugins.items():
        if not isinstance(name, str) or not isinstance(value, dict):
            continue
        try:
            _validate_scope_storage(store, _entry_scopes(value))
            item = _installed_plugin(value)
            _validate_name(item.name)
            if item.marketplace is not None:
                _validate_name(item.marketplace, label="Marketplace")
            path = _safe_cache_path(store, item.cache_path, item.name)
            manifest = read_plugin_manifest(path)
            if manifest.name != item.name:
                raise ValueError("cached manifest name does not match installed state")
            item = _effective_installed_plugin(project_root, item, workspace=workspace)
        except (OSError, UnicodeError, ValueError) as error:
            item = InstalledPlugin(
                name=name,
                description=str(value.get("description") or ""),
                version=str(value["version"]) if value.get("version") is not None else None,
                enabled=bool(value.get("enabled", False)),
                source=str(value.get("source") or ""),
                cache_path=str(value.get("cache_path") or ""),
                installed_at=str(value.get("installed_at") or ""),
                component_count=int(value.get("component_count") or 0),
                marketplace=(str(value["marketplace"]) if value.get("marketplace") else None),
                error=str(error),
                scopes=_safe_entry_scope_names(value),
            )
        installed.append(item)
    return sorted(installed, key=lambda plugin: plugin.name)


def read_installed_plugin(
    project_root: Path,
    name: str,
    *,
    scope: PluginScope | None = None,
) -> InstalledPlugin:
    store = _resolve_plugin_storage_root(project_root, name, scope)
    return _read_installed_plugin_from_store(project_root, store, name)


def _read_installed_plugin_from_store(
    project_root: Path,
    store: Path,
    name: str,
) -> InstalledPlugin:
    _validate_name(name)
    with _STORE_LOCK:
        state = _read_state(store)
        entry = dict(_plugin_entry(state, name))
        _validate_scope_storage(store, _entry_scopes(entry))
        installed = _installed_plugin(entry)
        path = _safe_cache_path(store, installed.cache_path, name)
    manifest = read_plugin_manifest(path)
    if manifest.name != name:
        raise ValueError(f"Cached plugin manifest name mismatch: {name}")
    return _effective_installed_plugin(project_root, installed)


def read_installed_plugin_manifest(
    project_root: Path,
    name: str,
    *,
    scope: PluginScope | None = None,
) -> PluginManifest:
    store = _resolve_plugin_storage_root(project_root, name, scope)
    return _read_installed_plugin_manifest_from_store(store, name)


def _read_installed_plugin_manifest_from_store(store: Path, name: str) -> PluginManifest:
    _validate_name(name)
    with _STORE_LOCK:
        state = _read_state(store)
        entry = _plugin_entry(state, name)
        _validate_scope_storage(store, _entry_scopes(entry))
        path = _safe_cache_path(store, str(entry.get("cache_path") or ""), name)
    manifest = read_plugin_manifest(path)
    if manifest.name != name:
        raise ValueError(f"Cached plugin manifest name mismatch: {name}")
    return manifest


def enabled_plugin_manifests(
    project_root: Path,
    *,
    workspace: RunWorkspace | None = None,
) -> list[PluginManifest]:
    if workspace is not None and workspace.safe_mode:
        return []
    invocation_manifests = (
        [read_plugin_manifest(path) for path in workspace.invocation_plugin_dirs]
        if workspace is not None
        else []
    )
    invocation_names = {manifest.name for manifest in invocation_manifests}
    manifests: list[PluginManifest] = []
    for plugin in list_installed_plugins(project_root, workspace=workspace):
        if not plugin.enabled or plugin.error is not None:
            continue
        if plugin.name in invocation_names:
            continue
        try:
            store = _resolve_plugin_storage_root(project_root, plugin.name, None)
            manifests.append(_read_installed_plugin_manifest_from_store(store, plugin.name))
        except (OSError, UnicodeError, ValueError):
            continue
    manifests.extend(invocation_manifests)
    return manifests


def _plugin_entry(state: dict[str, Any], name: str) -> dict[str, Any]:
    plugins = state.get("plugins")
    if not isinstance(plugins, dict) or not isinstance(plugins.get(name), dict):
        raise ValueError(f"Plugin is not installed: {name}")
    entry = plugins[name]
    if entry.get("name") != name:
        raise ValueError(f"Plugin state identity mismatch: {name}")
    return entry


def _validate_scope_storage(
    store: Path,
    scopes: dict[PluginScope, bool],
) -> None:
    is_user_store = store.resolve() == user_home()
    if is_user_store and any(scope != "user" for scope in scopes):
        raise ValueError("User plugin store may only contain user scope declarations.")
    if not is_user_store and "user" in scopes:
        raise ValueError("User scope declarations must use the user plugin store.")


def _installed_plugin(entry: dict[str, Any]) -> InstalledPlugin:
    return InstalledPlugin(
        name=str(entry.get("name") or ""),
        description=str(entry.get("description") or ""),
        version=str(entry["version"]) if entry.get("version") is not None else None,
        enabled=bool(entry.get("enabled", True)),
        source=str(entry.get("source") or ""),
        cache_path=str(entry.get("cache_path") or ""),
        installed_at=str(entry.get("installed_at") or ""),
        component_count=int(entry.get("component_count") or 0),
        marketplace=(str(entry["marketplace"]) if entry.get("marketplace") else None),
        scopes=tuple(sorted(_entry_scopes(entry))),
    )


def _verify_expected_plugin(
    entry: object,
    expected: tuple[str, str | None, str | None] | None,
) -> None:
    if expected is None:
        return
    if not isinstance(entry, dict):
        raise ValueError("Plugin was removed while its update was downloading.")
    current = (
        str(entry.get("source") or ""),
        str(entry["marketplace"]) if entry.get("marketplace") else None,
        str(entry["version"]) if entry.get("version") is not None else None,
    )
    if current != expected:
        raise ValueError("Plugin source or version changed while its update was downloading.")


__all__ = [
    "enabled_plugin_manifests",
    "install_local_plugin",
    "list_installed_plugins",
    "read_installed_plugin",
    "read_installed_plugin_manifest",
    "set_plugin_enabled",
    "update_installed_plugin",
    "uninstall_plugin",
]
