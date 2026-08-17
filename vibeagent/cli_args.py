from __future__ import annotations

import argparse
from collections.abc import Sequence

from .cli_argument_registration import add_cli_arguments
from .cli_auto_mode_args import normalize_auto_mode_command_arguments
from .cli_background_agent_args import normalize_background_agent_command_arguments
from .cli_compat_args import normalize_compat_arguments, normalize_prompt_suggestion_arguments
from .cli_local_flag_detection import (
    LOCAL_FLAG_ARG_NAMES,
    has_local_flag as _has_local_flag,
)
from .cli_mcp_command_args import normalize_mcp_command_arguments
from .cli_output_args import normalize_output_arguments
from .cli_status_args import normalize_status_command_arguments
from .cli_tmux import normalize_tmux_arguments
from .debug_runtime import normalize_debug_arguments


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="vibeagent",
        description="Run VibeAgent interactively or execute one task.",
        allow_abbrev=False,
    )
    add_cli_arguments(parser)
    values = normalize_prompt_suggestion_arguments(
        normalize_debug_arguments(
            normalize_auto_mode_command_arguments(
                normalize_status_command_arguments(
                    normalize_background_agent_command_arguments(
                        normalize_tmux_arguments(normalize_mcp_command_arguments(argv))
                    )
                )
            )
        )
    )
    args = parser.parse_args(values)
    normalized_values = normalize_status_command_arguments(values, parsed_task=args.task)
    if normalized_values != values:
        args = parser.parse_args(normalized_values)
    return normalize_output_arguments(normalize_compat_arguments(args))


def has_local_flag(args: argparse.Namespace) -> bool:
    return _has_local_flag(args)
