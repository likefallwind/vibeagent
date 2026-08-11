from __future__ import annotations

import argparse
from collections.abc import Sequence

from .cli_argument_registration import add_cli_arguments
from .cli_background_agent_args import normalize_background_agent_command_arguments
from .cli_compat_args import normalize_compat_arguments
from .cli_local_flag_detection import (
    LOCAL_FLAG_ARG_NAMES,
    has_local_flag as _has_local_flag,
)
from .cli_output_args import normalize_output_arguments


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="vibeagent",
        description="Run VibeAgent interactively or execute one task.",
        allow_abbrev=False,
    )
    add_cli_arguments(parser)
    values = normalize_background_agent_command_arguments(argv)
    return normalize_output_arguments(normalize_compat_arguments(parser.parse_args(values)))


def has_local_flag(args: argparse.Namespace) -> bool:
    return _has_local_flag(args)
