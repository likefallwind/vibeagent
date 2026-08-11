from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re

from .plugin_runtime import (
    PluginComponentFile,
    expand_plugin_path_variables,
    plugin_subprocess_environment,
    resolve_plugin_component_user_config,
)
from .plugin_store import enabled_plugin_manifests
from .plugin_types import PluginManifest
from .plugin_user_config import ResolvedPluginUserConfig
from .workspace_core import RunWorkspace
from .workspace_environment import workspace_process_environment
from .workspace_metadata_files import has_symlink_component, read_regular_file_bytes
from .workspace_paths import is_protected_project_path


LSP_CONFIG_MAX_BYTES = 128_000
LSP_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
LSP_EXTENSION_PATTERN = re.compile(r"^\.[A-Za-z0-9][A-Za-z0-9._+-]{0,31}$")
LSP_LANGUAGE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$")
LSP_ENV_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")
ENV_REFERENCE_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


@dataclass(frozen=True)
class LspServerConfig:
    name: str
    plugin: str
    command: str
    args: tuple[str, ...]
    env: dict[str, str]
    extension_to_language: dict[str, str]
    initialization_options: dict[str, object]
    settings: dict[str, object]
    workspace_folder: Path
    startup_timeout_ms: int
    shutdown_timeout_ms: int
    restart_on_crash: bool
    max_restarts: int
    config_path: str
    plugin_environment: dict[str, str] = field(default_factory=dict)
    process_environment: dict[str, str] = field(default_factory=dict)

    @property
    def argv(self) -> tuple[str, ...]:
        environment = {
            **(self.process_environment or os.environ),
            **self.plugin_environment,
        }
        return tuple(
            ENV_REFERENCE_PATTERN.sub(
                lambda match: environment.get(match.group(1), ""),
                value,
            )
            for value in (self.command, *self.args)
        )


def read_lsp_server_configs(workspace: RunWorkspace) -> list[LspServerConfig]:
    configs: list[LspServerConfig] = []
    seen: dict[str, str] = {}
    for manifest in enabled_plugin_manifests(workspace.root, workspace=workspace):
        for document, label in _manifest_documents(manifest):
            for name, value in document.items():
                selected = _parse_server(workspace, manifest, name, value, label)
                if selected.name in seen:
                    raise ValueError(
                        f"LSP server {selected.name!r} is defined in both "
                        f"{seen[selected.name]} and {selected.config_path}."
                    )
                seen[selected.name] = selected.config_path
                configs.append(selected)
    return sorted(configs, key=lambda item: item.name)


def lsp_server_count_for_manifest(manifest: PluginManifest) -> int:
    return sum(len(document) for document, _label in _manifest_documents(manifest))


def select_lsp_server(workspace: RunWorkspace, path: Path) -> LspServerConfig | None:
    return select_lsp_server_from_configs(read_lsp_server_configs(workspace), path)


def select_lsp_server_from_configs(
    configs: list[LspServerConfig], path: Path
) -> LspServerConfig | None:
    extension = path.suffix.lower()
    matches = [
        config
        for config in configs
        if extension in {item.lower() for item in config.extension_to_language}
    ]
    if len(matches) > 1:
        names = ", ".join(config.name for config in matches)
        raise ValueError(f"Multiple enabled LSP servers claim {extension}: {names}.")
    return matches[0] if matches else None


def _manifest_documents(manifest: PluginManifest) -> list[tuple[dict[str, object], str]]:
    documents: list[tuple[dict[str, object], str]] = []
    if manifest.inline_lsp_servers is not None:
        documents.append((manifest.inline_lsp_servers, ".claude-plugin/plugin.json#lspServers"))
    for path in manifest.lsp_files:
        raw = read_regular_file_bytes(path, max_bytes=LSP_CONFIG_MAX_BYTES, label="LSP config")
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(f"Could not parse LSP config {path}: {error}") from error
        if not isinstance(value, dict):
            raise ValueError(f"LSP config must contain a JSON object: {path}")
        servers = value.get("lspServers", value)
        if not isinstance(servers, dict):
            raise ValueError(f"LSP config lspServers must be an object: {path}")
        documents.append((servers, path.relative_to(manifest.root).as_posix()))
    return documents


def _parse_server(
    workspace: RunWorkspace,
    manifest: PluginManifest,
    name: object,
    value: object,
    label: str,
) -> LspServerConfig:
    if not isinstance(name, str) or not LSP_NAME_PATTERN.fullmatch(name):
        raise ValueError("LSP server names must use 1-64 letters, digits, dots, underscores, or hyphens.")
    if not isinstance(value, dict):
        raise ValueError(f"LSP server {name!r} configuration must be an object.")
    component = PluginComponentFile(manifest.name, "lsp", manifest.root / label, manifest.root)
    user_config = resolve_plugin_component_user_config(workspace, component)
    expanded = _expand_value(value, component, workspace, user_config)
    plugin_environment = plugin_subprocess_environment(
        workspace,
        component,
        user_config=user_config,
    )
    process_environment = workspace_process_environment(workspace)
    assert isinstance(expanded, dict)
    command = expanded.get("command")
    args = expanded.get("args", [])
    env = expanded.get("env", {})
    extensions = expanded.get("extensionToLanguage")
    transport = expanded.get("transport", "stdio")
    if transport != "stdio":
        raise ValueError(f"LSP server {name!r} transport must be 'stdio'; socket is not supported.")
    if not isinstance(command, str) or not command.strip() or "\x00" in command:
        raise ValueError(f"LSP server {name!r} requires a non-empty command.")
    if not isinstance(args, list) or len(args) > 100 or any(
        not isinstance(item, str) or "\x00" in item for item in args
    ):
        raise ValueError(f"LSP server {name!r} args must be a list of at most 100 strings.")
    if not isinstance(env, dict) or len(env) > 100 or any(
        not isinstance(key, str)
        or not LSP_ENV_NAME_PATTERN.fullmatch(key)
        or not isinstance(item, str)
        or "\x00" in item
        for key, item in env.items()
    ):
        raise ValueError(f"LSP server {name!r} env must map at most 100 string names to string values.")
    if not isinstance(extensions, dict) or not extensions or len(extensions) > 100:
        raise ValueError(f"LSP server {name!r} requires a non-empty extensionToLanguage object.")
    if any(
        not isinstance(extension, str)
        or not LSP_EXTENSION_PATTERN.fullmatch(extension)
        or not isinstance(language, str)
        or not LSP_LANGUAGE_PATTERN.fullmatch(language)
        for extension, language in extensions.items()
    ):
        raise ValueError(f"LSP server {name!r} has an invalid extensionToLanguage entry.")
    initialization = _object_option(expanded, "initializationOptions", name)
    settings = _object_option(expanded, "settings", name)
    workspace_folder = _workspace_folder(workspace, manifest.root, expanded.get("workspaceFolder"), name)
    startup = _bounded_int(expanded.get("startupTimeout", 10_000), "startupTimeout", name, 100, 120_000)
    shutdown = _bounded_int(expanded.get("shutdownTimeout", 2_000), "shutdownTimeout", name, 100, 30_000)
    restart = expanded.get("restartOnCrash", False)
    max_restarts = _bounded_int(expanded.get("maxRestarts", 0), "maxRestarts", name, 0, 10)
    if not isinstance(restart, bool):
        raise ValueError(f"LSP server {name!r} restartOnCrash must be a boolean.")
    return LspServerConfig(
        name=f"{manifest.name}.{name}",
        plugin=manifest.name,
        command=command.strip(),
        args=tuple(args),
        env=dict(env),
        extension_to_language=dict(extensions),
        initialization_options=initialization,
        settings=settings,
        workspace_folder=workspace_folder,
        startup_timeout_ms=startup,
        shutdown_timeout_ms=shutdown,
        restart_on_crash=restart,
        max_restarts=max_restarts,
        config_path=f"plugin:{manifest.name}/{label}",
        plugin_environment=plugin_environment,
        process_environment=process_environment,
    )


def _expand_value(
    value: object,
    component: PluginComponentFile,
    workspace: RunWorkspace,
    user_config: ResolvedPluginUserConfig,
) -> object:
    if isinstance(value, str):
        return expand_plugin_path_variables(
            value,
            component,
            workspace,
            sensitive="environment",
            user_config=user_config,
        )
    if isinstance(value, list):
        return [_expand_value(item, component, workspace, user_config) for item in value]
    if isinstance(value, dict):
        return {
            key: _expand_value(item, component, workspace, user_config)
            for key, item in value.items()
        }
    return value


def _object_option(value: dict[object, object], key: str, name: str) -> dict[str, object]:
    selected = value.get(key, {})
    if not isinstance(selected, dict) or any(not isinstance(item, str) for item in selected):
        raise ValueError(f"LSP server {name!r} {key} must be an object with string keys.")
    return dict(selected)


def _bounded_int(value: object, key: str, name: str, minimum: int, maximum: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
        raise ValueError(f"LSP server {name!r} {key} must be an integer from {minimum} to {maximum}.")
    return value


def _workspace_folder(workspace: RunWorkspace, plugin_root: Path, value: object, name: str) -> Path:
    if value is None:
        return workspace.root
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"LSP server {name!r} workspaceFolder must be a non-empty path.")
    candidate = Path(value)
    resolved = candidate.resolve() if candidate.is_absolute() else (workspace.root / candidate).resolve()
    project = workspace.root.resolve()
    plugin = plugin_root.resolve()
    inside_project = resolved == project or project in resolved.parents
    inside_plugin = resolved == plugin or plugin in resolved.parents
    if not inside_plugin and (not inside_project or is_protected_project_path(project, resolved)):
        raise ValueError(f"LSP server {name!r} workspaceFolder escapes the project or plugin root.")
    boundary = plugin if inside_plugin else project
    lexical = candidate if candidate.is_absolute() else workspace.root / candidate
    if has_symlink_component(boundary, lexical):
        raise ValueError(f"LSP server {name!r} workspaceFolder contains a symbolic link.")
    if not resolved.is_dir():
        raise ValueError(f"LSP server {name!r} workspaceFolder is not a directory: {value}.")
    return resolved


__all__ = [
    "LspServerConfig",
    "lsp_server_count_for_manifest",
    "read_lsp_server_configs",
    "select_lsp_server",
    "select_lsp_server_from_configs",
]
