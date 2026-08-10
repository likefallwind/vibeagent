from __future__ import annotations

from dataclasses import dataclass
import json
import shlex
from pathlib import Path

from .marketplace_commands import format_marketplace_details, handle_marketplace_command
from .marketplace_manifest import marketplace_manifest_exists, read_marketplace_manifest
from .marketplace_store import install_marketplace_plugin
from .plugin_manifest import read_plugin_manifest
from .plugin_monitor_config import monitor_count_for_manifest
from .plugin_scope_settings import PluginScope, validate_plugin_scope
from .plugin_store import (
    install_local_plugin,
    list_installed_plugins,
    read_installed_plugin_manifest,
    set_plugin_enabled,
    uninstall_plugin,
    update_installed_plugin,
)
from .plugin_types import InstalledPlugin, MarketplaceManifest, PluginManifest
from .plugin_user_config import (
    installed_plugin_id,
    require_plugin_user_config,
    resolve_plugin_user_config,
    serialize_plugin_option,
    set_plugin_user_config_value,
    unset_plugin_user_config_value,
)
from .workspace_resolve import resolve_mutation_path


PLUGIN_USAGE = (
    "Usage: /plugin [list|details <name>|install <project-path|name@marketplace> [--scope local|project|user]|"
    "enable <name> [--scope local|project|user]|disable <name> [--scope local|project|user]|"
    "update <name> [--scope local|project|user]|uninstall <name> [--scope local|project|user]|validate <project-path>|"
    "config <operation>|marketplace <operation>]"
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
        if parts[0] == "config":
            return _handle_plugin_config_command(project_root, parts[1:])
        parsed_operation = _parse_plugin_operation(parts)
        if parsed_operation is None:
            return PluginCommandResult(PLUGIN_USAGE)
        operation, value, scope = parsed_operation
        if operation == "install":
            plugin = (
                install_marketplace_plugin(project_root, value, scope=scope)
                if "@" in value
                else install_local_plugin(project_root, value, scope=scope)
            )
            source_suffix = f" from {plugin.marketplace}" if plugin.marketplace else ""
            manifest = read_installed_plugin_manifest(
                project_root,
                plugin.name,
                scope=scope,
            )
            config = resolve_plugin_user_config(
                project_root,
                manifest,
                plugin_id=(
                    f"{plugin.name}@{plugin.marketplace}"
                    if plugin.marketplace
                    else plugin.name
                ),
            )
            configuration_suffix = (
                f" Required configuration: {', '.join(config.missing_required)}; "
                f"use /plugin config {plugin.name}."
                if config.missing_required
                else ""
            )
            return PluginCommandResult(
                f"Installed plugin {plugin.name}{_version_suffix(plugin.version)} "
                f"({'enabled' if plugin.enabled else 'disabled'}){source_suffix}."
                f"{f' Scope: {scope}.' if scope is not None else ''}"
                f"{configuration_suffix}",
                changed=True,
            )
        if operation == "enable":
            manifest = read_installed_plugin_manifest(project_root, value, scope=scope)
            require_plugin_user_config(
                resolve_plugin_user_config(
                    project_root,
                    manifest,
                    plugin_id=installed_plugin_id(project_root, value, scope=scope),
                )
            )
            plugin = set_plugin_enabled(project_root, value, True, scope=scope)
            suffix = f" at {scope} scope" if scope is not None else ""
            return PluginCommandResult(f"Enabled plugin {plugin.name}{suffix}.", changed=True)
        if operation == "disable":
            plugin = set_plugin_enabled(project_root, value, False, scope=scope)
            suffix = f" at {scope} scope" if scope is not None else ""
            return PluginCommandResult(f"Disabled plugin {plugin.name}{suffix}.", changed=True)
        if operation == "update":
            result = update_installed_plugin(project_root, value, scope=scope)
            if not result.updated:
                return PluginCommandResult(
                    f"Plugin {result.plugin.name}{_version_suffix(result.plugin.version)} is already current."
                )
            previous = _version_suffix(result.previous_version).strip() or "unversioned"
            current = _version_suffix(result.plugin.version).strip() or "unversioned"
            return PluginCommandResult(
                f"Updated plugin {result.plugin.name}: {previous} -> {current}.",
                changed=True,
            )
        if operation == "uninstall":
            plugin = uninstall_plugin(project_root, value, scope=scope)
            suffix = f" from {scope} scope" if scope is not None else ""
            return PluginCommandResult(f"Uninstalled plugin {plugin.name}{suffix}.", changed=True)
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
        totals["hooks"] += len(manifest.hook_files) + (manifest.inline_hooks is not None)
        totals["MCP servers"] += len(manifest.mcp_files) + (manifest.inline_mcp_servers is not None)
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
        scopes = f" scopes={','.join(plugin.scopes)}" if plugin.scopes else ""
        lines.append(
            f"  {plugin.name}{_version_suffix(plugin.version)}{origin}  "
            f"{status:<8} components={plugin.component_count}{scopes}  {plugin.description}"
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
        f"  hooks: {len(manifest.hook_files) + (manifest.inline_hooks is not None)}",
        f"  MCP configs: {len(manifest.mcp_files) + (manifest.inline_mcp_servers is not None)}",
        f"  LSP configs: {len(manifest.lsp_files) + (1 if manifest.inline_lsp_servers is not None else 0)}",
        f"  executables: {len(manifest.bin_files)}",
        f"  monitors: {monitor_count_for_manifest(manifest)}",
        f"  default agent: {manifest.default_agent or '(none)'}",
        f"  subagent status line: {'command' if manifest.has_subagent_status_line else '(none)'}",
        f"  default settings source: {manifest.default_settings_source or '(none)'}",
        f"  user configuration options: {len(manifest.user_config)}",
    ]
    lines.extend(
        f"  user option: {option.key} ({option.type}, "
        f"{'required' if option.required else 'optional'}, "
        f"{'sensitive' if option.sensitive else 'shared'})"
        for option in manifest.user_config
    )
    lines.extend(f"  warning: {warning}" for warning in manifest.warnings)
    return "\n".join(lines)


def format_plugin_validation(manifest: PluginManifest) -> str:
    status = "passed with warnings" if manifest.warnings else "passed"
    return f"Plugin validation {status}.\n{format_plugin_details(manifest)}"


def format_marketplace_validation(manifest: MarketplaceManifest) -> str:
    return f"Marketplace validation passed.\n{format_marketplace_details(manifest)}"


def _version_suffix(version: str | None) -> str:
    return f" {version}" if version else ""


def _parse_plugin_operation(
    parts: list[str],
) -> tuple[str, str, PluginScope | None] | None:
    if len(parts) == 2:
        return parts[0], parts[1], None
    if len(parts) != 4 or parts[0] not in {
        "install",
        "enable",
        "disable",
        "update",
        "uninstall",
    }:
        return None
    if parts[2] in {"--scope", "-s"}:
        return parts[0], parts[1], validate_plugin_scope(parts[3])
    if parts[1] in {"--scope", "-s"}:
        return parts[0], parts[3], validate_plugin_scope(parts[2])
    return None


def _handle_plugin_config_command(
    project_root: Path,
    parts: list[str],
) -> PluginCommandResult:
    parts, scope = _extract_config_scope(parts)
    if len(parts) == 1:
        manifest = read_installed_plugin_manifest(project_root, parts[0], scope=scope)
        return PluginCommandResult(
            _format_plugin_user_config(project_root, manifest, scope=scope)
        )
    if len(parts) == 4 and parts[0] == "set":
        _operation, plugin_name, key, encoded = parts
        try:
            value = json.loads(encoded)
        except json.JSONDecodeError:
            value = encoded
        config = set_plugin_user_config_value(
            project_root,
            plugin_name,
            key,
            value,
            scope=scope,
        )
        option = next(item for item in config.options if item.key == key)
        if option.sensitive:
            storage = "user protected credentials" if scope == "user" else "protected credentials"
        elif scope == "user":
            storage = "~/.claude/settings.json"
        elif scope == "project":
            storage = ".claude/settings.json"
        else:
            storage = ".claude/settings.local.json"
        return PluginCommandResult(
            f"Configured plugin {plugin_name} option {key} in {storage}.",
            changed=True,
        )
    if len(parts) == 3 and parts[0] == "unset":
        _operation, plugin_name, key = parts
        unset_plugin_user_config_value(
            project_root,
            plugin_name,
            key,
            scope=scope,
        )
        return PluginCommandResult(
            f"Cleared local plugin {plugin_name} option {key}.",
            changed=True,
        )
    return PluginCommandResult(
        "Usage: /plugin config <name> | /plugin config set <name> <key> <json-value> | "
        "/plugin config unset <name> <key> [--scope local|project|user]"
    )


def _extract_config_scope(parts: list[str]) -> tuple[list[str], PluginScope | None]:
    if len(parts) >= 2 and parts[-2] in {"--scope", "-s"}:
        return parts[:-2], validate_plugin_scope(parts[-1])
    return parts, None


def _format_plugin_user_config(
    project_root: Path,
    manifest: PluginManifest,
    *,
    scope: PluginScope | None = None,
) -> str:
    config = resolve_plugin_user_config(
        project_root,
        manifest,
        plugin_id=installed_plugin_id(project_root, manifest.name, scope=scope),
    )
    lines = [
        f"Plugin configuration {manifest.name}",
        f"  plugin id: {config.plugin_id}",
    ]
    if not config.options:
        lines.append("  no user configuration declared")
        return "\n".join(lines)
    for option in config.options:
        if option.key not in config.values:
            status = "missing required" if option.required else "unset"
            value = ""
        else:
            status = "configured"
            rendered = (
                "<redacted>"
                if option.sensitive
                else serialize_plugin_option(config.values[option.key])
            )
            value = f" value={rendered!r} source={config.sources[option.key]}"
        lines.append(
            f"  {option.key}: {status} type={option.type} "
            f"sensitive={'yes' if option.sensitive else 'no'}{value}"
        )
    return "\n".join(lines)


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
