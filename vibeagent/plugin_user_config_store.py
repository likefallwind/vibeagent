from __future__ import annotations

import json
import os
from pathlib import Path
import stat
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING

from .plugin_locations import user_home
from .plugin_scope_settings import PluginScope
from .plugin_state import PLUGIN_STORE_LOCK, plugins_root
from .workspace_metadata_files import has_symlink_component, read_regular_file_bytes

if TYPE_CHECKING:
    from .workspace_core import RunWorkspace


MAX_PLUGIN_USER_SETTINGS_BYTES = 512_000
MAX_PLUGIN_CREDENTIALS_BYTES = 512_000
PLUGIN_CREDENTIALS_VERSION = 1


def read_plugin_configured_values(
    root: Path,
    aliases: tuple[str, ...],
    *,
    workspace: RunWorkspace | None = None,
) -> tuple[dict[str, object], dict[str, str], dict[str, str]]:
    configured: dict[str, object] = {}
    sources: dict[str, str] = {}
    settings_sources: dict[str, str] = {}
    if workspace is None:
        settings_locations = [
            (user_home(), user_home() / ".claude/settings.json", "~/.claude/settings.json"),
            (root, root / ".claude/settings.json", ".claude/settings.json"),
            (root, root / ".claude/settings.local.json", ".claude/settings.local.json"),
        ]
    else:
        from .workspace_settings_sources import claude_settings_files

        settings_locations = [
            (config.boundary, config.path, config.source)
            for config in claude_settings_files(workspace)
        ]
    for settings_root, path, label in settings_locations:
        payload = _read_settings_path(settings_root, path, label=label)
        for alias in aliases:
            for key, value in _plugin_options(payload, alias, label).items():
                configured[key] = value
                sources[key] = label
                settings_sources[key] = label
    credential_roots = [(user_home(), "user protected credential store")]
    if root != user_home():
        credential_roots.append((root, "protected credential store"))
    for credential_root, label in credential_roots:
        credentials = _read_credentials(credential_root)
        for alias in aliases:
            selected = credentials.get(alias, {})
            for key, value in selected.items():
                configured[key] = value
                sources[key] = label
    return configured, sources, settings_sources


def write_plugin_configured_value(
    root: Path,
    plugin_id: str,
    key: str,
    value: object,
    *,
    sensitive: bool,
    scope: PluginScope | None = None,
) -> None:
    target = user_home() if scope == "user" else root
    with PLUGIN_STORE_LOCK:
        if sensitive:
            credentials = _read_credentials(target)
            plugin_values = credentials.setdefault(plugin_id, {})
            plugin_values[key] = value
            _write_credentials(target, credentials)
            _remove_settings_option(target, plugin_id, key, scope=scope)
            return
        _write_settings_option(target, plugin_id, key, value, scope=scope)
        credentials = _read_credentials(target)
        if _remove_nested_option(credentials, plugin_id, key):
            _write_credentials(target, credentials)


def unset_plugin_configured_value(
    root: Path,
    plugin_id: str,
    key: str,
    *,
    scope: PluginScope | None = None,
) -> None:
    target = user_home() if scope == "user" else root
    with PLUGIN_STORE_LOCK:
        _remove_settings_option(target, plugin_id, key, scope=scope)
        credentials = _read_credentials(target)
        if _remove_nested_option(credentials, plugin_id, key):
            _write_credentials(target, credentials)


def _read_settings_payload(
    root: Path,
    relative: str,
    *,
    label: str | None = None,
) -> dict[str, object]:
    label = label or relative
    path = root / relative
    return _read_settings_path(root, path, label=label)


def _read_settings_path(root: Path, path: Path, *, label: str) -> dict[str, object]:
    if not path.exists() and not path.is_symlink():
        return {}
    if has_symlink_component(root, path) or not path.is_file():
        raise ValueError(f"{label} must be a regular non-symlink file.")
    raw = read_regular_file_bytes(path, max_bytes=MAX_PLUGIN_USER_SETTINGS_BYTES, label=label)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not parse {label}: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain a JSON object.")
    return payload


def _plugin_options(payload: dict[str, object], plugin_id: str, source: str) -> dict[str, object]:
    configs = payload.get("pluginConfigs", {})
    if not isinstance(configs, dict):
        raise ValueError(f"{source} pluginConfigs must be an object.")
    selected = configs.get(plugin_id, {})
    if not isinstance(selected, dict):
        raise ValueError(f"{source} pluginConfigs[{plugin_id!r}] must be an object.")
    options = selected.get("options", {})
    if not isinstance(options, dict) or any(not isinstance(key, str) for key in options):
        raise ValueError(f"{source} pluginConfigs[{plugin_id!r}].options must be an object.")
    return dict(options)


def _credentials_path(root: Path) -> Path:
    return plugins_root(root) / "user-config-credentials.json"


def _read_credentials(root: Path) -> dict[str, dict[str, object]]:
    path = _credentials_path(root)
    if not path.exists() and not path.is_symlink():
        return {}
    if path.is_symlink() or not path.is_file():
        raise ValueError("Plugin credential store must be a regular non-symlink file.")
    raw = read_regular_file_bytes(
        path,
        max_bytes=MAX_PLUGIN_CREDENTIALS_BYTES,
        label="Plugin credential store",
    )
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Plugin credential store is invalid: {error}") from error
    if not isinstance(payload, dict) or payload.get("version") != PLUGIN_CREDENTIALS_VERSION:
        raise ValueError("Plugin credential store has an unsupported format.")
    plugins = payload.get("plugins", {})
    if not isinstance(plugins, dict):
        raise ValueError("Plugin credential store plugins field must be an object.")
    return {
        str(plugin): dict(values)
        for plugin, values in plugins.items()
        if isinstance(plugin, str) and isinstance(values, dict)
    }


def _write_credentials(root: Path, values: dict[str, dict[str, object]]) -> None:
    directory = plugins_root(root, create=True)
    path = directory / "user-config-credentials.json"
    if path.is_symlink():
        raise ValueError("Plugin credential store must not be a symbolic link.")
    payload = json.dumps(
        {"version": PLUGIN_CREDENTIALS_VERSION, "plugins": values},
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    _atomic_write(path, payload, 0o600)


def _write_settings_option(
    root: Path,
    plugin_id: str,
    key: str,
    value: object,
    *,
    scope: PluginScope | None,
) -> None:
    relative = (
        ".claude/settings.json"
        if scope in {"user", "project"}
        else ".claude/settings.local.json"
    )
    payload = _read_settings_payload(root, relative)
    configs = payload.setdefault("pluginConfigs", {})
    if not isinstance(configs, dict):
        raise ValueError(f"{relative} pluginConfigs must be an object.")
    selected = configs.setdefault(plugin_id, {})
    if not isinstance(selected, dict):
        raise ValueError(f"{relative} pluginConfigs[{plugin_id!r}] must be an object.")
    options = selected.setdefault("options", {})
    if not isinstance(options, dict):
        raise ValueError(f"{relative} pluginConfigs[{plugin_id!r}].options must be an object.")
    options[key] = value
    _write_settings(root, payload, scope=scope)


def _remove_settings_option(
    root: Path,
    plugin_id: str,
    key: str,
    *,
    scope: PluginScope | None,
) -> None:
    relative = (
        ".claude/settings.json"
        if scope in {"user", "project"}
        else ".claude/settings.local.json"
    )
    path = root / relative
    if not path.exists() and not path.is_symlink():
        return
    payload = _read_settings_payload(root, relative)
    if _remove_nested_option(payload.get("pluginConfigs"), plugin_id, key):
        _write_settings(root, payload, scope=scope)


def _remove_nested_option(container: object, plugin_id: str, key: str) -> bool:
    if not isinstance(container, dict):
        return False
    selected = container.get(plugin_id)
    if not isinstance(selected, dict):
        return False
    options = selected.get("options")
    if not isinstance(options, dict) or key not in options:
        return False
    del options[key]
    if not options:
        selected.pop("options", None)
    if not selected:
        container.pop(plugin_id, None)
    return True


def _write_settings(
    root: Path,
    payload: dict[str, object],
    *,
    scope: PluginScope | None,
) -> None:
    directory = root / ".claude"
    name = "settings.json" if scope in {"user", "project"} else "settings.local.json"
    path = directory / name
    if directory.is_symlink() or path.is_symlink():
        raise ValueError(f".claude/{name} must not contain symbolic links.")
    directory.mkdir(mode=0o700, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else (
        0o644 if scope == "project" else 0o600
    )
    _atomic_write(path, encoded, mode)


def _atomic_write(path: Path, payload: str, mode: int) -> None:
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(payload)
        temporary = Path(handle.name)
    try:
        os.chmod(temporary, mode)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


__all__ = [
    "read_plugin_configured_values",
    "unset_plugin_configured_value",
    "write_plugin_configured_value",
]
