from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import stat
from tempfile import NamedTemporaryFile
from typing import Literal

from .workspace_metadata_files import has_symlink_component, read_regular_file_bytes


PluginScope = Literal["local", "project"]
PLUGIN_SCOPES = frozenset({"local", "project"})
MAX_PLUGIN_SCOPE_SETTINGS_BYTES = 512_000


@dataclass(frozen=True)
class PluginSettingsSnapshot:
    path: Path
    existed: bool
    content: bytes = b""
    mode: int = 0o600


def validate_plugin_scope(value: str) -> PluginScope:
    if value not in PLUGIN_SCOPES:
        raise ValueError("Plugin scope must be local or project.")
    return value  # type: ignore[return-value]


def plugin_scope_settings_path(root: Path, scope: PluginScope) -> Path:
    relative = ".claude/settings.local.json" if scope == "local" else ".claude/settings.json"
    return root.resolve() / relative


def capture_plugin_settings(root: Path, scope: PluginScope) -> PluginSettingsSnapshot:
    project = root.resolve()
    path = plugin_scope_settings_path(project, scope)
    if not path.exists() and not path.is_symlink():
        return PluginSettingsSnapshot(path=path, existed=False, mode=_default_mode(scope))
    if has_symlink_component(project, path) or not path.is_file():
        raise ValueError(f"{_settings_label(scope)} must be a regular non-symlink file.")
    content = read_regular_file_bytes(
        path,
        max_bytes=MAX_PLUGIN_SCOPE_SETTINGS_BYTES,
        label=_settings_label(scope),
    )
    return PluginSettingsSnapshot(
        path=path,
        existed=True,
        content=content,
        mode=stat.S_IMODE(path.stat().st_mode),
    )


def write_plugin_enabled_setting(
    root: Path,
    scope: PluginScope,
    plugin_id: str,
    enabled: bool | None,
) -> PluginSettingsSnapshot:
    snapshot = capture_plugin_settings(root, scope)
    payload = _decode_settings(snapshot, scope)
    configured = payload.get("enabledPlugins", {})
    if not isinstance(configured, dict) or any(
        not isinstance(key, str) or not isinstance(value, bool)
        for key, value in configured.items()
    ):
        raise ValueError(f"{_settings_label(scope)} enabledPlugins must map names to booleans.")
    selected = dict(configured)
    if enabled is None:
        selected.pop(plugin_id, None)
    else:
        selected[plugin_id] = enabled
    if selected:
        payload["enabledPlugins"] = selected
    else:
        payload.pop("enabledPlugins", None)
    _write_settings(snapshot.path, payload, snapshot.mode)
    return snapshot


def restore_plugin_settings(snapshot: PluginSettingsSnapshot) -> None:
    path = snapshot.path
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError(f"Refusing to restore plugin settings through a symbolic link: {path}")
    if snapshot.existed:
        path.parent.mkdir(mode=0o700, exist_ok=True)
        _atomic_write_bytes(path, snapshot.content, snapshot.mode)
        return
    path.unlink(missing_ok=True)


def effective_plugin_enabled(root: Path, plugin_id: str, *, fallback: bool) -> bool:
    selected = fallback
    for scope in ("project", "local"):
        snapshot = capture_plugin_settings(root, scope)
        payload = _decode_settings(snapshot, scope)
        configured = payload.get("enabledPlugins", {})
        if not isinstance(configured, dict) or any(
            not isinstance(key, str) or not isinstance(value, bool)
            for key, value in configured.items()
        ):
            raise ValueError(f"{_settings_label(scope)} enabledPlugins must map names to booleans.")
        value = configured.get(plugin_id)
        if isinstance(value, bool):
            selected = value
    return selected


def _decode_settings(
    snapshot: PluginSettingsSnapshot,
    scope: PluginScope,
) -> dict[str, object]:
    if not snapshot.existed:
        return {}
    try:
        payload = json.loads(snapshot.content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not parse {_settings_label(scope)}: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{_settings_label(scope)} must contain a JSON object.")
    return payload


def _write_settings(path: Path, payload: dict[str, object], mode: int) -> None:
    if path.parent.is_symlink() or path.is_symlink():
        raise ValueError(f"Plugin settings path must not contain symbolic links: {path}")
    path.parent.mkdir(mode=0o700, exist_ok=True)
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    if len(encoded) > MAX_PLUGIN_SCOPE_SETTINGS_BYTES:
        raise ValueError(f"Plugin settings exceed {MAX_PLUGIN_SCOPE_SETTINGS_BYTES} bytes.")
    _atomic_write_bytes(path, encoded, mode)


def _atomic_write_bytes(path: Path, payload: bytes, mode: int) -> None:
    with NamedTemporaryFile("wb", dir=path.parent, delete=False) as handle:
        handle.write(payload)
        temporary = Path(handle.name)
    try:
        os.chmod(temporary, mode)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _default_mode(scope: PluginScope) -> int:
    return 0o600 if scope == "local" else 0o644


def _settings_label(scope: PluginScope) -> str:
    return ".claude/settings.local.json" if scope == "local" else ".claude/settings.json"


__all__ = [
    "PLUGIN_SCOPES",
    "PluginScope",
    "PluginSettingsSnapshot",
    "capture_plugin_settings",
    "effective_plugin_enabled",
    "plugin_scope_settings_path",
    "restore_plugin_settings",
    "validate_plugin_scope",
    "write_plugin_enabled_setting",
]
