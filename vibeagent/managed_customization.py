from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .managed_settings import managed_settings_directory
from .workspace_core import RunWorkspace
from .workspace_settings_sources import (
    claude_settings_files,
    read_settings_payload,
    settings_file_exists,
)


CustomizationSurface = Literal["skills", "agents", "hooks", "mcp"]
CUSTOMIZATION_SURFACES: tuple[CustomizationSurface, ...] = (
    "skills",
    "agents",
    "hooks",
    "mcp",
)
MAX_MANAGED_CUSTOMIZATION_SETTINGS_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True)
class ManagedCustomizationPolicy:
    strict_surfaces: frozenset[CustomizationSurface] = frozenset()
    sources: tuple[str, ...] = ()

    def locks(self, surface: CustomizationSurface) -> bool:
        return surface in self.strict_surfaces


def read_managed_customization_policy(
    workspace: RunWorkspace,
) -> ManagedCustomizationPolicy:
    surfaces: set[CustomizationSurface] = set()
    sources: list[str] = []
    for config in claude_settings_files(workspace):
        if not config.managed or not settings_file_exists(config):
            continue
        payload = read_settings_payload(
            config,
            max_bytes=MAX_MANAGED_CUSTOMIZATION_SETTINGS_BYTES,
        )
        if "strictPluginOnlyCustomization" not in payload:
            continue
        surfaces.update(
            _parse_strict_surfaces(
                payload["strictPluginOnlyCustomization"],
                source=config.source,
            )
        )
        sources.append(config.source)
    return ManagedCustomizationPolicy(
        strict_surfaces=frozenset(surfaces),
        sources=tuple(dict.fromkeys(sources)),
    )


def managed_component_root(component: Literal["skills", "agents"]) -> Path:
    return managed_settings_directory().absolute() / ".claude" / component


def managed_mcp_path() -> Path:
    return managed_settings_directory().absolute() / "managed-mcp.json"


def _parse_strict_surfaces(
    value: object,
    *,
    source: str,
) -> tuple[CustomizationSurface, ...]:
    if value is True:
        return CUSTOMIZATION_SURFACES
    if value is False:
        return ()
    if not isinstance(value, list):
        raise ValueError(
            f"{source} strictPluginOnlyCustomization must be true, false, or an array."
        )
    known = set(CUSTOMIZATION_SURFACES)
    return tuple(
        surface
        for surface in CUSTOMIZATION_SURFACES
        if surface in {item for item in value if isinstance(item, str) and item in known}
    )


__all__ = [
    "CUSTOMIZATION_SURFACES",
    "CustomizationSurface",
    "ManagedCustomizationPolicy",
    "managed_component_root",
    "managed_mcp_path",
    "read_managed_customization_policy",
]
