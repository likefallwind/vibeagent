from __future__ import annotations

import argparse
from typing import Callable


IntParser = Callable[[str], int]


def add_git_local_arguments(local: argparse._MutuallyExclusiveGroup) -> None:
    local.add_argument("--git-status", action="store_true", help="Show raw short git status and exit.")
    local.add_argument("--conflicts", nargs="?", const="", metavar="PATH", help="Scan for unmerged git files and conflict marker lines and exit.")
    local.add_argument("--git-info", action="store_true", help="Show git branch, HEAD, upstream, remotes, and short status and exit.")
    local.add_argument("--branches", action="store_true", help="Show local git branches and current branch and exit.")
    local.add_argument("--log", nargs="?", const="", metavar="PATH", help="Show recent git commits, optionally scoped to one path, and exit.")
    local.add_argument("--show", nargs="?", const="HEAD", metavar="REV", help="Show one git revision with stat and patch and exit.")
    local.add_argument("--blame", metavar="PATH", help="Show git blame for one file and exit.")
    local.add_argument("--stashes", action="store_true", help="Show local git stash entries and exit.")
    local.add_argument("--check-git-fetch", nargs="?", const="", metavar="REMOTE", help="Preview selecting a git remote to fetch and exit.")
    local.add_argument("--git-fetch", nargs="?", const="", metavar="REMOTE", help="Run git fetch --prune for one remote and exit.")
    local.add_argument("--check-git-pull", action="store_true", help="Preview fast-forward pulling the current upstream and exit.")
    local.add_argument("--git-pull", action="store_true", help="Fast-forward pull the current upstream and exit.")
    local.add_argument("--check-git-push", action="store_true", help="Preview pushing the current branch to upstream and exit.")
    local.add_argument("--git-push", action="store_true", help="Push the current branch to upstream and exit.")
    local.add_argument("--check-git-stash", nargs="?", const="", metavar="MESSAGE", help="Preview saving non-runtime changes to git stash and exit.")
    local.add_argument("--git-stash", nargs="?", const="", metavar="MESSAGE", help="Save non-runtime changes to git stash and exit.")
    local.add_argument("--check-git-stash-apply", metavar="STASH_REF", help="Preview applying a stash to a clean worktree and exit.")
    local.add_argument("--git-stash-apply", metavar="STASH_REF", help="Apply a stash to a clean worktree and exit.")
    local.add_argument("--check-git-stash-drop", metavar="STASH_REF", help="Preview deleting a stash entry and exit.")
    local.add_argument("--git-stash-drop", metavar="STASH_REF", help="Delete a stash entry and exit.")
    local.add_argument("--check-git-stage", nargs="+", metavar="PATH", help="Preview staging explicit project paths and exit.")
    local.add_argument("--git-stage", nargs="+", metavar="PATH", help="Stage explicit project paths and exit.")
    local.add_argument("--check-git-unstage", nargs="+", metavar="PATH", help="Preview unstaging explicit project paths and exit.")
    local.add_argument("--git-unstage", nargs="+", metavar="PATH", help="Unstage explicit project paths and exit.")
    local.add_argument("--check-git-commit", metavar="MESSAGE", help="Preview committing currently staged changes and exit.")
    local.add_argument("--git-commit", metavar="MESSAGE", help="Commit currently staged changes and exit.")
    local.add_argument("--check-git-restore", nargs="+", metavar="PATH", help="Preview discarding unstaged tracked-file changes and exit.")
    local.add_argument("--git-restore", nargs="+", metavar="PATH", help="Discard unstaged tracked-file changes and exit.")
    local.add_argument("--check-git-switch", metavar="BRANCH", help="Preview switching or creating a local branch and exit.")
    local.add_argument("--git-switch", metavar="BRANCH", help="Switch or create a local branch and exit.")


def add_git_diff_option_arguments(
    parser: argparse.ArgumentParser,
    *,
    positive_int: IntParser,
    nonnegative_int: IntParser,
) -> None:
    parser.add_argument("--diff-max-chars", type=positive_int, default=12_000, metavar="N", help="Maximum raw diff characters to show with --diff.")
    parser.add_argument("--diff-hunks-max-hunks", type=positive_int, default=80, metavar="N", help="Maximum hunks to show with --diff-hunks.")
    parser.add_argument("--diff-hunks-max-lines", type=positive_int, default=80, metavar="N", help="Maximum patch lines per hunk with --diff-hunks.")
    parser.add_argument("--diff-context-lines", type=nonnegative_int, default=5, metavar="N", help="Surrounding source lines for --diff-contexts.")
    parser.add_argument("--diff-contexts-max-hunks", type=positive_int, default=80, metavar="N", help="Maximum hunks to inspect with --diff-contexts.")
    parser.add_argument("--diff-contexts-max-bytes", type=positive_int, default=20_000, metavar="N", help="Maximum bytes per source context with --diff-contexts.")
    parser.add_argument("--staged", "--cached", action="store_true", dest="diff_staged", help="Show staged changes with --diff, --diff-hunks, or --diff-contexts.")


def add_git_history_option_arguments(
    parser: argparse.ArgumentParser,
    *,
    positive_int: IntParser,
) -> None:
    parser.add_argument("--log-count", type=positive_int, default=5, metavar="N", help="Maximum commits to show with --log.")
    parser.add_argument("--show-path", metavar="PATH", help="Optional project-relative path for --show.")
    parser.add_argument("--show-max-chars", type=positive_int, default=12_000, metavar="N", help="Maximum output characters for --show.")
    parser.add_argument("--blame-lines", metavar="START[:END]", help="Optional inclusive line range for --blame.")
    parser.add_argument("--blame-max-chars", type=positive_int, default=12_000, metavar="N", help="Maximum output characters for --blame.")
    parser.add_argument("--stash-count", type=positive_int, default=20, metavar="N", help="Maximum stash entries to show with --stashes.")
    parser.add_argument("--stash-include-untracked", action="store_true", help="Include untracked files with --check-git-stash or --git-stash.")
    parser.add_argument("--git-switch-create", action="store_true", help="Create the branch when used with --check-git-switch or --git-switch.")
