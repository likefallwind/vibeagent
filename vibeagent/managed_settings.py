from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Callable

from .workspace_metadata_files import has_symlink_component, read_regular_file_bytes


MAX_MANAGED_SETTINGS_FILE_BYTES = 2 * 1024 * 1024
MAX_MANAGED_SETTINGS_TOTAL_BYTES = 4 * 1024 * 1024
MAX_MANAGED_SETTINGS_DROP_INS = 100


def managed_settings_directory() -> Path:
    if sys.platform == "darwin":
        return Path("/Library/Application Support/ClaudeCode")
    if os.name == "nt":
        return Path(r"C:\Program Files\ClaudeCode")
    return Path("/etc/claude-code")


def read_file_managed_settings(
    directory: Path | None = None,
    *,
    directory_resolver: Callable[[], Path] | None = None,
) -> tuple[dict[str, object] | None, tuple[str, ...]]:
    root = (directory or (directory_resolver or managed_settings_directory)()).absolute()
    if root.is_symlink():
        raise ValueError(f"Managed settings directory must not be a symbolic link: {root}")
    base = root / "managed-settings.json"
    drop_in_dir = root / "managed-settings.d"
    files: list[Path] = []
    if base.exists() or base.is_symlink():
        files.append(base)
    if drop_in_dir.exists() or drop_in_dir.is_symlink():
        if has_symlink_component(root, drop_in_dir) or not drop_in_dir.is_dir():
            raise ValueError(f"Managed settings drop-in path must be a regular directory: {drop_in_dir}")
        candidates = sorted(
            (
                path
                for path in drop_in_dir.iterdir()
                if not path.name.startswith(".") and path.suffix == ".json"
            ),
            key=lambda path: path.name,
        )
        if len(candidates) > MAX_MANAGED_SETTINGS_DROP_INS:
            raise ValueError(
                f"Managed settings exceed {MAX_MANAGED_SETTINGS_DROP_INS} drop-in files."
            )
        files.extend(candidates)
    if not files:
        return None, ()

    merged: dict[str, object] = {}
    sources: list[str] = []
    total_bytes = 0
    for path in files:
        if has_symlink_component(root, path) or not path.is_file():
            raise ValueError(f"Managed settings must be regular non-symlink files: {path}")
        raw = read_regular_file_bytes(
            path,
            max_bytes=MAX_MANAGED_SETTINGS_FILE_BYTES,
            label=path.as_posix(),
        )
        total_bytes += len(raw)
        if total_bytes > MAX_MANAGED_SETTINGS_TOTAL_BYTES:
            raise ValueError(
                f"Managed settings exceed {MAX_MANAGED_SETTINGS_TOTAL_BYTES} total bytes."
            )
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(f"Could not parse managed settings {path}: {error}") from error
        if not isinstance(payload, dict):
            raise ValueError(f"Managed settings {path} must contain a JSON object.")
        merged = _merge_managed_values(merged, payload)
        sources.append(path.as_posix())

    encoded = json.dumps(merged, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_MANAGED_SETTINGS_TOTAL_BYTES:
        raise ValueError(
            f"Merged managed settings exceed {MAX_MANAGED_SETTINGS_TOTAL_BYTES} bytes."
        )
    return merged, tuple(sources)


def _merge_managed_values(
    lower: dict[str, object],
    higher: dict[str, object],
) -> dict[str, object]:
    merged = dict(lower)
    for key, value in higher.items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = _merge_managed_values(existing, value)
        elif isinstance(existing, list) and isinstance(value, list):
            merged[key] = _deduplicated_list([*existing, *value])
        else:
            merged[key] = value
    return merged


def _deduplicated_list(values: list[object]) -> list[object]:
    result: list[object] = []
    fingerprints: set[str] = set()
    for value in values:
        fingerprint = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if fingerprint in fingerprints:
            continue
        fingerprints.add(fingerprint)
        result.append(value)
    return result


__all__ = [
    "managed_settings_directory",
    "read_file_managed_settings",
]
