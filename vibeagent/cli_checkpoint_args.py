from __future__ import annotations

import argparse


def add_checkpoint_local_arguments(local: argparse._MutuallyExclusiveGroup) -> None:
    local.add_argument(
        "--checkpoint",
        nargs="?",
        const="",
        metavar="LABEL",
        help="Save current git status, diffs, and ordinary untracked files as a local checkpoint and exit.",
    )
    local.add_argument("--checkpoints", action="store_true", help="List saved local checkpoints and exit.")
    local.add_argument("--checkpoint-show", metavar="ID", help="Show one saved local checkpoint and exit.")
    local.add_argument("--checkpoint-diff", metavar="ID", help="Show saved staged and unstaged checkpoint patches and exit.")
    local.add_argument("--checkpoint-status", metavar="ID", help="Compare current git status and diffs with a saved checkpoint and exit.")
    local.add_argument(
        "--check-checkpoint-restore",
        metavar="ID",
        help="Preview restoring tracked staged/unstaged changes and saved untracked files from a checkpoint and exit.",
    )
    local.add_argument(
        "--checkpoint-restore",
        metavar="ID",
        help="Restore tracked staged/unstaged changes and saved untracked files from a checkpoint and exit.",
    )
    local.add_argument("--check-checkpoint-delete", metavar="ID", help="Preview deleting one saved local checkpoint and exit.")
    local.add_argument("--checkpoint-delete", metavar="ID", help="Delete one saved local checkpoint and exit.")
    local.add_argument("--check-checkpoint-prune", metavar="N", help="Preview deleting older checkpoints while keeping the newest N and exit.")
    local.add_argument("--checkpoint-prune", metavar="N", help="Delete older checkpoints while keeping the newest N and exit.")
