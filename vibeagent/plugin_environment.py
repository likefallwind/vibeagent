from __future__ import annotations

import os
from pathlib import Path

from .plugin_runtime import enabled_plugin_component_files
from .workspace_core import RunWorkspace
from .workspace_metadata_files import has_symlink_component


def enabled_plugin_bin_paths(workspace: RunWorkspace) -> tuple[Path, ...]:
    paths: list[Path] = []
    for component in enabled_plugin_component_files(workspace, "bin"):
        directory = component.path.parent
        if directory in paths:
            continue
        if (
            has_symlink_component(component.plugin_root, directory)
            or directory.is_symlink()
            or not directory.is_dir()
        ):
            raise ValueError(f"Plugin {component.plugin} bin path is not a safe directory.")
        paths.append(directory)
    return tuple(paths)


def plugin_command_environment(workspace: RunWorkspace) -> dict[str, str]:
    environment = dict(os.environ)
    plugin_paths = enabled_plugin_bin_paths(workspace)
    if not plugin_paths:
        return environment
    current_path = environment.get("PATH", "")
    entries = [path.as_posix() for path in plugin_paths]
    if current_path:
        entries.append(current_path)
    environment["PATH"] = os.pathsep.join(entries)
    return environment


def plugin_command_search_path(workspace: RunWorkspace) -> str:
    return plugin_command_environment(workspace).get("PATH", "")


__all__ = [
    "enabled_plugin_bin_paths",
    "plugin_command_environment",
    "plugin_command_search_path",
]
