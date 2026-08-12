from __future__ import annotations

from dataclasses import dataclass

from .plugin_store import enabled_plugin_manifests
from .workspace_agent_profile_parser import AGENT_REFERENCE_PATTERN
from .workspace_core import RunWorkspace
from .workspace_settings_sources import (
    claude_settings_files,
    read_settings_payload,
    settings_file_exists,
)


MAX_AGENT_SETTINGS_BYTES = 128_000
PROJECT_AGENT_SETTINGS_PATHS = (
    ".claude/settings.local.json",
    ".claude/settings.json",
)
USER_AGENT_SETTINGS_PATH = "~/.claude/settings.json"


@dataclass(frozen=True)
class MainAgentSelection:
    name: str | None = None
    source: str | None = None


def resolve_main_agent_selection(
    workspace: RunWorkspace,
    explicit_agent: str | None,
) -> MainAgentSelection:
    if workspace.safe_mode:
        return MainAgentSelection()
    if explicit_agent is not None:
        return MainAgentSelection(
            name=_validate_reference(explicit_agent, "CLI --agent"),
            source="explicit",
        )

    for config in reversed(claude_settings_files(workspace)):
        if not settings_file_exists(config):
            continue
        payload = read_settings_payload(config, max_bytes=MAX_AGENT_SETTINGS_BYTES)
        if "agent" in payload:
            return MainAgentSelection(
                name=_validate_reference(
                    payload["agent"],
                    f"{config.source} agent",
                ),
                source=config.source,
            )

    defaults = [
        (manifest.name, manifest.default_agent, manifest.default_settings_source)
        for manifest in enabled_plugin_manifests(workspace.root, workspace=workspace)
        if manifest.default_agent is not None
    ]
    if len(defaults) > 1:
        names = ", ".join(plugin for plugin, _agent, _source in defaults)
        raise ValueError(
            "Multiple enabled plugins declare a default main agent; select one "
            f"with --agent or project settings: {names}."
        )
    if defaults:
        plugin, agent, source = defaults[0]
        return MainAgentSelection(
            name=f"{plugin}:{agent}",
            source=f"plugin:{plugin}:{source or 'settings'}",
        )
    return MainAgentSelection()


def _validate_reference(value: object, source: str) -> str:
    if not isinstance(value, str) or not AGENT_REFERENCE_PATTERN.fullmatch(
        value.strip()
    ):
        raise ValueError(f"{source} must be a valid agent name.")
    return value.strip()


__all__ = [
    "MainAgentSelection",
    "PROJECT_AGENT_SETTINGS_PATHS",
    "USER_AGENT_SETTINGS_PATH",
    "resolve_main_agent_selection",
]
