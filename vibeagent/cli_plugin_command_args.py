from __future__ import annotations

import argparse
from collections.abc import Sequence

from .cli_management_command_args import (
    add_management_command_local_argument,
    decode_management_command_arguments,
    normalize_management_command_arguments,
)


PLUGIN_COMMAND_OPTION = "--_plugin-command"


def add_plugin_command_local_argument(
    local: argparse._MutuallyExclusiveGroup,
) -> None:
    add_management_command_local_argument(
        local,
        option=PLUGIN_COMMAND_OPTION,
        dest="plugin_command",
    )


def normalize_plugin_command_arguments(argv: Sequence[str]) -> list[str]:
    return normalize_management_command_arguments(
        argv,
        command_names=frozenset({"plugin", "plugins"}),
        hidden_option=PLUGIN_COMMAND_OPTION,
    )


def decode_plugin_command_arguments(value: str) -> list[str]:
    return decode_management_command_arguments(value, label="Plugin")


__all__ = [
    "add_plugin_command_local_argument",
    "decode_plugin_command_arguments",
    "normalize_plugin_command_arguments",
]
