from __future__ import annotations

from dataclasses import dataclass
import shlex
from pathlib import Path

from .plugin_manifest import read_plugin_manifest
from .plugin_store import (
    install_local_plugin,
    list_installed_plugins,
    read_installed_plugin_manifest,
    set_plugin_enabled,
    uninstall_plugin,
)
from .plugin_types import InstalledPlugin, PluginManifest
from .workspace_resolve import resolve_mutation_path


PLUGIN_USAGE = (
    "Usage: /plugin [list|details <name>|install <project-path>|enable <name>|disable <name>|"
    "uninstall <name>|validate <project-path>]"
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
        if len(parts) != 2:
            return PluginCommandResult(PLUGIN_USAGE)
        operation, value = parts
        if operation == "install":
            plugin = install_local_plugin(project_root, value)
            return PluginCommandResult(
                f"Installed plugin {plugin.name}{_version_suffix(plugin.version)} "
                f"({'enabled' if plugin.enabled else 'disabled'}).",
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
            return PluginCommandResult(format_plugin_validation(read_plugin_manifest(source)))
        return PluginCommandResult(PLUGIN_USAGE)
    except (OSError, UnicodeError, ValueError) as error:
        return PluginCommandResult(f"Plugin error: {error}")


def reload_plugins_text(project_root: Path) -> str:
    plugins = list_installed_plugins(project_root)
    enabled = [plugin for plugin in plugins if plugin.enabled and plugin.error is None]
    errors = [plugin for plugin in plugins if plugin.error is not None]
    totals = {"skills": 0, "commands": 0, "agents": 0, "hooks": 0, "MCP servers": 0}
    for plugin in enabled:
        manifest = read_installed_plugin_manifest(project_root, plugin.name)
        totals["skills"] += len(manifest.skill_files)
        totals["commands"] += len(manifest.command_files)
        totals["agents"] += len(manifest.agent_files)
        totals["hooks"] += len(manifest.hook_files)
        totals["MCP servers"] += len(manifest.mcp_files)
    counts = ", ".join(f"{name}={count}" for name, count in totals.items())
    return f"Reloaded {len(enabled)} enabled plugin(s): {counts}; errors={len(errors)}."


def format_plugin_list(plugins: list[InstalledPlugin]) -> str:
    if not plugins:
        return "No plugins installed."
    lines = ["Installed plugins:"]
    for plugin in plugins:
        status = "error" if plugin.error else ("enabled" if plugin.enabled else "disabled")
        lines.append(
            f"  {plugin.name}{_version_suffix(plugin.version)}  {status:<8} components={plugin.component_count}  {plugin.description}"
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
    ]
    lines.extend(f"  warning: {warning}" for warning in manifest.warnings)
    return "\n".join(lines)


def format_plugin_validation(manifest: PluginManifest) -> str:
    status = "passed with warnings" if manifest.warnings else "passed"
    return f"Plugin validation {status}.\n{format_plugin_details(manifest)}"


def _version_suffix(version: str | None) -> str:
    return f" {version}" if version else ""


__all__ = [
    "PLUGIN_USAGE",
    "PluginCommandResult",
    "format_plugin_details",
    "format_plugin_list",
    "handle_plugin_command",
    "reload_plugins_text",
]
