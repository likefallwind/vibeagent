from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .plugin_store import enabled_plugin_manifests
from .workspace_core import RunWorkspace


PluginComponentKind = Literal["skill", "command", "agent", "hook", "mcp", "lsp"]


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
    }[kind]
    components: list[PluginComponentFile] = []
    for manifest in enabled_plugin_manifests(workspace.root):
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


def expand_plugin_path_variables(
    value: str,
    component: PluginComponentFile,
    workspace: RunWorkspace,
) -> str:
    return (
        value.replace("${CLAUDE_PLUGIN_ROOT}", component.plugin_root.as_posix())
        .replace("${CLAUDE_PROJECT_DIR}", workspace.root.as_posix())
    )


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
    "plugin_component_for_path",
]
