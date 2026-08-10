from __future__ import annotations

from pathlib import Path

from .marketplace_store import (
    add_marketplace,
    list_installed_marketplaces,
    read_installed_marketplace_manifest,
    remove_marketplace,
    set_marketplace_auto_update,
    update_marketplace,
)
from .plugin_types import InstalledMarketplace, MarketplaceManifest
from .plugin_scope_settings import PluginScope, validate_plugin_scope


MARKETPLACE_USAGE = (
    "Usage: /plugin marketplace "
    "[list|add <project-path|owner/repo[#ref]|https-url>|details <name>|update [name]|"
    "auto-update <name> <on|off>|remove <name>] [--scope user|project]"
)


def handle_marketplace_command(project_root: Path, parts: list[str]) -> tuple[str, bool]:
    try:
        parts, scope = _extract_scope(parts)
    except ValueError:
        raise
    if not parts or parts in (["list"], ["ls"]):
        return format_marketplace_list(
            list_installed_marketplaces(project_root, scope=scope)
        ), False
    if parts == ["update"]:
        return _update_all_marketplaces(project_root, scope=scope)
    if len(parts) == 3 and parts[0] == "auto-update":
        _operation, name, value = parts
        normalized = value.lower()
        if normalized not in {"on", "off", "enable", "disable"}:
            return MARKETPLACE_USAGE, False
        marketplace = set_marketplace_auto_update(
            project_root,
            name,
            normalized in {"on", "enable"},
            scope=scope,
        )
        status = "enabled" if marketplace.auto_update else "disabled"
        return f"Automatic updates {status} for marketplace {marketplace.name}.", True
    if len(parts) != 2:
        return MARKETPLACE_USAGE, False
    operation, value = parts
    if operation == "add":
        marketplace = add_marketplace(project_root, value, scope=scope)
        return (
            f"Added marketplace {marketplace.name} with {marketplace.plugin_count} plugin(s)"
            f"{f' at {scope} scope' if scope is not None else ''}.",
            True,
        )
    if operation == "details":
        manifest = read_installed_marketplace_manifest(project_root, value, scope=scope)
        return format_marketplace_details(manifest), False
    if operation == "update":
        marketplace = update_marketplace(project_root, value, scope=scope)
        return (
            f"Updated marketplace {marketplace.name}; {marketplace.plugin_count} plugin(s) available.",
            True,
        )
    if operation in {"remove", "rm"}:
        marketplace = remove_marketplace(project_root, value, scope=scope)
        return f"Removed marketplace {marketplace.name} and its installed plugins.", True
    return MARKETPLACE_USAGE, False


def format_marketplace_list(marketplaces: list[InstalledMarketplace]) -> str:
    if not marketplaces:
        return "No marketplaces added."
    lines = ["Plugin marketplaces:"]
    for marketplace in marketplaces:
        status = "error" if marketplace.error else "ready"
        lines.append(
            f"  {marketplace.name}  {status:<5} plugins={marketplace.plugin_count}  "
            f"auto-update={'on' if marketplace.auto_update else 'off'}  "
            f"scope={marketplace.scope}  owner={marketplace.owner}  source={marketplace.source}"
        )
        if marketplace.error:
            lines.append(f"    error: {marketplace.error}")
    return "\n".join(lines)


def _update_all_marketplaces(
    project_root: Path,
    *,
    scope: PluginScope | None,
) -> tuple[str, bool]:
    marketplaces = list_installed_marketplaces(project_root, scope=scope)
    if not marketplaces:
        return "No marketplaces added.", False
    updated: list[str] = []
    errors: list[str] = []
    for marketplace in marketplaces:
        try:
            update_marketplace(project_root, marketplace.name, scope=scope)
        except (OSError, UnicodeError, ValueError) as error:
            errors.append(f"{marketplace.name}: {error}")
        else:
            updated.append(marketplace.name)
    lines = [f"Updated {len(updated)} marketplace(s): {', '.join(updated) or 'none'}."]
    lines.extend(f"  error: {error}" for error in errors)
    return "\n".join(lines), bool(updated)


def _extract_scope(parts: list[str]) -> tuple[list[str], PluginScope | None]:
    if len(parts) >= 2 and parts[-2] in {"--scope", "-s"}:
        scope = validate_plugin_scope(parts[-1])
        if scope == "local":
            raise ValueError("Marketplace scope must be user or project.")
        return parts[:-2], scope
    return parts, None


def format_marketplace_details(manifest: MarketplaceManifest) -> str:
    lines = [
        f"Marketplace {manifest.name}",
        f"  description: {manifest.description or '(none)'}",
        f"  owner: {manifest.owner}",
        f"  root: {manifest.root.as_posix()}",
        f"  plugins: {len(manifest.plugins)}",
    ]
    for plugin in manifest.plugins:
        version = f" {plugin.version}" if plugin.version else ""
        lines.append(f"    {plugin.name}{version}  {plugin.description}")
    return "\n".join(lines)


__all__ = [
    "MARKETPLACE_USAGE",
    "format_marketplace_details",
    "format_marketplace_list",
    "handle_marketplace_command",
]
