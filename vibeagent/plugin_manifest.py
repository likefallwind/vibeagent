from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from .plugin_default_settings import read_plugin_default_settings
from .plugin_types import PluginManifest
from .plugin_user_config_schema import parse_plugin_user_config
from .workspace_metadata_files import has_symlink_component, read_regular_file_bytes


PLUGIN_NAME_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
PLUGIN_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+_-]{0,63}$")
MAX_PLUGIN_MANIFEST_BYTES = 128_000
MAX_PLUGIN_COMPONENTS = 1_000
MAX_PLUGIN_COMPONENT_DEPTH = 8


def read_plugin_manifest(plugin_root: Path) -> PluginManifest:
    root = plugin_root.resolve()
    if plugin_root.is_symlink() or not root.is_dir():
        raise ValueError(f"Plugin root must be a regular directory: {plugin_root}")
    manifest_path = root / ".claude-plugin" / "plugin.json"
    payload: dict[str, Any] = {}
    if manifest_path.exists() or manifest_path.is_symlink():
        if has_symlink_component(root, manifest_path) or not manifest_path.is_file():
            raise ValueError(".claude-plugin/plugin.json must be a regular non-symlink file.")
        raw = read_regular_file_bytes(
            manifest_path,
            max_bytes=MAX_PLUGIN_MANIFEST_BYTES,
            label="plugin.json",
        )
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(f"Could not parse plugin.json: {error}") from error
        if not isinstance(parsed, dict):
            raise ValueError("plugin.json must contain a JSON object.")
        payload = parsed
    else:
        manifest_path = None

    name = payload.get("name", root.name)
    if not isinstance(name, str) or not PLUGIN_NAME_PATTERN.fullmatch(name):
        raise ValueError("Plugin name must be 1-64 lowercase letters, digits, or hyphens.")
    description = payload.get("description", "")
    if not isinstance(description, str) or len(description) > 1_000:
        raise ValueError("Plugin description must be a string of at most 1000 characters.")
    version = payload.get("version")
    if version is not None and (
        not isinstance(version, str) or not PLUGIN_VERSION_PATTERN.fullmatch(version)
    ):
        raise ValueError("Plugin version must use 1-64 letters, digits, dots, pluses, underscores, or hyphens.")
    default_enabled = payload.get("defaultEnabled", True)
    if not isinstance(default_enabled, bool):
        raise ValueError("Plugin defaultEnabled must be a boolean.")

    skills = _component_files(root, payload, "skills", "skills", kind="skills")
    if "skills" not in payload and not skills and (root / "SKILL.md").is_file():
        skills = (root / "SKILL.md",)
    commands = _component_files(root, payload, "commands", "commands", kind="markdown")
    agents = _component_files(root, payload, "agents", "agents", kind="markdown")
    hooks = _config_files(root, payload, "hooks", "hooks/hooks.json")
    mcp = _config_files(root, payload, "mcpServers", ".mcp.json")
    inline_lsp = payload.get("lspServers") if isinstance(payload.get("lspServers"), dict) else None
    lsp = () if inline_lsp is not None else _config_files(root, payload, "lspServers", ".lsp.json")
    executables = _executable_files(root)
    monitor_files, inline_monitors = _monitor_components(root, payload)
    user_config = parse_plugin_user_config(payload.get("userConfig"))
    default_settings = read_plugin_default_settings(root, payload, tuple(agents))
    warnings = list(default_settings.warnings)

    all_components = (*skills, *commands, *agents, *hooks, *mcp, *lsp, *executables, *monitor_files)
    component_count = (
        len(all_components)
        + (1 if inline_lsp is not None else 0)
        + len(inline_monitors or ())
        + (1 if default_settings.enabled else 0)
        + (1 if user_config else 0)
    )
    if component_count > MAX_PLUGIN_COMPONENTS:
        raise ValueError(f"Plugin exposes more than {MAX_PLUGIN_COMPONENTS} components.")
    if len(set(all_components)) != len(all_components):
        raise ValueError("Plugin manifest resolves the same component file more than once.")
    return PluginManifest(
        name=name,
        description=" ".join(description.split()),
        version=version,
        default_enabled=default_enabled,
        root=root,
        manifest_path=manifest_path,
        skill_files=tuple(skills),
        command_files=tuple(commands),
        agent_files=tuple(agents),
        hook_files=tuple(hooks),
        mcp_files=tuple(mcp),
        lsp_files=tuple(lsp),
        bin_files=tuple(executables),
        monitor_files=tuple(monitor_files),
        user_config=user_config,
        inline_lsp_servers=dict(inline_lsp) if inline_lsp is not None else None,
        inline_monitors=inline_monitors,
        default_agent=default_settings.agent,
        default_settings_source=default_settings.source,
        subagent_status_line=default_settings.subagent_status_line,
        warnings=tuple(warnings),
    )


def _component_files(
    root: Path,
    payload: dict[str, Any],
    key: str,
    default: str,
    *,
    kind: str,
) -> tuple[Path, ...]:
    values = _manifest_paths(payload, key, default)
    if kind == "skills" and key in payload and (root / default).is_dir():
        values = [f"./{default}", *values]
    files: list[Path] = []
    for value in values:
        target = _resolve_plugin_path(root, value, key)
        if not target.exists():
            if key not in payload:
                continue
            raise ValueError(f"Plugin {key} path does not exist: {value}")
        if target.is_file():
            if kind == "skills" and target.name != "SKILL.md":
                raise ValueError(f"Plugin skill file must be named SKILL.md: {value}")
            if kind == "markdown" and target.suffix.lower() != ".md":
                raise ValueError(f"Plugin {key} file must use .md: {value}")
            files.append(target)
            continue
        if not target.is_dir():
            raise ValueError(f"Plugin {key} path must be a file or directory: {value}")
        if kind == "skills" and (target / "SKILL.md").is_file():
            files.append(_resolve_plugin_path(root, _relative(root, target / "SKILL.md"), key))
            continue
        files.extend(_walk_component_files(root, target, "SKILL.md" if kind == "skills" else "*.md"))
    return tuple(_dedupe_sorted(files))


def _config_files(root: Path, payload: dict[str, Any], key: str, default: str) -> tuple[Path, ...]:
    if key in payload and isinstance(payload[key], dict):
        raise ValueError(f"Inline plugin {key} objects are not supported; use a ./ relative JSON path.")
    values = _manifest_paths(payload, key, default)
    files: list[Path] = []
    for value in values:
        target = _resolve_plugin_path(root, value, key)
        if not target.exists() and key not in payload:
            continue
        if not target.is_file() or target.suffix.lower() != ".json":
            raise ValueError(f"Plugin {key} path must be a JSON file: {value}")
        files.append(target)
    return tuple(_dedupe_sorted(files))


def _manifest_paths(payload: dict[str, Any], key: str, default: str) -> list[str]:
    if key not in payload:
        return [f"./{default}"]
    value = payload[key]
    values = [value] if isinstance(value, str) else value
    if not isinstance(values, list) or not values or any(not isinstance(item, str) for item in values):
        raise ValueError(f"Plugin {key} must be a non-empty path string or list of path strings.")
    for item in values:
        if item not in {".", "./"} and not item.startswith("./"):
            raise ValueError(f"Plugin {key} paths must start with ./: {item}")
    return list(values)


def _resolve_plugin_path(root: Path, value: str, label: str) -> Path:
    relative = "." if value in {".", "./"} else value[2:]
    lexical = root / relative
    if has_symlink_component(root, lexical):
        raise ValueError(f"Plugin {label} path contains a symbolic link: {value}")
    target = lexical.resolve()
    if target != root and root not in target.parents:
        raise ValueError(f"Plugin {label} path escapes the plugin root: {value}")
    return target


def _walk_component_files(root: Path, directory: Path, pattern: str) -> list[Path]:
    files: list[Path] = []
    for path in sorted(directory.rglob(pattern)):
        relative = path.relative_to(directory)
        if len(relative.parts) > MAX_PLUGIN_COMPONENT_DEPTH:
            continue
        if has_symlink_component(root, path) or not path.is_file():
            continue
        files.append(path)
        if len(files) > MAX_PLUGIN_COMPONENTS:
            break
    return files


def _dedupe_sorted(paths: list[Path]) -> list[Path]:
    return sorted(set(paths), key=lambda path: path.as_posix())


def _executable_files(root: Path) -> tuple[Path, ...]:
    directory = root / "bin"
    if not directory.exists():
        return ()
    if has_symlink_component(root, directory) or not directory.is_dir():
        raise ValueError("Plugin bin path must be a regular non-symlink directory.")
    files: list[Path] = []
    for path in sorted(directory.iterdir(), key=lambda item: item.name):
        if path.is_symlink() or path.is_dir():
            continue
        if not path.is_file():
            raise ValueError(f"Plugin bin entry must be a regular file: {path.name}")
        if path.stat().st_mode & 0o111:
            files.append(path)
    return tuple(files)


def _monitor_components(
    root: Path, payload: dict[str, Any]
) -> tuple[tuple[Path, ...], tuple[object, ...] | None]:
    experimental = payload.get("experimental", {})
    if not isinstance(experimental, dict):
        raise ValueError("Plugin experimental configuration must be an object.")
    value = experimental.get("monitors", payload.get("monitors"))
    if value is None:
        default = root / "monitors" / "monitors.json"
        if not default.exists():
            return (), None
        return (_monitor_file(root, default, "./monitors/monitors.json"),), None
    if isinstance(value, str):
        if value not in {".", "./"} and not value.startswith("./"):
            raise ValueError(f"Plugin monitors path must start with ./: {value}")
        target = _resolve_plugin_path(root, value, "monitors")
        return (_monitor_file(root, target, value),), None
    if not isinstance(value, list) or not value:
        raise ValueError("Plugin experimental.monitors must be a relative JSON path or non-empty array.")
    return (), tuple(value)


def _monitor_file(root: Path, target: Path, value: str) -> Path:
    if not target.is_file() or target.suffix.lower() != ".json":
        raise ValueError(f"Plugin monitors path must be a JSON file: {value}")
    if has_symlink_component(root, target):
        raise ValueError(f"Plugin monitors path contains a symbolic link: {value}")
    return target


def _relative(root: Path, path: Path) -> str:
    return f"./{path.relative_to(root).as_posix()}"


__all__ = ["PLUGIN_NAME_PATTERN", "read_plugin_manifest"]
