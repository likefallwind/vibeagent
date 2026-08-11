from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .plugin_manifest import read_plugin_manifest
from .plugin_store import enabled_plugin_manifests
from .plugin_types import PluginManifest
from .plugin_user_config import (
    PluginSensitiveExpansion,
    ResolvedPluginUserConfig,
    expand_plugin_user_config_variables,
    resolve_plugin_user_config,
)
from .workspace_core import RunWorkspace


PluginComponentKind = Literal["skill", "command", "agent", "hook", "mcp", "lsp", "bin", "monitor"]


@dataclass(frozen=True)
class PluginComponentFile:
    plugin: str
    kind: PluginComponentKind
    path: Path
    plugin_root: Path

    @property
    def source(self) -> str:
        return f"plugin:{self.plugin}"

    @property
    def relative_path(self) -> str:
        return self.path.relative_to(self.plugin_root).as_posix()


def inline_plugin_component(
    manifest: PluginManifest,
    kind: PluginComponentKind,
) -> PluginComponentFile:
    if manifest.manifest_path is None:
        raise ValueError(f"Inline plugin {kind} configuration requires plugin.json.")
    return PluginComponentFile(
        plugin=manifest.name,
        kind=kind,
        path=manifest.manifest_path,
        plugin_root=manifest.root,
    )


def enabled_plugin_component_files(
    workspace: RunWorkspace,
    kind: PluginComponentKind,
) -> list[PluginComponentFile]:
    attribute = {
        "skill": "skill_files",
        "command": "command_files",
        "agent": "agent_files",
        "hook": "hook_files",
        "mcp": "mcp_files",
        "lsp": "lsp_files",
        "bin": "bin_files",
        "monitor": "monitor_files",
    }[kind]
    components: list[PluginComponentFile] = []
    for manifest in enabled_plugin_manifests(workspace.root, workspace=workspace):
        for path in getattr(manifest, attribute):
            components.append(
                PluginComponentFile(
                    plugin=manifest.name,
                    kind=kind,
                    path=path,
                    plugin_root=manifest.root,
                )
            )
    return sorted(components, key=lambda item: (item.plugin, item.relative_path))


def plugin_component_path_reference(project_root: Path, path: Path) -> str:
    selected = path.resolve()
    try:
        return selected.relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return selected.as_posix()


def expand_plugin_path_variables(
    value: str,
    component: PluginComponentFile,
    workspace: RunWorkspace,
    *,
    sensitive: PluginSensitiveExpansion = "reject",
    user_config: ResolvedPluginUserConfig | None = None,
) -> str:
    plugin_data = workspace.root / ".vibeagent" / "plugin-data" / component.plugin
    expanded = (
        value.replace("${CLAUDE_PLUGIN_ROOT}", component.plugin_root.as_posix())
        .replace("${CLAUDE_PLUGIN_DATA}", plugin_data.as_posix())
        .replace("${CLAUDE_PROJECT_DIR}", workspace.root.as_posix())
    )
    config = user_config or resolve_plugin_component_user_config(workspace, component)
    return expand_plugin_user_config_variables(expanded, config, sensitive=sensitive)


def plugin_subprocess_environment(
    workspace: RunWorkspace,
    component: PluginComponentFile,
    *,
    user_config: ResolvedPluginUserConfig | None = None,
) -> dict[str, str]:
    config = user_config or resolve_plugin_component_user_config(workspace, component)
    plugin_data = workspace.root / ".vibeagent" / "plugin-data" / component.plugin
    return {
        "CLAUDE_PLUGIN_ROOT": component.plugin_root.as_posix(),
        "CLAUDE_PLUGIN_DATA": plugin_data.as_posix(),
        "CLAUDE_PROJECT_DIR": workspace.root.as_posix(),
        **config.environment,
    }


def resolve_plugin_component_user_config(
    workspace: RunWorkspace,
    component: PluginComponentFile,
) -> ResolvedPluginUserConfig:
    manifest = read_plugin_manifest(component.plugin_root)
    if manifest.name != component.plugin:
        raise ValueError(f"Plugin component identity mismatch: {component.plugin}")
    return resolve_plugin_user_config(workspace.root, manifest, workspace=workspace)


def plugin_component_for_path(
    workspace: RunWorkspace,
    path: Path,
    kind: PluginComponentKind,
) -> PluginComponentFile | None:
    selected = path.resolve()
    return next(
        (item for item in enabled_plugin_component_files(workspace, kind) if item.path.resolve() == selected),
        None,
    )


__all__ = [
    "PluginComponentFile",
    "enabled_plugin_component_files",
    "expand_plugin_path_variables",
    "inline_plugin_component",
    "plugin_component_path_reference",
    "plugin_subprocess_environment",
    "resolve_plugin_component_user_config",
    "plugin_component_for_path",
]
