from __future__ import annotations

from pathlib import Path
from typing import Literal

from .plugin_state import read_plugin_state
from .user_paths import VIBEAGENT_USER_HOME, user_home


def plugin_storage_root(project_root: Path, scope: str | None) -> Path:
    return user_home() if scope == "user" else project_root.resolve()


def resolve_plugin_storage_root(
    project_root: Path,
    name: str,
    scope: str | None,
) -> Path:
    return _resolve_named_storage_root(project_root, name, scope, "plugins")


def resolve_marketplace_storage_root(
    project_root: Path,
    name: str,
    scope: str | None,
) -> Path:
    return _resolve_named_storage_root(project_root, name, scope, "marketplaces")


def _resolve_named_storage_root(
    project_root: Path,
    name: str,
    scope: str | None,
    collection: Literal["plugins", "marketplaces"],
) -> Path:
    project = project_root.resolve()
    if scope == "user":
        return user_home()
    if scope in {"local", "project"}:
        return project
    if _state_contains(project, collection, name):
        return project
    user = user_home()
    if _state_contains(user, collection, name):
        return user
    return project


def _state_contains(
    store: Path,
    collection: Literal["plugins", "marketplaces"],
    name: str,
) -> bool:
    values = read_plugin_state(store).get(collection)
    return isinstance(values, dict) and isinstance(values.get(name), dict)


__all__ = [
    "VIBEAGENT_USER_HOME",
    "plugin_storage_root",
    "resolve_marketplace_storage_root",
    "resolve_plugin_storage_root",
    "user_home",
]
