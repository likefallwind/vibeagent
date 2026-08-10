from __future__ import annotations

import argparse
from typing import Callable

from .tool_categories import valid_tool_categories
from .tool_search_options import tool_search_approval_choices


IntParser = Callable[[str], int]


def add_inspection_arguments(
    parser: argparse.ArgumentParser,
    local: argparse._MutuallyExclusiveGroup,
    *,
    positive_int: IntParser,
) -> None:
    parser.add_argument(
        "--model",
        nargs="?",
        const=True,
        metavar="MODEL",
        help="Show model provider configuration and exit, or set the model for a one-shot task when MODEL is provided.",
    )
    local.add_argument("--version", action="store_true", help="Show VibeAgent version and exit.")
    local.add_argument("--config", action="store_true", help="Show resolved provider and execution configuration and exit.")
    local.add_argument(
        "--tools",
        nargs="?",
        const=True,
        metavar="NAMES",
        help=(
            "Show model tool names and exit when used without a value, or restrict "
            "a one-shot coding task to comma-separated tool names."
        ),
    )
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
