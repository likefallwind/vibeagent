from __future__ import annotations

import argparse
from typing import Callable


IntParser = Callable[[str], int]


def add_workflow_local_arguments(local: argparse._MutuallyExclusiveGroup) -> None:
    local.add_argument("--review", action="store_true", help="Review current git changes, syntax checks, and suggested commands and exit.")
    local.add_argument("--handoff", action="store_true", help="Show final handoff review, checks, changed files, and latest plan and exit.")
    local.add_argument("--changes", action="store_true", help="Show a structured changed-file summary and exit.")


def add_workflow_option_arguments(
    parser: argparse.ArgumentParser,
    *,
    positive_int: IntParser,
) -> None:
    parser.add_argument("--review-max-files", type=positive_int, default=200, metavar="N", help="Maximum changed files to show with --review.")
    parser.add_argument("--review-max-checks", type=positive_int, default=5, metavar="N", help="Maximum suggested checks to show with --review.")
    parser.add_argument("--handoff-max-files", type=positive_int, default=200, metavar="N", help="Maximum changed files to show with --handoff.")
    parser.add_argument("--handoff-max-checks", type=positive_int, default=10, metavar="N", help="Maximum suggested checks to show with --handoff.")
    parser.add_argument("--handoff-max-status-chars", type=positive_int, default=4_000, metavar="N", help="Maximum git status characters to show with --handoff.")
    parser.add_argument("--handoff-max-plan-chars", type=positive_int, default=4_000, metavar="N", help="Maximum latest-plan characters to show with --handoff.")
    parser.add_argument("--changes-max-files", type=positive_int, default=200, metavar="N", help="Maximum changed files to show with --changes.")
