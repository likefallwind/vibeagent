from __future__ import annotations

import argparse
from typing import Callable


IntParser = Callable[[str], int]


def add_read_local_arguments(local: argparse._MutuallyExclusiveGroup) -> None:
    local.add_argument("--file-info", nargs="+", metavar="PATH", help="Show file, directory, size, and line metadata and exit.")
    local.add_argument("--image-info", nargs="+", metavar="PATH", help="Show image format, byte size, and dimensions and exit.")
    local.add_argument("--read", metavar="PATH", help="Read one project file and exit.")
    local.add_argument("--around", nargs=2, metavar=("PATH", "LINE"), help="Read one project file line with surrounding context and exit.")
    local.add_argument("--around-many", nargs="+", metavar="PATH:LINE[:CONTEXT]", help="Read several project file lines with surrounding context and exit.")
    local.add_argument("--output-contexts", metavar="TEXT", help="Extract file:line references from command output and read contexts.")
    local.add_argument("--output-diagnostics", metavar="TEXT", help="Summarize command output diagnostics and read referenced contexts.")
    local.add_argument("--python-traceback", metavar="TEXT", help="Summarize Python traceback or pytest exception output and read referenced contexts.")
    local.add_argument("--tail", metavar="PATH", help="Read the last lines of one project file and exit.")
    local.add_argument("--read-files", nargs="+", metavar="PATH", help="Read multiple project files and exit.")
    local.add_argument("--read-ranges", nargs="+", metavar="PATH:START[:END]", help="Read multiple focused project file line ranges and exit.")


def add_read_option_arguments(
    parser: argparse.ArgumentParser,
    *,
    positive_int: IntParser,
    nonnegative_int: IntParser,
) -> None:
    parser.add_argument("--read-lines", metavar="START[:END]", help="Optional inclusive line range for --read.")
    parser.add_argument("--read-max-bytes", type=positive_int, metavar="N", help="Maximum bytes to read with --read.")
    parser.add_argument("--read-line-numbers", action="store_true", help="Prefix full-file --read output with 1-based line numbers.")
    parser.add_argument("--read-files-max-bytes", type=positive_int, metavar="N", help="Maximum bytes per file with --read-files.")
    parser.add_argument("--read-files-line-numbers", action="store_true", help="Prefix --read-files output with 1-based line numbers.")
    parser.add_argument("--read-ranges-max-bytes", type=positive_int, metavar="N", help="Maximum bytes per range with --read-ranges.")
    parser.add_argument("--around-lines", type=nonnegative_int, default=20, metavar="N", help="Surrounding line count for --around.")
    parser.add_argument("--around-max-bytes", type=positive_int, metavar="N", help="Maximum bytes to read with --around.")
    parser.add_argument("--around-many-max-bytes", type=positive_int, metavar="N", help="Maximum bytes per context with --around-many.")
    parser.add_argument("--output-context-lines", type=nonnegative_int, default=5, metavar="N", help="Surrounding line count for --output-contexts.")
    parser.add_argument("--output-context-max", type=positive_int, default=20, metavar="N", help="Maximum contexts to read with --output-contexts.")
    parser.add_argument("--output-context-max-bytes", type=positive_int, default=20_000, metavar="N", help="Maximum bytes per context with --output-contexts.")
    parser.add_argument("--output-diagnostic-lines", type=nonnegative_int, default=2, metavar="N", help="Surrounding source lines for --output-diagnostics.")
    parser.add_argument("--output-diagnostic-max", type=positive_int, default=50, metavar="N", help="Maximum diagnostic lines to show with --output-diagnostics.")
    parser.add_argument("--output-diagnostic-context-max", type=positive_int, default=20, metavar="N", help="Maximum source contexts to read with --output-diagnostics.")
    parser.add_argument("--output-diagnostic-context-max-bytes", type=positive_int, default=20_000, metavar="N", help="Maximum bytes per context with --output-diagnostics or --python-traceback.")
    parser.add_argument("--tail-lines", type=positive_int, default=80, metavar="N", help="Trailing line count for --tail.")
    parser.add_argument("--tail-max-bytes", type=positive_int, metavar="N", help="Maximum bytes to read with --tail.")
