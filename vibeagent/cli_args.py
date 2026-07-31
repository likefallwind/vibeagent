from __future__ import annotations

import argparse
from collections.abc import Sequence

from .cli_parse_core import nonnegative_int, positive_int, timeout_ms
from .cli_code_intel_args import add_code_intel_local_arguments, add_code_intel_option_arguments
from .cli_compat_args import add_compat_arguments, normalize_compat_arguments
from .cli_edit_args import add_edit_local_arguments, add_edit_option_arguments
from .cli_git_args import (
    add_git_diff_option_arguments,
    add_git_history_option_arguments,
    add_git_local_arguments,
)
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
from .tool_categories import valid_tool_categories
from .tool_search_options import tool_search_approval_choices


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
    parser.add_argument(
        "--model",
        nargs="?",
        const=True,
        metavar="MODEL",
        help="Show model provider configuration and exit, or set the model for a one-shot task when MODEL is provided.",
    )
    local.add_argument("--version", action="store_true", help="Show VibeAgent version and exit.")
    local.add_argument("--config", action="store_true", help="Show resolved provider and execution configuration and exit.")
    local.add_argument("--tools", action="store_true", help="Show model tool names by category and exit.")
    local.add_argument("--tool", metavar="NAME", help="Show one model tool's description and input schema and exit.")
    local.add_argument("--tool-search", metavar="QUERY", help="Search model tools by name, description, category, or input fields and exit.")
    parser.add_argument("--tool-search-max", type=positive_int, default=20, metavar="N", help="Maximum matching tools to show with --tool-search.")
    parser.add_argument(
        "--tool-search-category",
        choices=valid_tool_categories(),
        help="Optional category filter for --tool-search.",
    )
    parser.add_argument(
        "--tool-search-approval",
        choices=tool_search_approval_choices(),
        default="any",
        help="Optional approval filter for --tool-search.",
    )
    local.add_argument("--permissions", action="store_true", help="Show approval-gated tools and hard command blocks and exit.")
    local.add_argument("--sandbox-status", action="store_true", help="Show command sandbox configuration and availability and exit.")
    local.add_argument("--trust-status", action="store_true", help="Show persistent permission trust for the active project and exit.")
    local.add_argument("--trust-project", action="store_true", help="Persist trust in permission allow rules for the active project and exit.")
    local.add_argument("--untrust-project", action="store_true", help="Remove persistent permission trust for the active project and exit.")
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
    local.add_argument("--status", action="store_true", help="Show default non-interactive status and exit.")
    local.add_argument("--context", action="store_true", help="Show project context sources and exit.")
    local.add_argument("--init", nargs="?", const="AGENTS.md", metavar="FILE", help="Create a starter AGENTS.md or CLAUDE.md and exit.")
    local.add_argument("--doctor", action="store_true", help="Show local diagnostics and exit.")
    local.add_argument("--review", action="store_true", help="Review current git changes, syntax checks, and suggested commands and exit.")
    parser.add_argument("--review-max-files", type=positive_int, default=200, metavar="N", help="Maximum changed files to show with --review.")
    parser.add_argument("--review-max-checks", type=positive_int, default=5, metavar="N", help="Maximum suggested checks to show with --review.")
    local.add_argument("--handoff", action="store_true", help="Show final handoff review, checks, changed files, and latest plan and exit.")
    parser.add_argument("--handoff-max-files", type=positive_int, default=200, metavar="N", help="Maximum changed files to show with --handoff.")
    parser.add_argument("--handoff-max-checks", type=positive_int, default=10, metavar="N", help="Maximum suggested checks to show with --handoff.")
    parser.add_argument("--handoff-max-status-chars", type=positive_int, default=4_000, metavar="N", help="Maximum git status characters to show with --handoff.")
    parser.add_argument("--handoff-max-plan-chars", type=positive_int, default=4_000, metavar="N", help="Maximum latest-plan characters to show with --handoff.")
    local.add_argument("--changes", action="store_true", help="Show a structured changed-file summary and exit.")
    parser.add_argument("--changes-max-files", type=positive_int, default=200, metavar="N", help="Maximum changed files to show with --changes.")
    local.add_argument("--diff", nargs="?", const="", metavar="ARGS", help="Show current git diff. Optional ARGS: '--staged [path]' or '[path]'.")
    local.add_argument("--diff-hunks", nargs="?", const="", metavar="ARGS", help="Show structured git diff hunks. Optional ARGS: '--staged [path]' or '[path]'.")
    local.add_argument("--diff-contexts", nargs="?", const="", metavar="ARGS", help="Show source context around git diff hunks. Optional ARGS: '--staged [path]' or '[path]'.")
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
    local.add_argument("--checkpoint", nargs="?", const="", metavar="LABEL", help="Save current git status, diffs, and ordinary untracked files as a local checkpoint and exit.")
    local.add_argument("--checkpoints", action="store_true", help="List saved local checkpoints and exit.")
    local.add_argument("--checkpoint-show", metavar="ID", help="Show one saved local checkpoint and exit.")
    local.add_argument("--checkpoint-diff", metavar="ID", help="Show saved staged and unstaged checkpoint patches and exit.")
    local.add_argument("--checkpoint-status", metavar="ID", help="Compare current git status and diffs with a saved checkpoint and exit.")
    local.add_argument("--check-checkpoint-restore", metavar="ID", help="Preview restoring tracked staged/unstaged changes and saved untracked files from a checkpoint and exit.")
    local.add_argument("--checkpoint-restore", metavar="ID", help="Restore tracked staged/unstaged changes and saved untracked files from a checkpoint and exit.")
    local.add_argument("--check-checkpoint-delete", metavar="ID", help="Preview deleting one saved local checkpoint and exit.")
    local.add_argument("--checkpoint-delete", metavar="ID", help="Delete one saved local checkpoint and exit.")
    local.add_argument("--check-checkpoint-prune", metavar="N", help="Preview deleting older checkpoints while keeping the newest N and exit.")
    local.add_argument("--checkpoint-prune", metavar="N", help="Delete older checkpoints while keeping the newest N and exit.")
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
