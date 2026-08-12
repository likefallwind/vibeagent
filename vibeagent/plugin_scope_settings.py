from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import stat
from tempfile import NamedTemporaryFile
from typing import Literal, TYPE_CHECKING

from .workspace_metadata_files import has_symlink_component, read_regular_file_bytes

if TYPE_CHECKING:
    from .workspace_core import RunWorkspace


PluginScope = Literal["local", "project", "user"]
PLUGIN_SCOPES = frozenset({"local", "project", "user"})
MAX_PLUGIN_SCOPE_SETTINGS_BYTES = 512_000


@dataclass(frozen=True)
class PluginSettingsSnapshot:
    path: Path
    existed: bool
    content: bytes = b""
    mode: int = 0o600


def validate_plugin_scope(value: str) -> PluginScope:
    if value not in PLUGIN_SCOPES:
        raise ValueError("Plugin scope must be local, project, or user.")
    return value  # type: ignore[return-value]


def plugin_scope_settings_path(root: Path, scope: PluginScope) -> Path:
    if scope == "user":
        from .plugin_locations import user_home

        return user_home() / ".claude/settings.json"
    relative = ".claude/settings.local.json" if scope == "local" else ".claude/settings.json"
    return root.resolve() / relative


def capture_plugin_settings(root: Path, scope: PluginScope) -> PluginSettingsSnapshot:
    if scope == "user":
        from .plugin_locations import user_home

        boundary = user_home()
    else:
        boundary = root.resolve()
    path = plugin_scope_settings_path(root, scope)
    if not path.exists() and not path.is_symlink():
        return PluginSettingsSnapshot(path=path, existed=False, mode=_default_mode(scope))
    if has_symlink_component(boundary, path) or not path.is_file():
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


def effective_plugin_enabled(
    root: Path,
    plugin_id: str,
    *,
    fallback: bool,
    workspace: RunWorkspace | None = None,
) -> bool:
    selected = fallback
    if workspace is None:
        payloads = [
            (_decode_settings(capture_plugin_settings(root, scope), scope), scope)
            for scope in ("user", "project", "local")
        ]
    else:
        from .workspace_settings_sources import (
            claude_settings_files,
            read_settings_payload,
            settings_file_exists,
        )

        payloads = [
            (
                read_settings_payload(config, max_bytes=MAX_PLUGIN_SCOPE_SETTINGS_BYTES),
                config.source,
            )
            for config in claude_settings_files(workspace)
            if settings_file_exists(config)
        ]
    for payload, scope in payloads:
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


def _decode_settings_path(boundary: Path, path: Path, label: str) -> dict[str, object]:
    if not path.exists() and not path.is_symlink():
        return {}
    if has_symlink_component(boundary, path) or not path.is_file():
        raise ValueError(f"{label} must be a regular non-symlink file.")
    content = read_regular_file_bytes(
        path,
        max_bytes=MAX_PLUGIN_SCOPE_SETTINGS_BYTES,
        label=label,
    )
    try:
        payload = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not parse {label}: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain a JSON object.")
    return payload


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
    return 0o600 if scope in {"local", "user"} else 0o644


def _settings_label(scope: PluginScope) -> str:
    if scope == "local":
        return ".claude/settings.local.json"
    if scope == "user":
        return "~/.claude/settings.json"
    return ".claude/settings.json"


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
