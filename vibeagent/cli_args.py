from __future__ import annotations

import argparse
from collections.abc import Sequence

from .cli_parse_core import nonnegative_int, positive_int, timeout_ms
from .cli_checkpoint_args import add_checkpoint_local_arguments
from .cli_code_intel_args import add_code_intel_local_arguments, add_code_intel_option_arguments
from .cli_compat_args import add_compat_arguments, normalize_compat_arguments
from .cli_edit_args import add_edit_local_arguments, add_edit_option_arguments
from .cli_git_args import (
    add_git_diff_local_arguments,
    add_git_diff_option_arguments,
    add_git_history_option_arguments,
    add_git_local_arguments,
)
from .cli_inspection_args import add_inspection_arguments
from .cli_local_flag_detection import (
    LOCAL_FLAG_ARG_NAMES,
    has_local_flag as _has_local_flag,
)
from .cli_output_args import add_output_arguments, normalize_output_arguments
from .cli_one_shot_args import add_one_shot_arguments
from .cli_process_args import add_process_local_arguments, add_process_option_arguments
from .cli_project_args import (
    add_project_check_local_arguments,
    add_project_check_option_arguments,
    add_project_discovery_local_arguments,
    add_project_discovery_option_arguments,
)
from .cli_read_args import add_read_local_arguments, add_read_option_arguments
from .cli_runtime_args import (
    add_runtime_connection_option_arguments,
    add_runtime_local_arguments,
    add_runtime_network_local_arguments,
    add_runtime_run_option_arguments,
)
from .cli_session_args import add_session_limit_arguments, add_session_local_arguments
from .cli_status_args import add_status_local_arguments
from .cli_workflow_args import add_workflow_local_arguments, add_workflow_option_arguments


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="vibeagent",
        description="Run VibeAgent interactively or execute one task.",
        allow_abbrev=False,
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--chat", action="store_true", help="Run the one-shot task in daily conversation mode.")
    mode.add_argument("--code", action="store_true", help="Run the one-shot task in coding mode. This is the default.")
    local = parser.add_mutually_exclusive_group()
    add_inspection_arguments(parser, local, positive_int=positive_int)
    add_project_check_local_arguments(local)
    add_project_check_option_arguments(parser, positive_int=positive_int)
    add_runtime_local_arguments(local)
    add_runtime_network_local_arguments(local, positive_int=positive_int)
    add_project_discovery_local_arguments(local)
    add_read_local_arguments(local)
    add_code_intel_local_arguments(local)
    add_edit_local_arguments(local)
    add_git_local_arguments(local)
    add_process_local_arguments(local)
    add_status_local_arguments(local)
    add_workflow_local_arguments(local)
    add_workflow_option_arguments(parser, positive_int=positive_int)
    add_git_diff_local_arguments(local)
    add_git_diff_option_arguments(
        parser,
        positive_int=positive_int,
        nonnegative_int=nonnegative_int,
    )
    add_runtime_connection_option_arguments(
        parser,
        positive_int=positive_int,
        timeout_ms=timeout_ms,
    )
    add_project_discovery_option_arguments(
        parser,
        positive_int=positive_int,
        nonnegative_int=nonnegative_int,
    )
    add_code_intel_option_arguments(
        parser,
        positive_int=positive_int,
        nonnegative_int=nonnegative_int,
    )
    add_read_option_arguments(
        parser,
        positive_int=positive_int,
        nonnegative_int=nonnegative_int,
    )
    add_session_limit_arguments(
        parser,
        positive_int=positive_int,
        nonnegative_int=nonnegative_int,
    )
    add_git_history_option_arguments(parser, positive_int=positive_int)
    add_process_option_arguments(
        parser,
        positive_int=positive_int,
        nonnegative_int=nonnegative_int,
        timeout_ms=timeout_ms,
    )
    add_edit_option_arguments(
        parser,
        nonnegative_int=nonnegative_int,
        positive_int=positive_int,
    )
    add_runtime_run_option_arguments(
        parser,
        positive_int=positive_int,
        nonnegative_int=nonnegative_int,
        timeout_ms=timeout_ms,
    )
    add_session_local_arguments(parser, local)
    add_checkpoint_local_arguments(local)
    local.add_argument("--usage", action="store_true", help="Show local session usage and exit.")
    local.add_argument("--cost", action="store_true", help="Show configured cost estimate and exit.")
    local.add_argument("--save-config", action="store_true", help="Save non-secret provider defaults to .vibeagent/config.json and exit.")
    add_one_shot_arguments(
        parser,
        positive_int=positive_int,
        nonnegative_int=nonnegative_int,
        timeout_ms=timeout_ms,
    )
    add_output_arguments(parser)
    add_compat_arguments(parser, positive_int=positive_int)
    parser.add_argument("task", nargs="*", help="One-shot task text. Omit it to start the interactive prompt.")
    return normalize_output_arguments(normalize_compat_arguments(parser.parse_args(list(argv))))


def has_local_flag(args: argparse.Namespace) -> bool:
    return _has_local_flag(args)
