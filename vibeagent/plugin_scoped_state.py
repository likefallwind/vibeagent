from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import cast

from .plugin_scope_settings import PluginScope, effective_plugin_enabled
from .plugin_types import InstalledPlugin


def plugin_entry_scopes(entry: object) -> dict[PluginScope, bool]:
    if not isinstance(entry, dict):
        return {}
    value = entry.get("scopes", {})
    if not isinstance(value, dict):
        raise ValueError("Plugin state scopes field must be an object.")
    parsed: dict[PluginScope, bool] = {}
    for key, enabled in value.items():
        if key not in {"local", "project", "user"} or not isinstance(enabled, bool):
            raise ValueError("Plugin state scopes must map local/project/user to booleans.")
        parsed[cast(PluginScope, key)] = enabled
    return parsed


def safe_plugin_scope_names(entry: object) -> tuple[str, ...]:
    try:
        return tuple(sorted(plugin_entry_scopes(entry)))
    except ValueError:
        return ()


def qualified_plugin_id(name: str, marketplace: str | None) -> str:
    return f"{name}@{marketplace}" if marketplace else name


def effective_installed_plugin(
    project_root: Path,
    plugin: InstalledPlugin,
) -> InstalledPlugin:
    return replace(
        plugin,
        enabled=effective_plugin_enabled(
            project_root,
            qualified_plugin_id(plugin.name, plugin.marketplace),
            fallback=plugin.enabled,
        ),
    )


__all__ = [
    "effective_installed_plugin",
    "plugin_entry_scopes",
    "qualified_plugin_id",
    "safe_plugin_scope_names",
]
