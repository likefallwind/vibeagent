from __future__ import annotations

import json

from .workspace_core import RunWorkspace
from .workspace_settings_sources import (
    claude_settings_files,
    read_settings_payload,
    settings_file_exists,
)


MAX_SHELL_RESPONSE_SETTINGS_BYTES = 128_000


def resolve_respond_to_bash_commands(workspace: RunWorkspace) -> bool:
    if workspace.safe_mode:
        return True
    enabled = True
    try:
        for config in claude_settings_files(workspace):
            if not settings_file_exists(config):
                continue
            payload = read_settings_payload(
                config,
                max_bytes=MAX_SHELL_RESPONSE_SETTINGS_BYTES,
            )
            if "respondToBashCommands" not in payload:
                continue
            value = payload["respondToBashCommands"]
            if not isinstance(value, bool):
                raise ValueError(
                    f"{config.source} respondToBashCommands must be true or false."
                )
            enabled = value
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(str(error)) from error
    return enabled


__all__ = ["resolve_respond_to_bash_commands"]
