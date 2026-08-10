from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .plugin_manifest import PLUGIN_VERSION_PATTERN, read_plugin_manifest
from .plugin_npm_sources import (
    normalize_npm_registry,
    validate_npm_package_name,
    validate_npm_version_selector,
)
from .plugin_remote_sources import (
    github_repository_url,
    normalize_public_https_url,
    validate_git_revision,
    validate_git_sha,
)
from .plugin_state import validate_plugin_name
from .plugin_types import MarketplaceManifest, MarketplacePlugin
from .workspace_metadata_files import has_symlink_component, read_regular_file_bytes


MAX_MARKETPLACE_MANIFEST_BYTES = 1_000_000
MAX_MARKETPLACE_PLUGINS = 1_000


@dataclass(frozen=True)
class _PluginSource:
    kind: str
    display: str
    url: str | None = None
    ref: str | None = None
    sha: str | None = None
    subdirectory: str | None = None
    npm_package: str | None = None
    npm_version: str | None = None
    npm_registry: str | None = None


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
    source_value = entry.get("source")
    if isinstance(source_value, str):
        source = source_value
        source_kind = "relative"
        path = _resolve_plugin_source(root, source, label)
        manifest = read_plugin_manifest(path)
        if manifest.name != name:
            raise ValueError(
                f"{label} name {name!r} does not match plugin manifest name {manifest.name!r}."
            )
        source_info = _PluginSource(kind=source_kind, display=source)
        fallback_description = manifest.description
        fallback_version = manifest.version
    elif isinstance(source_value, dict):
        source_info = _read_remote_plugin_source(source_value, label)
        source_kind = source_info.kind
        source = source_info.display
        path = None
        fallback_description = ""
        fallback_version = None
    else:
        raise ValueError(f"{label} source must be a relative path or supported Git source object.")
    description = _optional_text(entry, "description", max_length=1_000) or fallback_description
    version = entry.get("version", fallback_version)
    if version is not None and (
        not isinstance(version, str) or not PLUGIN_VERSION_PATTERN.fullmatch(version)
    ):
        raise ValueError(f"{label} version must use the supported plugin version format.")
    return MarketplacePlugin(
        name=name,
        source=source,
        source_kind=source_kind,
        path=path,
        url=source_info.url,
        ref=source_info.ref,
        sha=source_info.sha,
        subdirectory=source_info.subdirectory,
        npm_package=source_info.npm_package,
        npm_version=source_info.npm_version,
        npm_registry=source_info.npm_registry,
        description=" ".join(description.split()),
        version=version,
    )


def _read_remote_plugin_source(
    source: dict[str, Any],
    label: str,
) -> _PluginSource:
    kind = source.get("source")
    if kind == "github":
        repository = source.get("repo")
        if not isinstance(repository, str):
            raise ValueError(f"{label} GitHub source requires repo=owner/repository.")
        url = github_repository_url(repository)
        display = f"github:{repository}"
        subdirectory = None
    elif kind in {"url", "git-subdir"}:
        raw_url = source.get("url")
        if not isinstance(raw_url, str):
            raise ValueError(f"{label} {kind} source requires an HTTPS url.")
        url = normalize_public_https_url(raw_url, label=f"{label} Git URL")
        display = url
        subdirectory = _safe_subdirectory(source.get("path"), label) if kind == "git-subdir" else None
    elif kind == "npm":
        package = source.get("package")
        if not isinstance(package, str):
            raise ValueError(f"{label} npm source requires a package name.")
        package = validate_npm_package_name(package)
        version_value = source.get("version")
        if version_value is not None and not isinstance(version_value, str):
            raise ValueError(f"{label} npm package version must be a string.")
        version = validate_npm_version_selector(version_value)
        registry_value = source.get("registry")
        if registry_value is not None and not isinstance(registry_value, str):
            raise ValueError(f"{label} npm registry must be a string.")
        registry = normalize_npm_registry(registry_value)
        return _PluginSource(
            kind="npm",
            display=f"npm:{package}@{version}",
            npm_package=package,
            npm_version=version,
            npm_registry=registry,
        )
    else:
        raise ValueError(f"{label} source object must use github, url, git-subdir, or npm.")
    ref_value = source.get("ref")
    if ref_value is not None and not isinstance(ref_value, str):
        raise ValueError(f"{label} Git ref must be a string.")
    ref = validate_git_revision(ref_value)
    sha_value = source.get("sha")
    if sha_value is not None and not isinstance(sha_value, str):
        raise ValueError(f"{label} Git SHA must be a string.")
    sha = validate_git_sha(sha_value)
    if ref is not None and sha is not None:
        raise ValueError(f"{label} source must not specify both ref and sha.")
    return _PluginSource(
        kind=str(kind),
        display=display,
        url=url,
        ref=ref,
        sha=sha,
        subdirectory=subdirectory,
    )


def _safe_subdirectory(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or value.startswith("/"):
        raise ValueError(f"{label} git-subdir source requires a relative path.")
    path = Path(value)
    if ".." in path.parts or len(path.parts) > 12:
        raise ValueError(f"{label} git-subdir path must stay inside the Git repository.")
    return path.as_posix()


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
