from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import RLock
from typing import Any
from uuid import uuid4

from .plugin_manifest import PLUGIN_NAME_PATTERN, read_plugin_manifest
from .plugin_installation import copy_plugin_tree, remove_plugin_tree
from .plugin_types import InstalledPlugin, PluginManifest
from .workspace_metadata_files import read_regular_file_bytes
from .workspace_resolve import resolve_mutation_path


MAX_PLUGIN_STATE_BYTES = 2_000_000
PLUGIN_STATE_VERSION = 1
_STORE_LOCK = RLock()


def install_local_plugin(project_root: Path, source_path: str) -> InstalledPlugin:
    source = resolve_mutation_path(project_root, source_path)
    manifest = read_plugin_manifest(source)
    root = _plugins_root(project_root, create=True)
    cache_root = root / "cache"
    _ensure_directory(cache_root, create=True)
    destination = cache_root / manifest.name
    if destination.is_symlink():
        raise ValueError(f"Plugin cache destination must not be a symbolic link: {manifest.name}")
    staging = cache_root / f".{manifest.name}.install-{uuid4().hex[:8]}"
    backup = cache_root / f".{manifest.name}.backup-{uuid4().hex[:8]}"
    copy_plugin_tree(source, staging)

    with _STORE_LOCK:
        state = _read_state(project_root)
        existing_plugins = state.get("plugins", {})
        existing_entry = existing_plugins.get(manifest.name) if isinstance(existing_plugins, dict) else None
        try:
            if destination.exists():
                destination.replace(backup)
            staging.replace(destination)
            installed_manifest = read_plugin_manifest(destination)
            if installed_manifest.name != manifest.name:
                raise ValueError("Plugin identity changed while copying the install source.")
            entry = {
                "name": installed_manifest.name,
                "description": installed_manifest.description,
                "version": installed_manifest.version,
                "enabled": (
                    bool(existing_entry.get("enabled"))
                    if isinstance(existing_entry, dict)
                    else installed_manifest.default_enabled
                ),
                "source": source.relative_to(project_root.resolve()).as_posix(),
                "cache_path": destination.relative_to(project_root.resolve()).as_posix(),
                "installed_at": _timestamp(),
                "component_count": installed_manifest.component_count,
            }
            plugins = state.setdefault("plugins", {})
            if not isinstance(plugins, dict):
                raise ValueError("Plugin state plugins field is invalid.")
            plugins[manifest.name] = entry
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
    return _installed_plugin(entry)


def set_plugin_enabled(project_root: Path, name: str, enabled: bool) -> InstalledPlugin:
    _validate_name(name)
    with _STORE_LOCK:
        state = _read_state(project_root)
        entry = _plugin_entry(state, name)
        entry["enabled"] = enabled
        _write_state(project_root, state)
        return _installed_plugin(entry)


def uninstall_plugin(project_root: Path, name: str) -> InstalledPlugin:
    _validate_name(name)
    with _STORE_LOCK:
        state = _read_state(project_root)
        entry = _plugin_entry(state, name)
        installed = _installed_plugin(entry)
        cache_path = _safe_cache_path(project_root, str(entry.get("cache_path") or ""), name)
        trash_path = cache_path.parent / f".{name}.uninstall-{uuid4().hex[:8]}"
        if cache_path.exists():
            cache_path.replace(trash_path)
        plugins = state["plugins"]
        assert isinstance(plugins, dict)
        del plugins[name]
        try:
            _write_state(project_root, state)
        except Exception:
            if trash_path.exists():
                trash_path.replace(cache_path)
            raise
        if trash_path.exists():
            remove_plugin_tree(trash_path)
        return installed


def list_installed_plugins(project_root: Path) -> list[InstalledPlugin]:
    with _STORE_LOCK:
        state = _read_state(project_root)
    plugins = state.get("plugins", {})
    if not isinstance(plugins, dict):
        return []
    installed: list[InstalledPlugin] = []
    for name, value in plugins.items():
        if not isinstance(name, str) or not isinstance(value, dict):
            continue
        try:
            item = _installed_plugin(value)
            _validate_name(item.name)
            path = _safe_cache_path(project_root, item.cache_path, item.name)
            manifest = read_plugin_manifest(path)
            if manifest.name != item.name:
                raise ValueError("cached manifest name does not match installed state")
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
                error=str(error),
            )
        installed.append(item)
    return sorted(installed, key=lambda plugin: plugin.name)


def read_installed_plugin_manifest(project_root: Path, name: str) -> PluginManifest:
    _validate_name(name)
    with _STORE_LOCK:
        state = _read_state(project_root)
        entry = _plugin_entry(state, name)
        path = _safe_cache_path(project_root, str(entry.get("cache_path") or ""), name)
    manifest = read_plugin_manifest(path)
    if manifest.name != name:
        raise ValueError(f"Cached plugin manifest name mismatch: {name}")
    return manifest


def enabled_plugin_manifests(project_root: Path) -> list[PluginManifest]:
    manifests: list[PluginManifest] = []
    for plugin in list_installed_plugins(project_root):
        if not plugin.enabled or plugin.error is not None:
            continue
        try:
            manifests.append(read_installed_plugin_manifest(project_root, plugin.name))
        except (OSError, UnicodeError, ValueError):
            continue
    return manifests


def _read_state(project_root: Path) -> dict[str, Any]:
    path = _state_path(project_root)
    if not path.exists():
        return {"version": PLUGIN_STATE_VERSION, "plugins": {}}
    if path.is_symlink() or not path.is_file():
        raise ValueError("Plugin state must be a regular non-symlink file.")
    try:
        raw = read_regular_file_bytes(path, max_bytes=MAX_PLUGIN_STATE_BYTES, label="Plugin state")
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Plugin state is invalid: {error}") from error
    if not isinstance(value, dict) or value.get("version") != PLUGIN_STATE_VERSION:
        raise ValueError("Plugin state has an unsupported format.")
    if not isinstance(value.get("plugins"), dict):
        raise ValueError("Plugin state plugins field must be an object.")
    return value


def _write_state(project_root: Path, state: dict[str, Any]) -> None:
    root = _plugins_root(project_root, create=True)
    state_path = root / "installed.json"
    if state_path.is_symlink():
        raise ValueError("Plugin state must not be a symbolic link.")
    payload = json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with NamedTemporaryFile("w", encoding="utf-8", dir=root, delete=False) as handle:
        handle.write(payload)
        temp_path = Path(handle.name)
    os.chmod(temp_path, 0o600)
    temp_path.replace(state_path)


def _plugin_entry(state: dict[str, Any], name: str) -> dict[str, Any]:
    plugins = state.get("plugins")
    if not isinstance(plugins, dict) or not isinstance(plugins.get(name), dict):
        raise ValueError(f"Plugin is not installed: {name}")
    return plugins[name]


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
    )


def _plugins_root(project_root: Path, *, create: bool = False) -> Path:
    project = project_root.resolve()
    runtime = project / ".vibeagent"
    root = runtime / "plugins"
    for path, label in ((runtime, ".vibeagent"), (root, ".vibeagent/plugins")):
        if path.is_symlink():
            raise ValueError(f"{label} must not be a symbolic link.")
    if create:
        runtime.mkdir(mode=0o700, exist_ok=True)
        root.mkdir(mode=0o700, exist_ok=True)
        os.chmod(root, 0o700)
    if root.exists() and not root.is_dir():
        raise ValueError(".vibeagent/plugins must be a directory.")
    return root


def _state_path(project_root: Path) -> Path:
    return _plugins_root(project_root) / "installed.json"


def _safe_cache_path(project_root: Path, value: str, name: str) -> Path:
    cache_root = _plugins_root(project_root) / "cache"
    expected = cache_root / name
    expected_value = expected.relative_to(project_root.resolve()).as_posix()
    if value != expected_value:
        raise ValueError(f"Plugin cache path is invalid for {name}.")
    if cache_root.is_symlink() or expected.is_symlink():
        raise ValueError(f"Plugin cache path must not be a symbolic link: {name}")
    return expected


def _ensure_directory(path: Path, *, create: bool) -> None:
    if path.is_symlink():
        raise ValueError(f"Plugin path must not be a symbolic link: {path}")
    if create:
        path.mkdir(mode=0o700, exist_ok=True)
    if not path.is_dir():
        raise ValueError(f"Plugin path is not a directory: {path}")


def _validate_name(name: str) -> None:
    if not PLUGIN_NAME_PATTERN.fullmatch(name):
        raise ValueError("Plugin name must be 1-64 lowercase letters, digits, or hyphens.")


def _timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


__all__ = [
    "enabled_plugin_manifests",
    "install_local_plugin",
    "list_installed_plugins",
    "read_installed_plugin_manifest",
    "set_plugin_enabled",
    "uninstall_plugin",
]
