from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from .plugin_store import enabled_plugin_manifests
from .workspace_agent_profile_parser import AGENT_REFERENCE_PATTERN
from .workspace_core import RunWorkspace
from .workspace_metadata_files import has_symlink_component, read_regular_file_bytes


MAX_AGENT_SETTINGS_BYTES = 128_000
PROJECT_AGENT_SETTINGS_PATHS = (
    ".claude/settings.local.json",
    ".claude/settings.json",
)


@dataclass(frozen=True)
class MainAgentSelection:
    name: str | None = None
    source: str | None = None


def resolve_main_agent_selection(
    workspace: RunWorkspace,
    explicit_agent: str | None,
) -> MainAgentSelection:
    if explicit_agent is not None:
        return MainAgentSelection(
            name=_validate_reference(explicit_agent, "CLI --agent"),
            source="explicit",
        )

    for relative in PROJECT_AGENT_SETTINGS_PATHS:
        path = workspace.root / relative
        if not path.exists() and not path.is_symlink():
            continue
        payload = _read_project_settings(workspace.root, path, relative)
        if "agent" not in payload:
            continue
        return MainAgentSelection(
            name=_validate_reference(payload["agent"], f"{relative} agent"),
            source=relative,
        )

    defaults = [
        (manifest.name, manifest.default_agent, manifest.default_settings_source)
        for manifest in enabled_plugin_manifests(workspace.root)
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


def _read_project_settings(
    root: Path,
    path: Path,
    relative: str,
) -> dict[str, object]:
    if has_symlink_component(root, path) or not path.is_file():
        raise ValueError(f"{relative} must be a regular non-symlink file.")
    raw = read_regular_file_bytes(
        path,
        max_bytes=MAX_AGENT_SETTINGS_BYTES,
        label=relative,
    )
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not parse {relative}: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{relative} must contain a JSON object.")
    return payload


def _validate_reference(value: object, source: str) -> str:
    if not isinstance(value, str) or not AGENT_REFERENCE_PATTERN.fullmatch(
        value.strip()
    ):
        raise ValueError(f"{source} must be a valid project or plugin agent name.")
    return value.strip()


__all__ = [
    "MainAgentSelection",
    "PROJECT_AGENT_SETTINGS_PATHS",
    "resolve_main_agent_selection",
]
