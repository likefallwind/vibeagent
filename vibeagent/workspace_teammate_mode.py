from __future__ import annotations

import json

from .workspace_core import RunWorkspace
from .workspace_settings_sources import (
    claude_settings_files,
    read_settings_payload,
    settings_file_exists,
)


MAX_TEAMMATE_MODE_SETTINGS_BYTES = 128_000
TEAMMATE_MODES = ("in-process", "auto", "tmux", "iterm2")
SPLIT_PANE_TEAMMATE_MODES = frozenset({"tmux", "iterm2"})


def resolve_teammate_mode(
    workspace: RunWorkspace,
    *,
    explicit: str | None = None,
) -> str:
    selected = explicit
    if selected is None and not workspace.safe_mode:
        selected = _settings_teammate_mode(workspace)
    selected = selected or "in-process"
    if selected not in TEAMMATE_MODES:
        raise ValueError("teammateMode must be in-process, auto, tmux, or iterm2.")
    if selected in SPLIT_PANE_TEAMMATE_MODES:
        raise ValueError(
            f"Teammate display mode {selected!r} is not available yet; use in-process or auto."
        )
    return "in-process"


def _settings_teammate_mode(workspace: RunWorkspace) -> str | None:
    selected: str | None = None
    try:
        for config in claude_settings_files(workspace):
            if not settings_file_exists(config):
                continue
            payload = read_settings_payload(
                config,
                max_bytes=MAX_TEAMMATE_MODE_SETTINGS_BYTES,
            )
            if "teammateMode" not in payload:
                continue
            value = payload["teammateMode"]
            if not isinstance(value, str) or value not in TEAMMATE_MODES:
                raise ValueError(
                    f"{config.source} teammateMode must be in-process, auto, tmux, or iterm2."
                )
            selected = value
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(str(error)) from error
    return selected


__all__ = ["TEAMMATE_MODES", "resolve_teammate_mode"]
