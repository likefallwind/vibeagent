from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .plugin_manifest import PLUGIN_VERSION_PATTERN, read_plugin_manifest
from .plugin_state import validate_plugin_name
from .plugin_types import MarketplaceManifest, MarketplacePlugin
from .workspace_metadata_files import has_symlink_component, read_regular_file_bytes


MAX_MARKETPLACE_MANIFEST_BYTES = 1_000_000
MAX_MARKETPLACE_PLUGINS = 1_000


def read_marketplace_manifest(source: Path) -> MarketplaceManifest:
    root, manifest_path = _marketplace_paths(source)
    raw = read_regular_file_bytes(
        manifest_path,
        max_bytes=MAX_MARKETPLACE_MANIFEST_BYTES,
        label="marketplace.json",
    )
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not parse marketplace.json: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError("marketplace.json must contain a JSON object.")

    name = payload.get("name")
    if not isinstance(name, str):
        raise ValueError("Marketplace name must be a string.")
    validate_plugin_name(name, label="Marketplace")
    description = _optional_text(payload, "description", max_length=1_000)
    owner_payload = payload.get("owner")
    if not isinstance(owner_payload, dict):
        raise ValueError("Marketplace owner must be an object with a name.")
    owner = owner_payload.get("name")
    if not isinstance(owner, str) or not owner.strip() or len(owner) > 200:
        raise ValueError("Marketplace owner name must be a non-empty string of at most 200 characters.")

    entries = payload.get("plugins")
    if not isinstance(entries, list):
        raise ValueError("Marketplace plugins must be an array.")
    if len(entries) > MAX_MARKETPLACE_PLUGINS:
        raise ValueError(f"Marketplace exposes more than {MAX_MARKETPLACE_PLUGINS} plugins.")
    plugins = tuple(_read_plugin_entry(root, entry, index) for index, entry in enumerate(entries))
    names = [plugin.name for plugin in plugins]
    if len(set(names)) != len(names):
        raise ValueError("Marketplace plugin names must be unique.")
    return MarketplaceManifest(
        name=name,
        description=" ".join(description.split()),
        owner=" ".join(owner.split()),
        root=root,
        manifest_path=manifest_path,
        plugins=plugins,
    )


def marketplace_manifest_exists(source: Path) -> bool:
    if source.is_dir():
        return (source / ".claude-plugin" / "marketplace.json").exists() or (
            source / "marketplace.json"
        ).exists()
    return source.name == "marketplace.json" and source.exists()


def _marketplace_paths(source: Path) -> tuple[Path, Path]:
    if source.is_symlink():
        raise ValueError("Marketplace source must not be a symbolic link.")
    resolved = source.resolve()
    if resolved.is_dir():
        root = resolved
        preferred = root / ".claude-plugin" / "marketplace.json"
        manifest_path = preferred if preferred.exists() or preferred.is_symlink() else root / "marketplace.json"
    elif resolved.is_file() and resolved.name == "marketplace.json":
        manifest_path = resolved
        root = resolved.parent.parent if resolved.parent.name == ".claude-plugin" else resolved.parent
    else:
        raise ValueError("Marketplace source must be a directory or marketplace.json file.")
    if not manifest_path.exists():
        raise ValueError("Marketplace source does not contain .claude-plugin/marketplace.json.")
    if has_symlink_component(root, manifest_path) or not manifest_path.is_file():
        raise ValueError("marketplace.json must be a regular non-symlink file.")
    return root, manifest_path


def _read_plugin_entry(root: Path, entry: object, index: int) -> MarketplacePlugin:
    label = f"Marketplace plugins[{index}]"
    if not isinstance(entry, dict):
        raise ValueError(f"{label} must be an object.")
    name = entry.get("name")
    if not isinstance(name, str):
        raise ValueError(f"{label} name must be a string.")
    validate_plugin_name(name)
    source = entry.get("source")
    if not isinstance(source, str):
        raise ValueError(
            f"{label} source must be a ./ relative directory; network and package sources are not supported yet."
        )
    path = _resolve_plugin_source(root, source, label)
    manifest = read_plugin_manifest(path)
    if manifest.name != name:
        raise ValueError(
            f"{label} name {name!r} does not match plugin manifest name {manifest.name!r}."
        )
    description = _optional_text(entry, "description", max_length=1_000) or manifest.description
    version = entry.get("version", manifest.version)
    if version is not None and (
        not isinstance(version, str) or not PLUGIN_VERSION_PATTERN.fullmatch(version)
    ):
        raise ValueError(f"{label} version must use the supported plugin version format.")
    return MarketplacePlugin(
        name=name,
        source=source,
        path=path,
        description=" ".join(description.split()),
        version=version,
    )


def _resolve_plugin_source(root: Path, source: str, label: str) -> Path:
    if not source.startswith("./") or source in {"./", "."}:
        raise ValueError(f"{label} source must start with ./ and name a plugin directory.")
    relative = Path(source[2:])
    if not relative.parts or ".." in relative.parts:
        raise ValueError(f"{label} source must not contain '..'.")
    lexical = root / relative
    if has_symlink_component(root, lexical):
        raise ValueError(f"{label} source contains a symbolic link: {source}")
    target = lexical.resolve()
    if root not in target.parents or not target.is_dir():
        raise ValueError(f"{label} source must resolve to a directory inside the marketplace: {source}")
    return target


def _optional_text(payload: dict[str, Any], key: str, *, max_length: int) -> str:
    value = payload.get(key, "")
    if not isinstance(value, str) or len(value) > max_length:
        raise ValueError(f"Marketplace {key} must be a string of at most {max_length} characters.")
    return value


__all__ = ["marketplace_manifest_exists", "read_marketplace_manifest"]
