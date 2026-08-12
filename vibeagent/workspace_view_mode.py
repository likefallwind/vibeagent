from __future__ import annotations

import json

from .workspace_core import RunWorkspace
from .workspace_settings_sources import (
    claude_settings_files,
    read_settings_payload,
    settings_file_exists,
)


MAX_VIEW_MODE_SETTINGS_BYTES = 128_000
VIEW_MODES = frozenset({"default", "verbose", "focus"})


def resolve_verbose_mode(workspace: RunWorkspace, *, explicit: bool = False) -> bool:
    if explicit:
        return True
    if workspace.safe_mode:
        return False
    selected = "default"
    try:
        for config in claude_settings_files(workspace):
            if not settings_file_exists(config):
                continue
            payload = read_settings_payload(
                config,
                max_bytes=MAX_VIEW_MODE_SETTINGS_BYTES,
            )
            if "viewMode" not in payload:
                continue
            value = payload["viewMode"]
            if not isinstance(value, str) or value not in VIEW_MODES:
                raise ValueError(
                    f"{config.source} viewMode must be default, verbose, or focus."
                )
            selected = value
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(str(error)) from error
    return selected == "verbose"


__all__ = ["resolve_verbose_mode"]
