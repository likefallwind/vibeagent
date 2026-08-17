from __future__ import annotations

import argparse
from collections.abc import Sequence

from .cli_management_command_args import (
    add_management_command_local_argument,
    decode_management_command_arguments,
    normalize_management_command_arguments,
)


MCP_COMMAND_OPTION = "--_mcp-command"


def add_mcp_command_local_argument(
    local: argparse._MutuallyExclusiveGroup,
) -> None:
    add_management_command_local_argument(
        local,
        option=MCP_COMMAND_OPTION,
        dest="mcp_command",
    )


def normalize_mcp_command_arguments(argv: Sequence[str]) -> list[str]:
    return normalize_management_command_arguments(
        argv,
        command_names=frozenset({"mcp"}),
        hidden_option=MCP_COMMAND_OPTION,
    )


def decode_mcp_command_arguments(value: str) -> list[str]:
    return decode_management_command_arguments(value, label="MCP")


__all__ = [
    "add_mcp_command_local_argument",
    "decode_mcp_command_arguments",
    "normalize_mcp_command_arguments",
]
