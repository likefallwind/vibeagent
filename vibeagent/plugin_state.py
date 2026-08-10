from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import RLock
from typing import Any

from .plugin_manifest import PLUGIN_NAME_PATTERN
from .workspace_metadata_files import read_regular_file_bytes


MAX_PLUGIN_STATE_BYTES = 2_000_000
PLUGIN_STATE_VERSION = 1
PLUGIN_STORE_LOCK = RLock()


def read_plugin_state(project_root: Path) -> dict[str, Any]:
    path = plugin_state_path(project_root)
    if not path.exists():
        return _empty_state()
    if path.is_symlink() or not path.is_file():
        raise ValueError("Plugin state must be a regular non-symlink file.")
    try:
        raw = read_regular_file_bytes(path, max_bytes=MAX_PLUGIN_STATE_BYTES, label="Plugin state")
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Plugin state is invalid: {error}") from error
    if not isinstance(value, dict) or value.get("version") != PLUGIN_STATE_VERSION:
        raise ValueError("Plugin state has an unsupported format.")
    for field in ("plugins", "marketplaces"):
        if field not in value:
            value[field] = {}
        if not isinstance(value[field], dict):
            raise ValueError(f"Plugin state {field} field must be an object.")
    return value


def write_plugin_state(project_root: Path, state: dict[str, Any]) -> None:
    root = plugins_root(project_root, create=True)
    state_path = root / "installed.json"
    if state_path.is_symlink():
        raise ValueError("Plugin state must not be a symbolic link.")
    payload = json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with NamedTemporaryFile("w", encoding="utf-8", dir=root, delete=False) as handle:
        handle.write(payload)
        temp_path = Path(handle.name)
    os.chmod(temp_path, 0o600)
    temp_path.replace(state_path)


def plugins_root(project_root: Path, *, create: bool = False) -> Path:
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


def plugin_state_path(project_root: Path) -> Path:
    return plugins_root(project_root) / "installed.json"


def safe_plugin_cache_path(project_root: Path, value: str, name: str) -> Path:
    cache_root = plugins_root(project_root) / "cache"
    return _safe_named_cache_path(project_root, cache_root, value, name, "Plugin")


def safe_marketplace_cache_path(project_root: Path, value: str, name: str) -> Path:
    cache_root = plugins_root(project_root) / "marketplaces"
    return _safe_named_cache_path(project_root, cache_root, value, name, "Marketplace")


def ensure_directory(path: Path, *, create: bool) -> None:
    if path.is_symlink():
        raise ValueError(f"Plugin path must not be a symbolic link: {path}")
    if create:
        path.mkdir(mode=0o700, exist_ok=True)
    if not path.is_dir():
        raise ValueError(f"Plugin path is not a directory: {path}")


def validate_plugin_name(name: str, *, label: str = "Plugin") -> None:
    if not PLUGIN_NAME_PATTERN.fullmatch(name):
        raise ValueError(f"{label} name must be 1-64 lowercase letters, digits, or hyphens.")


def state_timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _safe_named_cache_path(
    project_root: Path,
    cache_root: Path,
    value: str,
    name: str,
    label: str,
) -> Path:
    expected = cache_root / name
    expected_value = expected.relative_to(project_root.resolve()).as_posix()
    if value != expected_value:
        raise ValueError(f"{label} cache path is invalid for {name}.")
    if cache_root.is_symlink() or expected.is_symlink():
        raise ValueError(f"{label} cache path must not be a symbolic link: {name}")
    return expected


def _empty_state() -> dict[str, Any]:
    return {"version": PLUGIN_STATE_VERSION, "plugins": {}, "marketplaces": {}}


__all__ = [
    "PLUGIN_STORE_LOCK",
    "ensure_directory",
    "plugin_state_path",
    "plugins_root",
    "read_plugin_state",
    "safe_marketplace_cache_path",
    "safe_plugin_cache_path",
    "state_timestamp",
    "validate_plugin_name",
    "write_plugin_state",
]
