from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re

from .plugin_store import enabled_plugin_manifests
from .plugin_types import PluginManifest
from .workspace_core import RunWorkspace
from .workspace_metadata_files import read_regular_file_bytes


MONITOR_CONFIG_MAX_BYTES = 128_000
MAX_PLUGIN_MONITORS = 100
MAX_MONITOR_COMMAND_CHARS = 4_000
MAX_MONITOR_DESCRIPTION_CHARS = 1_000
MONITOR_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
MONITOR_SKILL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
VARIABLE_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_.-]*)\}")


@dataclass(frozen=True)
class PluginMonitorConfig:
    name: str
    plugin: str
    command: str
    description: str
    when: str
    skill: str | None
    plugin_root: Path
    plugin_data: Path
    source: str


def read_plugin_monitor_configs(workspace: RunWorkspace) -> list[PluginMonitorConfig]:
    configs: list[PluginMonitorConfig] = []
    for manifest in enabled_plugin_manifests(workspace.root):
        seen: set[str] = set()
        for entries, source in _manifest_monitor_documents(manifest):
            for index, entry in enumerate(entries):
                config = _parse_monitor(workspace, manifest, entry, source, index)
                if config.name in seen:
                    raise ValueError(
                        f"Plugin {manifest.name} defines monitor {config.name!r} more than once."
                    )
                seen.add(config.name)
                configs.append(config)
                if len(configs) > MAX_PLUGIN_MONITORS:
                    raise ValueError(
                        f"Enabled plugins expose more than {MAX_PLUGIN_MONITORS} monitors."
                    )
    return sorted(configs, key=lambda item: (item.plugin, item.name))


def monitor_count_for_manifest(manifest: PluginManifest) -> int:
    return sum(len(entries) for entries, _source in _manifest_monitor_documents(manifest))


def _manifest_monitor_documents(
    manifest: PluginManifest,
) -> list[tuple[list[object], str]]:
    documents: list[tuple[list[object], str]] = []
    if manifest.inline_monitors is not None:
        documents.append((list(manifest.inline_monitors), ".claude-plugin/plugin.json#experimental.monitors"))
    for path in manifest.monitor_files:
        raw = read_regular_file_bytes(
            path, max_bytes=MONITOR_CONFIG_MAX_BYTES, label="plugin monitor config"
        )
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(f"Could not parse plugin monitor config {path}: {error}") from error
        if not isinstance(value, list) or not value:
            raise ValueError(f"Plugin monitor config must contain a non-empty JSON array: {path}")
        documents.append((value, path.relative_to(manifest.root).as_posix()))
    return documents


def _parse_monitor(
    workspace: RunWorkspace,
    manifest: PluginManifest,
    value: object,
    source: str,
    index: int,
) -> PluginMonitorConfig:
    label = f"Plugin {manifest.name} monitor {source}[{index}]"
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object.")
    extra = set(value) - {"name", "command", "description", "when"}
    if extra:
        raise ValueError(f"{label} has unsupported fields: {', '.join(sorted(map(str, extra)))}.")
    name = value.get("name")
    command = value.get("command")
    description = value.get("description")
    when = value.get("when", "always")
    if not isinstance(name, str) or not MONITOR_NAME_PATTERN.fullmatch(name):
        raise ValueError(f"{label} name must use 1-64 letters, digits, dots, underscores, or hyphens.")
    if (
        not isinstance(command, str)
        or not command.strip()
        or "\x00" in command
        or len(command) > MAX_MONITOR_COMMAND_CHARS
    ):
        raise ValueError(f"{label} command must be 1-{MAX_MONITOR_COMMAND_CHARS} safe characters.")
    if (
        not isinstance(description, str)
        or not description.strip()
        or len(description) > MAX_MONITOR_DESCRIPTION_CHARS
    ):
        raise ValueError(
            f"{label} description must be 1-{MAX_MONITOR_DESCRIPTION_CHARS} characters."
        )
    if not isinstance(when, str):
        raise ValueError(f"{label} when must be 'always' or 'on-skill-invoke:<skill-name>'.")
    skill = None
    if when != "always":
        prefix = "on-skill-invoke:"
        skill = when[len(prefix) :] if when.startswith(prefix) else None
        if skill is None or not MONITOR_SKILL_PATTERN.fullmatch(skill):
            raise ValueError(f"{label} when must be 'always' or 'on-skill-invoke:<skill-name>'.")
    data_dir = workspace.root / ".vibeagent" / "plugin-data" / manifest.name
    expanded = _expand_command(command.strip(), workspace, manifest.root, data_dir, label)
    return PluginMonitorConfig(
        name=name,
        plugin=manifest.name,
        command=expanded,
        description=" ".join(description.split()),
        when=when,
        skill=skill,
        plugin_root=manifest.root,
        plugin_data=data_dir,
        source=f"plugin:{manifest.name}/{source}",
    )


def _expand_command(
    command: str,
    workspace: RunWorkspace,
    plugin_root: Path,
    plugin_data: Path,
    label: str,
) -> str:
    values = {
        "CLAUDE_PLUGIN_ROOT": plugin_root.as_posix(),
        "CLAUDE_PLUGIN_DATA": plugin_data.as_posix(),
        "CLAUDE_PROJECT_DIR": workspace.root.as_posix(),
    }

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name.startswith("user_config."):
            raise ValueError(f"{label} uses unsupported plugin user configuration variable {name!r}.")
        if name in values:
            return values[name]
        return os.environ.get(name, "")

    return VARIABLE_PATTERN.sub(replace, command)


__all__ = [
    "PluginMonitorConfig",
    "monitor_count_for_manifest",
    "read_plugin_monitor_configs",
]
