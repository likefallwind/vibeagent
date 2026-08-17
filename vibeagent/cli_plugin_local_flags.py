from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .cli_plugin_command_args import decode_plugin_command_arguments
from .plugin_commands import (
    PLUGIN_USAGE,
    PluginCommandResult,
    handle_plugin_command_parts,
)


def run_plugin_local_flag(
    args: argparse.Namespace,
    project_root: Path | None,
    _commands: dict[str, Any],
) -> tuple[str, dict[str, object]] | None:
    if args.plugin_command is None:
        return None
    command_args = decode_plugin_command_arguments(args.plugin_command)
    help_requested = not command_args or command_args in (["help"], ["--help"], ["-h"])
    result = (
        PluginCommandResult(PLUGIN_USAGE)
        if help_requested
        else handle_plugin_command_parts(project_root or Path.cwd(), command_args)
    )
    text = result.text.replace("Usage: /plugin", "Usage: vibeagent plugin", 1)
    if help_requested:
        text = f"Plugin commands:\n{text}"
    return text, {"plugin": {"changed": result.changed}}


__all__ = ["run_plugin_local_flag"]
