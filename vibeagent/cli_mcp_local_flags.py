from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .cli_mcp_command_args import decode_mcp_command_arguments
from .mcp_commands import MCP_USAGE, McpCommandResult, handle_mcp_command_parts


def run_mcp_local_flag(
    args: argparse.Namespace,
    project_root: Path | None,
    _commands: dict[str, Any],
) -> tuple[str, dict[str, object]] | None:
    if args.mcp_command is None:
        return None
    command_args = decode_mcp_command_arguments(args.mcp_command)
    help_requested = not command_args or command_args in (["help"], ["--help"], ["-h"])
    result = (
        McpCommandResult(MCP_USAGE)
        if help_requested
        else handle_mcp_command_parts(project_root or Path.cwd(), command_args)
    )
    text = result.text.replace("Usage: /mcp", "Usage: vibeagent mcp", 1)
    if help_requested:
        text = f"MCP commands:\n{text}"
    return text, {"mcp": {"changed": result.changed}}


__all__ = ["run_mcp_local_flag"]
