from __future__ import annotations

import argparse


def add_status_local_arguments(local: argparse._MutuallyExclusiveGroup) -> None:
    local.add_argument("--status", action="store_true", help="Show default non-interactive status and exit.")
    local.add_argument("--context", action="store_true", help="Show project context sources and exit.")
    local.add_argument("--init", nargs="?", const="AGENTS.md", metavar="FILE", help="Create a starter AGENTS.md or CLAUDE.md and exit.")
    local.add_argument("--doctor", action="store_true", help="Show local diagnostics and exit.")
