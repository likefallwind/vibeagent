from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
from typing import Literal

from .plugin_store import list_installed_plugins, read_installed_plugin_manifest
from .plugin_types import PluginManifest, PluginUserConfigOption
from .plugin_user_config_schema import validate_plugin_user_config_value
from .plugin_user_config_store import (
    read_plugin_configured_values,
    unset_plugin_configured_value,
    write_plugin_configured_value,
)


PLUGIN_USER_VARIABLE_PATTERN = re.compile(r"\$\{user_config\.([A-Za-z_][A-Za-z0-9_]{0,63})\}")
PluginSensitiveExpansion = Literal["reject", "environment"]


@dataclass(frozen=True)
class ResolvedPluginUserConfig:
    plugin_id: str
    options: tuple[PluginUserConfigOption, ...]
    values: dict[str, object]
    sources: dict[str, str]
    missing_required: tuple[str, ...]

    @property
    def sensitive_keys(self) -> frozenset[str]:
        return frozenset(option.key for option in self.options if option.sensitive)

    @property
    def environment(self) -> dict[str, str]:
        return {
            plugin_option_environment_name(key): serialize_plugin_option(value)
            for key, value in self.values.items()
        }


def resolve_plugin_user_config(
    project_root: Path,
    manifest: PluginManifest,
    *,
    plugin_id: str | None = None,
) -> ResolvedPluginUserConfig:
    root = project_root.resolve()
    plugin_id = plugin_id or installed_plugin_id(root, manifest.name)
    aliases = (plugin_id,)
    configured, sources, settings_sources = read_plugin_configured_values(root, aliases)

    values: dict[str, object] = {}
    selected_sources: dict[str, str] = {}
    missing: list[str] = []
    for option in manifest.user_config:
        if option.sensitive and option.key in settings_sources:
            raise ValueError(
                f"Sensitive plugin option {option.key!r} must not be stored in "
                f"{settings_sources[option.key]}."
            )
        environment_name = plugin_option_environment_name(option.key)
        if environment_name in os.environ:
            raw = _parse_environment_value(option, os.environ[environment_name])
            source = f"environment:{environment_name}"
        elif option.key in configured:
            raw = configured[option.key]
            source = sources[option.key]
        elif option.has_default:
            raw = option.default
            source = "manifest default"
        else:
            if option.required:
                missing.append(option.key)
            continue
        try:
            values[option.key] = validate_plugin_user_config_value(option, raw)
        except ValueError as error:
            raise ValueError(
                f"Invalid value for plugin {manifest.name} option {option.key!r} from {source}: {error}"
            ) from error
        selected_sources[option.key] = source
    return ResolvedPluginUserConfig(
        plugin_id=plugin_id,
        options=manifest.user_config,
        values=values,
        sources=selected_sources,
        missing_required=tuple(sorted(missing)),
    )


def require_plugin_user_config(config: ResolvedPluginUserConfig) -> None:
    if config.missing_required:
        names = ", ".join(config.missing_required)
        raise ValueError(
            f"Plugin {config.plugin_id} is missing required user configuration: {names}. "
            f"Use /plugin config set {config.plugin_id.split('@', 1)[0]} <key> <json-value>."
        )


def expand_plugin_user_config_variables(
    value: str,
    config: ResolvedPluginUserConfig,
    *,
    sensitive: PluginSensitiveExpansion = "reject",
) -> str:
    require_plugin_user_config(config)
    options = {option.key: option for option in config.options}

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        option = options.get(key)
        if option is None:
            raise ValueError(f"Plugin {config.plugin_id} references undeclared user configuration {key!r}.")
        if key not in config.values:
            return ""
        if option.sensitive:
            if sensitive != "environment":
                raise ValueError(
                    f"Plugin {config.plugin_id} cannot substitute sensitive option {key!r} into model-visible content."
                )
            return "${" + plugin_option_environment_name(key) + "}"
        return serialize_plugin_option(config.values[key])

    return PLUGIN_USER_VARIABLE_PATTERN.sub(replace, value)


def set_plugin_user_config_value(
    project_root: Path,
    plugin_name: str,
    key: str,
    value: object,
) -> ResolvedPluginUserConfig:
    root = project_root.resolve()
    manifest = read_installed_plugin_manifest(root, plugin_name)
    option = _option(manifest, key)
    selected = validate_plugin_user_config_value(option, value)
    plugin_id = installed_plugin_id(root, manifest.name)
    if option.sensitive:
        # Refuse before writing when a shared settings file already exposes this secret.
        resolve_plugin_user_config(root, manifest, plugin_id=plugin_id)
    write_plugin_configured_value(
        root,
        plugin_id,
        key,
        selected,
        sensitive=option.sensitive,
    )
    return resolve_plugin_user_config(root, manifest)


def unset_plugin_user_config_value(
    project_root: Path,
    plugin_name: str,
    key: str,
) -> ResolvedPluginUserConfig:
    root = project_root.resolve()
    manifest = read_installed_plugin_manifest(root, plugin_name)
    _option(manifest, key)
    plugin_id = installed_plugin_id(root, manifest.name)
    unset_plugin_configured_value(root, plugin_id, key)
    return resolve_plugin_user_config(root, manifest)


def installed_plugin_id(project_root: Path, plugin_name: str) -> str:
    installed = next(
        (plugin for plugin in list_installed_plugins(project_root) if plugin.name == plugin_name),
        None,
    )
    if installed is None:
        raise ValueError(f"Plugin is not installed: {plugin_name}")
    return (
        f"{installed.name}@{installed.marketplace}"
        if installed.marketplace is not None
        else installed.name
    )


def plugin_option_environment_name(key: str) -> str:
    return f"CLAUDE_PLUGIN_OPTION_{key}"


def serialize_plugin_option(value: object) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _option(manifest: PluginManifest, key: str) -> PluginUserConfigOption:
    option = next((item for item in manifest.user_config if item.key == key), None)
    if option is None:
        raise ValueError(f"Plugin {manifest.name} does not declare user configuration {key!r}.")
    return option


def _parse_environment_value(option: PluginUserConfigOption, value: str) -> object:
    if option.type in {"string", "directory", "file"} and not option.multiple:
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Environment variable {plugin_option_environment_name(option.key)} must contain JSON for {option.type}."
        ) from error


__all__ = [
    "ResolvedPluginUserConfig",
    "expand_plugin_user_config_variables",
    "installed_plugin_id",
    "plugin_option_environment_name",
    "require_plugin_user_config",
    "resolve_plugin_user_config",
    "serialize_plugin_option",
    "set_plugin_user_config_value",
    "unset_plugin_user_config_value",
]
