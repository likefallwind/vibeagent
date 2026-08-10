from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

from .workspace_metadata_files import (
    has_symlink_component,
    parse_scalar_frontmatter,
    read_regular_file_bytes,
)


MAX_PLUGIN_SETTINGS_BYTES = 128_000
AGENT_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


@dataclass(frozen=True)
class PluginDefaultSettings:
    agent: str | None = None
    source: str | None = None
    has_subagent_status_line: bool = False
    warnings: tuple[str, ...] = ()

    @property
    def enabled(self) -> bool:
        return self.agent is not None or self.has_subagent_status_line


def read_plugin_default_settings(
    root: Path,
    manifest_payload: dict[str, Any],
    agent_files: tuple[Path, ...],
) -> PluginDefaultSettings:
    settings_path = root / "settings.json"
    if settings_path.exists() or settings_path.is_symlink():
        payload = _read_settings_file(root, settings_path)
        source = "settings.json"
    elif "settings" in manifest_payload:
        payload = manifest_payload["settings"]
        source = ".claude-plugin/plugin.json:settings"
        if not isinstance(payload, dict):
            raise ValueError("Plugin manifest settings must be an object.")
    else:
        return PluginDefaultSettings()

    agent = payload.get("agent")
    if agent is not None:
        if not isinstance(agent, str) or not AGENT_NAME_PATTERN.fullmatch(agent):
            raise ValueError("Plugin default agent must be a valid unqualified agent name.")
        available_agents = _declared_agent_names(root, agent_files)
        if agent not in available_agents:
            raise ValueError(
                f"Plugin default agent is not declared by this plugin: {agent}."
            )

    has_status_line = "subagentStatusLine" in payload
    warnings = (
        ("Plugin subagentStatusLine is not supported by the current terminal UI.",)
        if has_status_line
        else ()
    )
    return PluginDefaultSettings(
        agent=agent,
        source=source,
        has_subagent_status_line=has_status_line,
        warnings=warnings,
    )


def _read_settings_file(root: Path, path: Path) -> dict[str, Any]:
    if has_symlink_component(root, path) or not path.is_file():
        raise ValueError("Plugin settings.json must be a regular non-symlink file.")
    raw = read_regular_file_bytes(
        path,
        max_bytes=MAX_PLUGIN_SETTINGS_BYTES,
        label="Plugin settings.json",
    )
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not parse plugin settings.json: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError("Plugin settings.json must contain a JSON object.")
    return payload


def _declared_agent_names(root: Path, agent_files: tuple[Path, ...]) -> set[str]:
    names: set[str] = set()
    for path in agent_files:
        relative = path.relative_to(root).as_posix()
        raw = read_regular_file_bytes(
            path,
            max_bytes=64_000,
            label=f"Plugin agent {relative}",
        )
        try:
            metadata, _body = parse_scalar_frontmatter(
                raw.decode("utf-8"), frozenset({"name"})
            )
        except UnicodeDecodeError as error:
            raise ValueError(f"Plugin agent is not valid UTF-8: {relative}.") from error
        name = str(metadata.get("name", "")).strip()
        if not AGENT_NAME_PATTERN.fullmatch(name):
            raise ValueError(f"Plugin agent has an invalid or missing name: {relative}.")
        names.add(name)
    return names


__all__ = [
    "MAX_PLUGIN_SETTINGS_BYTES",
    "PluginDefaultSettings",
    "read_plugin_default_settings",
]
