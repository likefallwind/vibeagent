from __future__ import annotations

import os
from pathlib import Path

from .invocation_plugin_archives import materialize_invocation_plugin_archive
from .invocation_plugin_urls import (
    materialize_invocation_plugin_url,
    parse_invocation_plugin_urls,
)
from .plugin_manifest import read_plugin_manifest


MAX_INVOCATION_PLUGIN_DIRS = 20


def resolve_invocation_plugin_dirs(
    values: list[str] | tuple[str, ...] | None,
    *,
    invocation_root: Path,
    plugin_urls: list[str] | tuple[str, ...] | None = None,
) -> tuple[Path, ...]:
    urls = parse_invocation_plugin_urls(plugin_urls)
    if not values and not urls:
        return ()
    if len(values or ()) + len(urls) > MAX_INVOCATION_PLUGIN_DIRS:
        raise ValueError(
            f"--plugin-dir and --plugin-url accept at most {MAX_INVOCATION_PLUGIN_DIRS} plugins combined."
        )
    resolved: list[Path] = []
    names: dict[str, Path] = {}
    seen: set[Path] = set()
    for value in values or ():
        if not value.strip():
            raise ValueError("--plugin-dir path cannot be empty.")
        candidate = Path(value).expanduser()
        candidate = candidate if candidate.is_absolute() else invocation_root / candidate
        lexical = Path(os.path.abspath(candidate))
        try:
            root = candidate.resolve(strict=True)
        except OSError as error:
            raise ValueError(f"--plugin-dir directory not found: {value}") from error
        if lexical != root or candidate.is_symlink():
            raise ValueError(f"--plugin-dir must be a regular non-symlink directory or ZIP archive: {value}")
        if root.is_file() and root.suffix.lower() == ".zip":
            root = materialize_invocation_plugin_archive(root)
        elif not root.is_dir():
            raise ValueError(f"--plugin-dir must be a regular non-symlink directory or ZIP archive: {value}")
        _append_plugin_root(root, resolved=resolved, names=names, seen=seen)
    seen_urls: set[str] = set()
    for value in urls:
        if value in seen_urls:
            continue
        seen_urls.add(value)
        root = materialize_invocation_plugin_url(value)
        _append_plugin_root(root, resolved=resolved, names=names, seen=seen)
    return tuple(resolved)


def _append_plugin_root(
    root: Path,
    *,
    resolved: list[Path],
    names: dict[str, Path],
    seen: set[Path],
) -> None:
    manifest = read_plugin_manifest(root)
    previous = names.get(manifest.name)
    if previous is not None and previous != root:
        raise ValueError(
            f"Invocation plugins resolve duplicate plugin name {manifest.name}: "
            f"{previous} and {root}"
        )
    names[manifest.name] = root
    if root not in seen:
        seen.add(root)
        resolved.append(root)


__all__ = ["MAX_INVOCATION_PLUGIN_DIRS", "resolve_invocation_plugin_dirs"]
