from __future__ import annotations

import argparse
from typing import Callable


IntParser = Callable[[str], int]


def add_project_check_local_arguments(local: argparse._MutuallyExclusiveGroup) -> None:
    local.add_argument("--checks", action="store_true", help="Show suggested test, build, and lint commands and exit.")
    local.add_argument("--check-suggested-checks", nargs="?", const="", metavar="N", help="Preflight suggested test, build, and lint commands and exit.")
    local.add_argument("--run-suggested-checks", nargs="?", const="", metavar="N", help="Run suggested test, build, and lint commands and exit.")
    local.add_argument("--commands", action="store_true", help="Show project-defined commands from manifests and exit.")
    local.add_argument("--related-tests", nargs="*", metavar="PATH", help="Suggest test files related to paths or current git changes and exit.")
    local.add_argument("--focused-tests", nargs="*", metavar="PATH", help="Suggest focused test commands related to paths or current git changes and exit.")
    local.add_argument("--check-focused-tests", nargs="*", metavar="PATH", help="Preflight focused test commands related to paths or current git changes and exit.")
    local.add_argument("--run-focused-tests", nargs="*", metavar="PATH", help="Run focused test commands related to paths or current git changes and exit.")
    local.add_argument("--manifests", action="store_true", help="Show package and pyproject manifest metadata and exit.")
    local.add_argument("--instructions", action="store_true", help="Show AGENTS.md and CLAUDE.md instruction sources and exit.")
    local.add_argument("--hooks", action="store_true", help="Show resolved hook events, handlers, and sources and exit.")
    local.add_argument("--todos", nargs="?", const="", metavar="PATH", help="Show TODO, FIXME, HACK, XXX, and BUG markers and exit.")


def add_project_discovery_local_arguments(local: argparse._MutuallyExclusiveGroup) -> None:
    local.add_argument("--overview", action="store_true", help="Show a compact project orientation bundle and exit.")
    local.add_argument("--repo-map", nargs="?", const="", metavar="PATH", help="Show a bounded repository tree and source symbol map and exit.")
    local.add_argument("--search", metavar="QUERY", help="Search project text with gitignore and safety filtering and exit.")
    local.add_argument("--search-contexts", metavar="QUERY", help="Search project text and show line-centered context snippets and exit.")
    local.add_argument("--find-files", metavar="QUERY", help="Find project files by path fragment and exit.")
    local.add_argument("--glob", metavar="PATTERN", help="Find project files or directories by glob pattern and exit.")
    local.add_argument("--tree", nargs="?", const="", metavar="PATH", help="Show a bounded project directory tree and exit.")
    local.add_argument("--symbols", nargs="+", metavar="PATH", help="Show source imports and symbol outlines and exit.")


def add_project_check_option_arguments(
    parser: argparse.ArgumentParser,
    *,
    positive_int: IntParser,
) -> None:
    parser.add_argument("--checks-max", type=positive_int, default=20, metavar="N", help="Maximum suggested checks to show with --checks.")
    parser.add_argument("--check-suggested-checks-max", type=positive_int, default=10, metavar="N", help="Maximum suggested checks to preflight with --check-suggested-checks.")
    parser.add_argument("--run-suggested-checks-max", type=positive_int, default=10, metavar="N", help="Maximum suggested checks to run with --run-suggested-checks.")


def add_project_discovery_option_arguments(
    parser: argparse.ArgumentParser,
    *,
    positive_int: IntParser,
    nonnegative_int: IntParser,
) -> None:
    parser.add_argument("--search-path", metavar="PATH", help="Project-relative search scope for --search.")
    parser.add_argument("--search-max-matches", type=positive_int, metavar="N", help="Maximum matches to show with --search or --search-contexts.")
    parser.add_argument("--search-regex", action="store_true", help="Treat --search or --search-contexts query as a regular expression.")
    parser.add_argument("--search-ignore-case", action="store_true", help="Use case-insensitive matching with --search or --search-contexts.")
    parser.add_argument("--search-context-lines", type=nonnegative_int, metavar="N", help="Surrounding source lines for --search or --search-contexts.")
    parser.add_argument("--search-context-max-bytes", type=positive_int, metavar="N", help="Maximum bytes per context with --search-contexts.")
    parser.add_argument("--related-tests-max-paths", type=positive_int, metavar="N", help="Maximum source paths to consider with --related-tests.")
    parser.add_argument("--related-tests-max-candidates", type=positive_int, metavar="N", help="Maximum related test candidates to show with --related-tests.")
    parser.add_argument("--focused-tests-max-paths", type=positive_int, metavar="N", help="Maximum source paths to consider with --focused-tests, --check-focused-tests, or --run-focused-tests.")
    parser.add_argument("--focused-tests-max-candidates", type=positive_int, metavar="N", help="Maximum related test candidates to consider with focused test commands.")
    parser.add_argument("--focused-tests-max-commands", type=positive_int, metavar="N", help="Maximum focused test commands to show, preflight, or run.")
    parser.add_argument("--commands-max-commands", type=positive_int, metavar="N", help="Maximum project commands to show with --commands.")
    parser.add_argument("--commands-max-files", type=positive_int, metavar="N", help="Maximum command metadata files to scan with --commands.")
    parser.add_argument("--manifests-max-files", type=positive_int, metavar="N", help="Maximum manifest files to scan with --manifests.")
    parser.add_argument("--manifests-max-items", type=positive_int, metavar="N", help="Maximum manifest items to show with --manifests.")
    parser.add_argument("--todos-max-items", type=positive_int, metavar="N", help="Maximum TODO marker count to show with --todos.")
    parser.add_argument("--todos-max-files", type=positive_int, metavar="N", help="Maximum files to scan with --todos.")
    parser.add_argument("--instructions-max-files", type=positive_int, metavar="N", help="Maximum instruction files to scan with --instructions.")
    parser.add_argument("--instructions-max-bytes", type=positive_int, metavar="N", help="Maximum instruction text bytes to include with --instructions.")
    parser.add_argument("--overview-max-files", type=positive_int, metavar="N", help="Maximum files to show with --overview.")
    parser.add_argument("--overview-max-commands", type=positive_int, metavar="N", help="Maximum project commands to show with --overview.")
    parser.add_argument("--overview-max-checks", type=positive_int, metavar="N", help="Maximum suggested checks to show with --overview.")
    parser.add_argument("--repo-map-max-depth", type=nonnegative_int, metavar="N", help="Maximum tree depth to show with --repo-map.")
    parser.add_argument("--repo-map-max-files", type=positive_int, metavar="N", help="Maximum files to show with --repo-map.")
    parser.add_argument("--repo-map-max-symbols", type=positive_int, metavar="N", help="Maximum symbols to show with --repo-map.")
    parser.add_argument("--find-files-path", metavar="PATH", help="Project-relative scope for --find-files.")
    parser.add_argument("--find-files-max-matches", type=positive_int, metavar="N", help="Maximum path matches to show with --find-files.")
    parser.add_argument("--find-files-regex", action="store_true", help="Treat --find-files query as a regular expression.")
    parser.add_argument("--find-files-case-sensitive", action="store_true", help="Use case-sensitive matching with --find-files.")
    parser.add_argument("--find-files-include-dirs", action="store_true", help="Include matching directories with trailing slashes in --find-files output.")
    parser.add_argument("--glob-max-matches", type=positive_int, metavar="N", help="Maximum file matches to show with --glob.")
    parser.add_argument("--glob-include-dirs", action="store_true", help="Include matching directories with trailing slashes in --glob output.")
    parser.add_argument("--tree-max-depth", type=nonnegative_int, metavar="N", help="Maximum directory depth to show with --tree.")
    parser.add_argument("--tree-max-entries", type=positive_int, metavar="N", help="Maximum entries to show with --tree.")
    parser.add_argument("--symbols-max", type=positive_int, metavar="N", help="Maximum symbols to show with --symbols.")
