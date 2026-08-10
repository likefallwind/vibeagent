from __future__ import annotations

from pathlib import Path

from .marketplace_store import (
    add_local_marketplace,
    list_installed_marketplaces,
    read_installed_marketplace_manifest,
    remove_marketplace,
    update_local_marketplace,
)
from .plugin_types import InstalledMarketplace, MarketplaceManifest


MARKETPLACE_USAGE = (
    "Usage: /plugin marketplace "
    "[list|add <project-path>|details <name>|update <name>|remove <name>]"
)


def handle_marketplace_command(project_root: Path, parts: list[str]) -> tuple[str, bool]:
    if not parts or parts in (["list"], ["ls"]):
        return format_marketplace_list(list_installed_marketplaces(project_root)), False
    if len(parts) != 2:
        return MARKETPLACE_USAGE, False
    operation, value = parts
    if operation == "add":
        marketplace = add_local_marketplace(project_root, value)
        return (
            f"Added marketplace {marketplace.name} with {marketplace.plugin_count} plugin(s).",
            True,
        )
    if operation == "details":
        manifest = read_installed_marketplace_manifest(project_root, value)
        return format_marketplace_details(manifest), False
    if operation == "update":
        marketplace = update_local_marketplace(project_root, value)
        return (
            f"Updated marketplace {marketplace.name}; {marketplace.plugin_count} plugin(s) available.",
            True,
        )
    if operation in {"remove", "rm"}:
        marketplace = remove_marketplace(project_root, value)
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
            f"owner={marketplace.owner}  source={marketplace.source}"
        )
        if marketplace.error:
            lines.append(f"    error: {marketplace.error}")
    return "\n".join(lines)


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
