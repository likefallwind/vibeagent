from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from .mcp_user_config import read_user_mcp_documents
from .plugin_runtime import (
    PluginComponentFile,
    enabled_plugin_component_files,
    inline_plugin_component,
)
from .plugin_store import enabled_plugin_manifests
from .workspace_core import RunWorkspace


if TYPE_CHECKING:
    from .mcp_config import McpServerConfig


McpPathReader = Callable[
    [RunWorkspace, Path, PluginComponentFile | None],
    list["McpServerConfig"],
]
McpDocumentReader = Callable[
    [RunWorkspace, object, str, PluginComponentFile | None],
    list["McpServerConfig"],
]


def read_scoped_mcp_server_configs(
    workspace: RunWorkspace,
    *,
    read_path: McpPathReader,
    read_document: McpDocumentReader,
) -> list[McpServerConfig]:
    from .mcp_config import MCP_CONFIG_NAME

    selected: dict[str, McpServerConfig] = {}
    explicit_paths = _deduped_paths(workspace.mcp_config_paths)
    if workspace.strict_mcp_config:
        _append_explicit_configs(
            workspace,
            selected,
            explicit_paths,
            read_path,
        )
        return sorted(selected.values(), key=lambda config: config.name)

    plugin_components = enabled_plugin_component_files(workspace, "mcp")
    for component in plugin_components:
        _merge_configs(
            selected,
            read_path(
                workspace,
                component.path,
                component,
            ),
            replace_existing=False,
        )
    for manifest in enabled_plugin_manifests(workspace.root, workspace=workspace):
        if manifest.inline_mcp_servers is None:
            continue
        component = inline_plugin_component(manifest, "mcp")
        label = f"{component.source}:{component.relative_path}#mcpServers"
        _merge_configs(
            selected,
            read_document(
                workspace,
                {"mcpServers": manifest.inline_mcp_servers},
                label,
                component,
            ),
            replace_existing=False,
        )

    scoped_documents = read_user_mcp_documents(workspace)
    user_document = next(
        (document for document in scoped_documents if document.scope == "user"),
        None,
    )
    local_document = next(
        (document for document in scoped_documents if document.scope == "local"),
        None,
    )
    if user_document is not None:
        _merge_configs(
            selected,
            read_document(
                workspace,
                user_document.document,
                user_document.source,
                None,
            ),
            replace_existing=True,
        )
    project_path = workspace.root / MCP_CONFIG_NAME
    if project_path.exists():
        _merge_configs(
            selected,
            read_path(workspace, project_path, None),
            replace_existing=True,
        )
    if local_document is not None:
        _merge_configs(
            selected,
            read_document(
                workspace,
                local_document.document,
                local_document.source,
                None,
            ),
            replace_existing=True,
        )

    implicit_paths = {
        project_path.resolve(),
        *(component.path.resolve() for component in plugin_components),
    }
    _append_explicit_configs(
        workspace,
        selected,
        [path for path in explicit_paths if path.resolve() not in implicit_paths],
        read_path,
    )
    return sorted(selected.values(), key=lambda config: config.name)


def _append_explicit_configs(
    workspace: RunWorkspace,
    selected: dict[str, McpServerConfig],
    paths: list[Path],
    read_config: McpPathReader,
) -> None:
    for path in paths:
        _merge_configs(
            selected,
            read_config(workspace, path, None),
            replace_existing=False,
        )


def _merge_configs(
    selected: dict[str, McpServerConfig],
    configs: list[McpServerConfig],
    *,
    replace_existing: bool,
) -> None:
    for config in configs:
        previous = selected.get(config.name)
        if previous is not None and not replace_existing:
            raise ValueError(
                f"MCP server {config.name!r} is defined in both "
                f"{previous.config_path} and {config.config_path}."
            )
        selected[config.name] = config


def _deduped_paths(paths: tuple[Path, ...]) -> list[Path]:
    deduped: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(path)
    return deduped


__all__ = ["read_scoped_mcp_server_configs"]
