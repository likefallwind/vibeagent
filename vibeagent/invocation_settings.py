from __future__ import annotations

import json
from pathlib import Path

from .workspace_metadata_files import read_regular_file_bytes


MAX_INVOCATION_SETTINGS_BYTES = 2 * 1024 * 1024
SETTING_SOURCE_NAMES = ("user", "project", "local")


def parse_setting_sources(value: str | None) -> tuple[str, ...]:
    if value is None:
        return SETTING_SOURCE_NAMES
    parts = [part.strip() for part in value.split(",") if part.strip()]
    invalid = [part for part in parts if part not in SETTING_SOURCE_NAMES]
    if invalid:
        raise ValueError(
            "--setting-sources accepts only user, project, and local; invalid: "
            + ", ".join(invalid)
        )
    return tuple(name for name in SETTING_SOURCE_NAMES if name in parts)


def parse_invocation_settings(value: str | None, invocation_root: Path) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        raise ValueError("--settings must be a JSON object or a settings file path.")
    if stripped.startswith("{"):
        raw = stripped.encode("utf-8")
        label = "CLI --settings"
    else:
        path = Path(stripped).expanduser()
        path = path if path.is_absolute() else invocation_root / path
        if path.is_symlink() or not path.is_file():
            raise ValueError("--settings path must be a regular non-symlink file.")
        raw = read_regular_file_bytes(
            path,
            max_bytes=MAX_INVOCATION_SETTINGS_BYTES,
            label="CLI --settings",
        )
        label = path.as_posix()
    if len(raw) > MAX_INVOCATION_SETTINGS_BYTES:
        raise ValueError(f"{label} exceeds {MAX_INVOCATION_SETTINGS_BYTES} bytes.")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not parse {label}: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain a JSON object.")
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if len(canonical.encode("utf-8")) > MAX_INVOCATION_SETTINGS_BYTES:
        raise ValueError(f"{label} exceeds {MAX_INVOCATION_SETTINGS_BYTES} bytes after normalization.")
    return canonical


__all__ = [
    "MAX_INVOCATION_SETTINGS_BYTES",
    "SETTING_SOURCE_NAMES",
    "parse_invocation_settings",
    "parse_setting_sources",
]
