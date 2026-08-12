from __future__ import annotations

import os
from pathlib import Path

from .plugin_manifest import read_plugin_manifest


MAX_INVOCATION_PLUGIN_DIRS = 20


def resolve_invocation_plugin_dirs(
    values: list[str] | tuple[str, ...] | None,
    *,
    invocation_root: Path,
) -> tuple[Path, ...]:
    if not values:
        return ()
    if len(values) > MAX_INVOCATION_PLUGIN_DIRS:
        raise ValueError(f"--plugin-dir accepts at most {MAX_INVOCATION_PLUGIN_DIRS} directories.")
    resolved: list[Path] = []
    names: dict[str, Path] = {}
    seen: set[Path] = set()
    for value in values:
        if not value.strip():
            raise ValueError("--plugin-dir path cannot be empty.")
        candidate = Path(value).expanduser()
        candidate = candidate if candidate.is_absolute() else invocation_root / candidate
        lexical = Path(os.path.abspath(candidate))
        try:
            root = candidate.resolve(strict=True)
        except OSError as error:
            raise ValueError(f"--plugin-dir directory not found: {value}") from error
        if lexical != root or candidate.is_symlink() or not root.is_dir():
            raise ValueError(f"--plugin-dir must be a regular non-symlink directory: {value}")
        manifest = read_plugin_manifest(root)
        previous = names.get(manifest.name)
        if previous is not None and previous != root:
            raise ValueError(
                f"--plugin-dir resolves duplicate plugin name {manifest.name}: "
                f"{previous} and {root}"
            )
        names[manifest.name] = root
        if root not in seen:
            seen.add(root)
            resolved.append(root)
    return tuple(resolved)


__all__ = ["MAX_INVOCATION_PLUGIN_DIRS", "resolve_invocation_plugin_dirs"]
