from __future__ import annotations

import argparse
from collections.abc import Sequence


def add_status_local_arguments(local: argparse._MutuallyExclusiveGroup) -> None:
    local.add_argument("--status", action="store_true", help="Show default non-interactive status and exit.")
    local.add_argument("--context", action="store_true", help="Show project context sources and exit.")
    local.add_argument("--init", nargs="?", const="", metavar="FILE", help="Create a starter AGENTS.md or CLAUDE.md and exit; with --print, run Setup hooks before the task.")
    local.add_argument("--init-only", action="store_true", help="Run Setup(init) and SessionStart(startup) hooks, then exit.")
    local.add_argument("--doctor", action="store_true", help="Show local diagnostics and exit.")


def normalize_status_command_arguments(
    argv: Sequence[str],
    *,
    parsed_task: Sequence[str] | None = None,
) -> list[str]:
    values = list(argv)
    if values and values[0] == "doctor":
        return ["--doctor", *values[1:]]
    if list(parsed_task or ()) == ["doctor"]:
        index = len(values) - 1 - values[::-1].index("doctor")
        values[index] = "--doctor"
    return values


__all__ = ["add_status_local_arguments", "normalize_status_command_arguments"]
