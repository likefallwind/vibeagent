from __future__ import annotations

from dataclasses import dataclass
import shlex
from pathlib import Path

from .marketplace_commands import format_marketplace_details, handle_marketplace_command
from .marketplace_manifest import marketplace_manifest_exists, read_marketplace_manifest
from .marketplace_store import install_marketplace_plugin
from .plugin_manifest import read_plugin_manifest
from .plugin_monitor_config import monitor_count_for_manifest
from .plugin_store import (
    install_local_plugin,
    list_installed_plugins,
    read_installed_plugin_manifest,
    set_plugin_enabled,
    uninstall_plugin,
)
from .plugin_types import InstalledPlugin, MarketplaceManifest, PluginManifest
from .workspace_resolve import resolve_mutation_path


PLUGIN_USAGE = (
    "Usage: /plugin [list|details <name>|install <project-path|name@marketplace>|enable <name>|"
    "disable <name>|uninstall <name>|validate <project-path>|marketplace <operation>]"
)


@dataclass(frozen=True)
class PluginCommandResult:
    text: str
    changed: bool = False


def handle_plugin_command(project_root: Path, argument: str | None) -> PluginCommandResult:
    try:
        parts = shlex.split(argument or "")
    except ValueError as error:
        return PluginCommandResult(f"{PLUGIN_USAGE}\nError: {error}")
    try:
        if not parts or parts in (["list"], ["ls"]):
            return PluginCommandResult(format_plugin_list(list_installed_plugins(project_root)))
        if parts[0] in {"marketplace", "market"}:
            text, changed = handle_marketplace_command(project_root, parts[1:])
            return PluginCommandResult(text, changed=changed)
        if len(parts) != 2:
            return PluginCommandResult(PLUGIN_USAGE)
        operation, value = parts
        if operation == "install":
            plugin = (
                install_marketplace_plugin(project_root, value)
                if "@" in value
                else install_local_plugin(project_root, value)
            )
            source_suffix = f" from {plugin.marketplace}" if plugin.marketplace else ""
            return PluginCommandResult(
                f"Installed plugin {plugin.name}{_version_suffix(plugin.version)} "
                f"({'enabled' if plugin.enabled else 'disabled'}){source_suffix}.",
                changed=True,
            )
        if operation == "enable":
            plugin = set_plugin_enabled(project_root, value, True)
            return PluginCommandResult(f"Enabled plugin {plugin.name}.", changed=True)
        if operation == "disable":
            plugin = set_plugin_enabled(project_root, value, False)
            return PluginCommandResult(f"Disabled plugin {plugin.name}.", changed=True)
        if operation == "uninstall":
            plugin = uninstall_plugin(project_root, value)
            return PluginCommandResult(f"Uninstalled plugin {plugin.name}.", changed=True)
        if operation == "details":
            return PluginCommandResult(format_plugin_details(read_installed_plugin_manifest(project_root, value)))
        if operation == "validate":
            source = resolve_mutation_path(project_root, value)
            if marketplace_manifest_exists(source):
                return PluginCommandResult(format_marketplace_validation(read_marketplace_manifest(source)))
            return PluginCommandResult(format_plugin_validation(read_plugin_manifest(source)))
        return PluginCommandResult(PLUGIN_USAGE)
    except (OSError, UnicodeError, ValueError) as error:
        return PluginCommandResult(f"Plugin error: {error}")


def reload_plugins_text(project_root: Path) -> str:
    plugins = list_installed_plugins(project_root)
    enabled = [plugin for plugin in plugins if plugin.enabled and plugin.error is None]
    errors = [plugin for plugin in plugins if plugin.error is not None]
    totals = {
        "skills": 0,
        "commands": 0,
        "agents": 0,
        "hooks": 0,
        "MCP servers": 0,
        "LSP servers": 0,
        "executables": 0,
        "monitors": 0,
        "default agents": 0,
    }
    for plugin in enabled:
        manifest = read_installed_plugin_manifest(project_root, plugin.name)
        totals["skills"] += len(manifest.skill_files)
        totals["commands"] += len(manifest.command_files)
        totals["agents"] += len(manifest.agent_files)
        totals["hooks"] += len(manifest.hook_files)
        totals["MCP servers"] += len(manifest.mcp_files)
        totals["LSP servers"] += _lsp_server_count(manifest)
        totals["executables"] += len(manifest.bin_files)
        totals["monitors"] += monitor_count_for_manifest(manifest)
        totals["default agents"] += 1 if manifest.default_agent is not None else 0
    counts = ", ".join(f"{name}={count}" for name, count in totals.items())
    return f"Reloaded {len(enabled)} enabled plugin(s): {counts}; errors={len(errors)}."


def format_plugin_list(plugins: list[InstalledPlugin]) -> str:
    if not plugins:
        return "No plugins installed."
    lines = ["Installed plugins:"]
    for plugin in plugins:
        status = "error" if plugin.error else ("enabled" if plugin.enabled else "disabled")
        origin = f" @{plugin.marketplace}" if plugin.marketplace else ""
        lines.append(
            f"  {plugin.name}{_version_suffix(plugin.version)}{origin}  "
            f"{status:<8} components={plugin.component_count}  {plugin.description}"
        )
        if plugin.error:
            lines.append(f"    error: {plugin.error}")
    return "\n".join(lines)


def format_plugin_details(manifest: PluginManifest) -> str:
    lines = [
        f"Plugin {manifest.name}{_version_suffix(manifest.version)}",
        f"  description: {manifest.description or '(none)'}",
        f"  root: {manifest.root.as_posix()}",
        f"  skills: {len(manifest.skill_files)}",
        f"  commands: {len(manifest.command_files)}",
        f"  agents: {len(manifest.agent_files)}",
        f"  hooks: {len(manifest.hook_files)}",
        f"  MCP configs: {len(manifest.mcp_files)}",
        f"  LSP configs: {len(manifest.lsp_files) + (1 if manifest.inline_lsp_servers is not None else 0)}",
        f"  executables: {len(manifest.bin_files)}",
        f"  monitors: {monitor_count_for_manifest(manifest)}",
        f"  default agent: {manifest.default_agent or '(none)'}",
        f"  default settings source: {manifest.default_settings_source or '(none)'}",
    ]
    lines.extend(f"  warning: {warning}" for warning in manifest.warnings)
    return "\n".join(lines)


def format_plugin_validation(manifest: PluginManifest) -> str:
    status = "passed with warnings" if manifest.warnings else "passed"
    return f"Plugin validation {status}.\n{format_plugin_details(manifest)}"


def format_marketplace_validation(manifest: MarketplaceManifest) -> str:
    return f"Marketplace validation passed.\n{format_marketplace_details(manifest)}"


def _version_suffix(version: str | None) -> str:
    return f" {version}" if version else ""


def _lsp_server_count(manifest: PluginManifest) -> int:
    from .lsp_config import lsp_server_count_for_manifest

    try:
        return lsp_server_count_for_manifest(manifest)
    except (OSError, UnicodeError, ValueError):
        return 0


__all__ = [
    "PLUGIN_USAGE",
    "PluginCommandResult",
    "format_plugin_details",
    "format_plugin_list",
    "handle_plugin_command",
    "reload_plugins_text",
]
